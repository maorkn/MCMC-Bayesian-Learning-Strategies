"""Utility script to probe MAX31865 behaviour when the sensor appears to stall.

Run directly from the REPL:
    import max31865_diagnostic
    max31865_diagnostic.run(duration_sec=300, sample_interval=1)

The script records register snapshots, highlights raw readings of 0 / 0x7FFF,
and prints a summary so we can tell whether the issue is electrical or
software. Designed for MicroPython on the ESP32.
"""
import time
import gc

from max31865 import (
    init_max31865,
    read_temperature,
    read_temperature_raw,
    read_register,
    check_fault,
    write_register,
    CONFIG_REG,
    RTD_MSB_REG,
    RTD_LSB_REG,
)


def _read_raw_registers():
    """Return a dict with raw register values and derived RTD code."""
    msb = read_register(RTD_MSB_REG)
    lsb = read_register(RTD_LSB_REG)
    raw = ((msb << 8) | lsb) >> 1
    return {"msb": msb, "lsb": lsb, "raw": raw}


def _classify_raw(raw_value):
    """Label raw samples that are suspicious so they stand out in the log."""
    if raw_value == 0:
        return "raw_zero"
    if raw_value == 0x7FFF:
        return "raw_max"
    return "ok"


def _snapshot():
    """Grab one measurement snapshot from the sensor."""
    registers = _read_raw_registers()
    config_val = read_register(CONFIG_REG)
    fault = check_fault()
    temp = read_temperature()
    if temp is None:
        # Fall back to a single raw read to capture the latest value
        temp = read_temperature_raw()
    return {
        "temp": temp,
        "config": config_val,
        "fault": fault,
        "raw": registers["raw"],
        "msb": registers["msb"],
        "lsb": registers["lsb"],
        "raw_state": _classify_raw(registers["raw"]),
    }


def _print_snapshot(idx, elapsed, snap):
    """Stream-friendly line describing the current snapshot."""
    temp_txt = "None" if snap["temp"] is None else "{:.2f}".format(snap["temp"])
    fault_txt = snap["fault"] if snap["fault"] else "-"
    print(
        "#{:04d} {:6.1f}s temp={} raw=0x{:04X} ({}) cfg=0x{:02X} fault={}".format(
            idx,
            elapsed,
            temp_txt,
            snap["raw"],
            snap["raw_state"],
            snap["config"],
            fault_txt,
        )
    )


def _summary(stats):
    """Print aggregated statistics after the run finishes."""
    total = stats["total"]
    if total == 0:
        print("No samples captured.")
        return

    print("\n=== MAX31865 Diagnostic Summary ===")
    print("Samples:", total)
    print("Valid temps:", stats["valid_temp"])
    print("None temps:", stats["none_temp"])
    print("Faults triggered:", stats["fault_events"])
    print("Raw zero count:", stats["raw_zero"])
    print("Raw max count:", stats["raw_max"])
    print("Config deviations:", stats["config_bad"])
    if stats["longest_zero_streak"] > 0:
        print("Longest consecutive raw-zero streak:", stats["longest_zero_streak"])
    if stats["recoveries_attempted"]:
        print("Auto recoveries attempted:", stats["recoveries_attempted"])


def _maybe_recover(snap, stats):
    """If raw goes to zero repeatedly, try a local reconfiguration."""
    if snap["raw_state"] != "raw_zero":
        stats["current_zero_streak"] = 0
        return

    stats["current_zero_streak"] += 1
    stats["longest_zero_streak"] = max(
        stats["longest_zero_streak"], stats["current_zero_streak"]
    )

    if stats["current_zero_streak"] < 5:
        return

    print("[Diagnostic] Raw zero persists, re-sending CONFIG 0xC3")
    stats["recoveries_attempted"] += 1
    try:
        write_register(CONFIG_REG, 0x00)
        time.sleep_ms(50)
        write_register(CONFIG_REG, 0xC3)
        time.sleep_ms(100)
        cfg = read_register(CONFIG_REG)
        print("[Diagnostic] Config readback after recovery: 0x{:02X}".format(cfg))
    except Exception as exc:
        print("[Diagnostic] Recovery write failed:", exc)


def run(duration_sec=120, sample_interval=1.0):
    """Run the diagnostic loop for the requested duration."""
    print("\n=== MAX31865 Diagnostic ===")
    print("Duration:", duration_sec, "seconds")
    print("Sample interval:", sample_interval, "seconds")

    if not init_max31865():
        print("[Diagnostic] Sensor failed to initialise; aborting test.")
        return

    stats = {
        "total": 0,
        "valid_temp": 0,
        "none_temp": 0,
        "fault_events": 0,
        "raw_zero": 0,
        "raw_max": 0,
        "config_bad": 0,
        "current_zero_streak": 0,
        "longest_zero_streak": 0,
        "recoveries_attempted": 0,
    }

    start = time.time()
    idx = 0

    while True:
        now = time.time()
        elapsed = now - start
        if elapsed >= duration_sec:
            break

        snap = _snapshot()
        idx += 1
        stats["total"] += 1

        if snap["temp"] is None:
            stats["none_temp"] += 1
        else:
            stats["valid_temp"] += 1

        if snap["fault"]:
            stats["fault_events"] += 1

        if snap["raw_state"] == "raw_zero":
            stats["raw_zero"] += 1
        elif snap["raw_state"] == "raw_max":
            stats["raw_max"] += 1

        if snap["config"] not in (0xC3, 0xC1):
            stats["config_bad"] += 1

        _print_snapshot(idx, elapsed, snap)
        _maybe_recover(snap, stats)

        gc.collect()
        sleep_left = sample_interval - (time.time() - now)
        if sleep_left > 0:
            time.sleep(sleep_left)

    _summary(stats)


if __name__ == "__main__":
    run()
