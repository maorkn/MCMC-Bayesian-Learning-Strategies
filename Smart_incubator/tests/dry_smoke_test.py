#!/usr/bin/env python3
"""
Dry-run smoke test for the Smart Incubator firmware.

This harness bootstraps stub hardware modules, runs the real `main.py`
control loop, and executes a handful of accelerated experiment cycles
without requiring an ESP32. The `time` module is optionally patched to a
simulated clock so cycles finish instantly while preserving the control
logic flow.
"""

from __future__ import annotations

import argparse
import gc
import importlib
import random
import sys
import time
import types
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Optional

SCRIPT_DIR = Path(__file__).resolve().parent
SMART_INCUBATOR_DIR = SCRIPT_DIR.parent
FIRMWARE_DIR = SMART_INCUBATOR_DIR / "Firmware"


class DryRunFinished(BaseException):
    """Signal raised internally to stop the infinite main loop."""


class SimulatedClock:
    """MicroPython-style clock that advances instantly when sleeping."""

    def __init__(self):
        self._now = 0.0

    def time(self) -> float:
        return self._now

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            self._now += seconds

    def sleep_ms(self, milliseconds: int) -> None:
        if milliseconds > 0:
            self._now += milliseconds / 1000.0

    def ticks_ms(self) -> int:
        return int(self._now * 1000)

    @staticmethod
    def ticks_diff(a: int, b: int) -> int:
        return a - b


def ensure_gc_helpers() -> None:
    """MicroPython compatibility for CPython's gc module."""
    if not hasattr(gc, "mem_free"):
        gc.mem_free = lambda: 128 * 1024  # type: ignore[attr-defined]


def install_simulated_clock(use_simulated_time: bool) -> Optional[SimulatedClock]:
    """Patch the time module with fast, deterministic behaviour."""
    if not use_simulated_time:
        if not hasattr(time, "sleep_ms"):
            time.sleep_ms = lambda ms: time.sleep(ms / 1000.0)  # type: ignore[attr-defined]
        if not hasattr(time, "ticks_ms"):
            time.ticks_ms = lambda: int(time.time() * 1000)  # type: ignore[attr-defined]
        if not hasattr(time, "ticks_diff"):
            time.ticks_diff = lambda a, b: a - b  # type: ignore[attr-defined]
        return None

    sim_clock = SimulatedClock()
    time.time = sim_clock.time  # type: ignore[assignment]
    time.sleep = sim_clock.sleep  # type: ignore[assignment]
    time.sleep_ms = sim_clock.sleep_ms  # type: ignore[assignment]
    time.ticks_ms = sim_clock.ticks_ms  # type: ignore[assignment]
    time.ticks_diff = sim_clock.ticks_diff  # type: ignore[assignment]
    return sim_clock


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def install_stub_modules(verbose_logger: bool = False) -> None:
    """Provide host-friendly stand-ins for hardware-specific modules."""

    # --- machine module -----------------------------------------------------
    machine = types.ModuleType("machine")

    class Pin:
        OUT = 0
        IN = 1

        def __init__(self, pin: int, mode: Optional[int] = None, value: int = 0):
            self.pin = pin
            self.mode = mode
            self._value = value

        def value(self, new_value: Optional[int] = None) -> int:
            if new_value is None:
                return self._value
            self._value = new_value
            return self._value

    class PWM:
        def __init__(self, pin: Pin):
            self.pin = pin
            self._freq = 1000
            self._duty = 0

        def freq(self, value: Optional[int] = None) -> int:
            if value is None:
                return self._freq
            self._freq = value
            return self._freq

        def duty_u16(self, value: Optional[int] = None) -> int:
            if value is None:
                return self._duty
            self._duty = int(_clamp(value, 0, 65535))
            return self._duty

        def duty(self, value: Optional[int] = None) -> int:
            if value is None:
                return int(self._duty / 65535 * 1023)
            scaled = int(_clamp(value, 0, 1023))
            self._duty = int((scaled / 1023) * 65535)
            return scaled

    class SPI:
        def __init__(self, *_args, **_kwargs):
            self._last_write = b""

        def write(self, data: bytes) -> None:
            self._last_write = bytes(data)

        def read(self, length: int) -> bytes:
            return bytes([0] * length)

    class RTC:
        def datetime(self):
            tm = time.localtime()
            return (tm.tm_year, tm.tm_mon, tm.tm_mday, tm.tm_wday, tm.tm_hour, tm.tm_min, tm.tm_sec, 0)

    machine.Pin = Pin
    machine.PWM = PWM
    machine.SPI = SPI
    machine.RTC = RTC
    sys.modules["machine"] = machine

    # --- urandom module -----------------------------------------------------
    urandom = types.ModuleType("urandom")
    urandom.randint = random.randint  # type: ignore[attr-defined]
    urandom.getrandbits = random.getrandbits  # type: ignore[attr-defined]
    sys.modules["urandom"] = urandom

    # --- max31865 (temperature sensor) -------------------------------------
    max31865 = types.ModuleType("max31865")

    def init_max31865() -> bool:
        return True

    def read_temperature() -> float:
        return 23.0 + random.uniform(-0.25, 0.25)

    def check_fault():
        return None

    max31865.init_max31865 = init_max31865  # type: ignore[attr-defined]
    max31865.read_temperature = read_temperature  # type: ignore[attr-defined]
    max31865.check_fault = check_fault  # type: ignore[attr-defined]
    sys.modules["max31865"] = max31865

    # --- sd_logger stub -----------------------------------------------------
    sd_logger = types.ModuleType("sd_logger")

    class ExperimentLogger:
        def __init__(self, meta_data: Optional[Dict[str, Any]] = None):
            self.meta_data = meta_data or {}
            self.sd_write_ok = True
            self.snapshots = []
            self.cycle_summaries = []
            self.status = "init"
            self.error = None

        def init_experiment(self) -> bool:
            print("[DryRun] Experiment logger initialized with params:", self.meta_data)
            self.status = "running"
            return True

        def log_snapshot(self, cycle_num: int, data: Dict[str, Any]) -> bool:
            if len(self.snapshots) < 25:
                self.snapshots.append((cycle_num, data))
            if verbose_logger:
                print(f"[DryRun] Snapshot cycle={cycle_num} elapsed={data.get('elapsed_minutes')}")
            return True

        def log_cycle_summary(self, cycle_num: int, data: Dict[str, Any]) -> bool:
            summary = {"cycle": cycle_num, **data}
            self.cycle_summaries.append(summary)
            if verbose_logger:
                print(f"[DryRun] Cycle {cycle_num} summary:", summary)
            return True

        def finalize_experiment(self, status: str = "complete", error: Optional[str] = None) -> bool:
            self.status = status
            self.error = error
            print(f"[DryRun] Experiment finalized with status='{status}' error='{error}'")
            return True

    def init_sd() -> bool:
        print("[DryRun] init_sd() called")
        return True

    def deinit():
        print("[DryRun] sd_deinit() called")

    sd_logger.ExperimentLogger = ExperimentLogger  # type: ignore[attr-defined]
    sd_logger.init_sd = init_sd  # type: ignore[attr-defined]
    sd_logger.deinit = deinit  # type: ignore[attr-defined]
    sys.modules["sd_logger"] = sd_logger

    # --- OLED display stub --------------------------------------------------
    oled_display = types.ModuleType("oled_display")

    class OLEDDisplay:
        def __init__(self):
            self.last_payload = None

        def update_display(self, *payload):
            self.last_payload = payload

        def clear(self):
            self.last_payload = None

    oled_display.OLEDDisplay = OLEDDisplay  # type: ignore[attr-defined]
    sys.modules["oled_display"] = oled_display

    # --- temp_controller stub ----------------------------------------------
    temp_controller = types.ModuleType("temp_controller")

    class _Actuator:
        def __init__(self, name: str):
            self.name = name
            self.is_on = False

        def turn_off(self):
            self.is_on = False

    class _Cooler(_Actuator):
        pass

    class TempController:
        def __init__(self, *_args, **_kwargs):
            self.heater = _Actuator("heater")
            self.cooler = _Cooler("cooler")
            self._temp = 23.0

        def control_temp(self, target_temp: float):
            delta = target_temp - self._temp
            self._temp += delta * 0.35
            noise = random.uniform(-0.05, 0.05)
            self._temp += noise
            mode = "idle"
            if delta > 0.2:
                mode = "heat"
                self.cooler.is_on = False
            elif delta < -0.2:
                mode = "cool"
                self.cooler.is_on = True
            else:
                self.cooler.is_on = False
            power = _clamp(abs(delta) * 12.0, 0.0, 100.0)
            return round(self._temp, 3), round(power, 2), mode

    temp_controller.TempController = TempController  # type: ignore[attr-defined]
    sys.modules["temp_controller"] = temp_controller

    # --- LED / vibration / US control stubs ---------------------------------
    led_control = types.ModuleType("led_control")
    led_module = types.ModuleType("led")

    class LED:
        def __init__(self, pwm: PWM):
            self.pwm = pwm
            self.brightness = 0.0

        def set_brightness(self, value: float):
            self.brightness = _clamp(value, 0, 100)
            self.pwm.duty_u16(int(self.brightness / 100 * 65535))

        def turn_off(self):
            self.set_brightness(0)

    led_control.LED = LED  # type: ignore[attr-defined]
    led_module.LED = LED  # type: ignore[attr-defined]
    sys.modules["led_control"] = led_control
    sys.modules["led"] = led_module

    vibration_control = types.ModuleType("vibration_control")

    class Vibration:
        def __init__(self, pwm: PWM):
            self.pwm = pwm
            self.intensity = 0.0
            self.interval = (20, 60)
            self.active = False
            self._start_time = time.time()

        def set_intensity(self, value: float):
            self.intensity = _clamp(value, 0, 100)

        def set_interval(self, interval):
            if isinstance(interval, str):
                on, off = interval.split(":")
                self.interval = (int(on), int(off))
            else:
                self.interval = interval

        def start(self):
            self.active = True
            self._start_time = time.time()
            self._apply_pwm(True)

        def stop(self):
            self.active = False
            self.pwm.duty_u16(0)

        def update(self):
            if not self.active:
                return
            on, off = self.interval
            period = max(1, on + off)
            elapsed = (time.time() - self._start_time) % period
            self._apply_pwm(elapsed < on)

        def _apply_pwm(self, on_state: bool):
            if on_state:
                self.pwm.duty_u16(int(self.intensity / 100 * 65535))
            else:
                self.pwm.duty_u16(0)

    vibration_control.Vibration = Vibration  # type: ignore[attr-defined]
    sys.modules["vibration_control"] = vibration_control

    us_control = types.ModuleType("us_control")

    class USController:
        def __init__(self, led_obj: LED, vib_obj: Vibration):
            self.led = led_obj
            self.vib = vib_obj
            self.led_intensity = 25
            self.vib_intensity = 100

        def set_led_intensity(self, value: float):
            self.led_intensity = _clamp(value, 0, 100)
            self.led.set_brightness(self.led_intensity)

        def set_vib_intensity(self, value: float):
            self.vib_intensity = _clamp(value, 0, 100)
            self.vib.set_intensity(self.vib_intensity)

        def set_vib_interval(self, interval: str):
            self.vib.set_interval(interval)

        def activate(self, _us_type="BOTH"):
            self.led.set_brightness(self.led_intensity)
            self.vib.start()
            return 1, 1

        def deactivate(self, _us_type="BOTH"):
            self.led.turn_off()
            self.vib.stop()
            return 0, 0

        def update_vibration(self):
            self.vib.update()

    us_control.USController = USController  # type: ignore[attr-defined]
    sys.modules["us_control"] = us_control


def reset_module_cache() -> None:
    """Remove firmware modules that we want to import fresh."""
    for name in ("main", "run_experiment_cycle"):
        sys.modules.pop(name, None)


def configure_main_for_test(main_module, args) -> None:
    """Overwrite long-running production parameters with test-friendly ones."""
    main_module.min_interval = args.min_minutes
    main_module.max_interval = args.max_minutes
    main_module.us_duration_seconds = args.us_seconds
    main_module.heat_duration_seconds = args.heat_seconds
    main_module.correlation = _clamp(args.correlation, -1.0, 1.0)


def wrap_run_cycle(main_module, rec_module, max_cycles: int):
    """Wrap run_experiment_cycle so we can stop after a few iterations."""
    counter = {"count": 0}
    original = rec_module.run_experiment_cycle

    def wrapper(*args, **kwargs):
        result = original(*args, **kwargs)
        counter["count"] += 1
        if counter["count"] >= max_cycles:
            raise DryRunFinished()
        return result

    rec_module.run_experiment_cycle = wrapper
    main_module.run_experiment_cycle = wrapper
    return counter


def summarize_results(main_module, cycle_counter: int) -> None:
    logger = getattr(main_module, "experiment_logger", None)
    print("\n=== Dry Run Summary ===")
    print(f"Cycles executed: {cycle_counter}")
    if not logger:
        print("No logger instance found.")
        return

    summaries = getattr(logger, "cycle_summaries", [])
    modes = Counter(entry.get("correlation_mode") for entry in summaries if isinstance(entry, dict))
    if modes:
        print("Correlation modes observed:", dict(modes))
    else:
        print("No cycle summaries recorded.")

    print(f"Snapshots captured: {len(getattr(logger, 'snapshots', []))}")
    print(f"Experiment status: {getattr(logger, 'status', 'unknown')}")
    if logger.error:
        print(f"Logger reported error: {logger.error}")


def parse_args():
    parser = argparse.ArgumentParser(description="Dry-run Smart Incubator main loop without hardware.")
    parser.add_argument("--cycles", type=int, default=2, help="Number of experiment cycles to run before stopping.")
    parser.add_argument("--correlation", type=float, default=0.5, help="Correlation value fed into main.py.")
    parser.add_argument("--min-minutes", type=int, default=1, help="Minimum cycle length in minutes.")
    parser.add_argument("--max-minutes", type=int, default=2, help="Maximum cycle length in minutes.")
    parser.add_argument("--heat-seconds", type=int, default=120, help="Heat shock duration in seconds.")
    parser.add_argument("--us-seconds", type=int, default=60, help="US duration in seconds.")
    parser.add_argument("--realtime", action="store_true", help="Use real wall-clock time instead of the simulated clock.")
    parser.add_argument("--verbose-logger", action="store_true", help="Print each snapshot/summary the stub logger records.")
    parser.add_argument("--seed", type=int, help="Seed value for deterministic randomness.")
    return parser.parse_args()


def main():
    args = parse_args()
    if args.max_minutes < args.min_minutes:
        raise SystemExit("max-minutes must be >= min-minutes")
    if args.seed is not None:
        random.seed(args.seed)

    ensure_gc_helpers()
    install_simulated_clock(not args.realtime)
    install_stub_modules(verbose_logger=args.verbose_logger)

    sys.path.insert(0, str(FIRMWARE_DIR))
    reset_module_cache()

    rec_module = importlib.import_module("run_experiment_cycle")
    main_module = importlib.import_module("main")
    configure_main_for_test(main_module, args)
    counter = wrap_run_cycle(main_module, rec_module, max_cycles=args.cycles)

    try:
        main_module.main()
    except DryRunFinished:
        pass

    summarize_results(main_module, counter["count"])


if __name__ == "__main__":
    main()
