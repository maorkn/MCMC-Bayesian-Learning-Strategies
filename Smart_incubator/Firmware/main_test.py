# main_test.py - Post-training survival test protocol
from machine import Pin, PWM
import time
import gc

from max31865 import init_max31865
from sd_logger import ExperimentLogger, init_sd, deinit as sd_deinit
from oled_display import OLEDDisplay
from temp_controller import TempController
from led_control import LED
from vibration_control import Vibration
from us_control import USController

# ---- PIN DEFINITIONS ----
TEC_PIN = 27   # TEC1 cooler control pin
LED_PIN = 25   # LED control pin
VIB_PIN = 16   # Vibration control pin
PTC_PIN = 33   # PTC heater control pin

# ---- GLOBAL STATE ----
display = None
temp_ctrl = None
us_controller = None
led_pwm = None
vib_pwm = None
experiment_logger = None

# ---- TEST CONFIGURATION ----
training_temp = 23.0                     # Degrees Celsius during US exposure
challenge_temp = 38.0                    # Degrees Celsius during lethal challenge
training_duration_seconds = 30 * 60      # 30 minutes of US at basal temperature
challenge_duration_seconds = 150 * 60     # Default 150 minute challenge (adjust as needed)
us_led_intensity = 100                   # 100% light intensity
us_vibration_intensity = 100             # 100% vibration intensity
us_type = "BOTH"
log_interval_seconds = 10                # SD logging cadence
status_interval_seconds = 60             # Console status cadence
gc_interval_seconds = 300                # Run GC every 5 minutes

test_notes = "Post-training survival test with tubes: corr=1, corr=0, control"
stage_display_metadata = {
    "training_us": {"cycle": 1, "correlation": 1.0},
    "heat_challenge": {"cycle": 2, "correlation": 0.0}
}


def init_output_pins():
    """Initialize LED and vibration PWM outputs."""
    global led_pwm, vib_pwm

    led_pwm = PWM(Pin(LED_PIN))
    vib_pwm = PWM(Pin(VIB_PIN))

    for pwm in (led_pwm, vib_pwm):
        pwm.freq(1000)
        pwm.duty_u16(0)

    return True


def init_temp_sensor():
    """Initialize the PT100 temperature sensor."""
    return init_max31865()


def init_display():
    """Initialize OLED display (optional)."""
    try:
        disp = OLEDDisplay()
        print("[System] OLED display initialized")
        return disp
    except Exception as exc:
        print(f"[WARNING] OLED init failed: {exc}")
        return None


def init_temp_controller():
    """Create temperature controller instance."""
    return TempController(PTC_PIN, TEC_PIN, kp=6.0, ki=0.02, kd=1.5)


def init_us_controller():
    """Create US controller with LED and vibration drivers."""
    global led_pwm, vib_pwm
    led = LED(led_pwm)
    vibration = Vibration(vib_pwm)
    return USController(led, vibration)


def cleanup_globals():
    """Release hardware resources to allow a restart."""
    global display, temp_ctrl, us_controller, experiment_logger

    print("[Cleanup] Releasing peripherals...")
    try:
        sd_deinit()
        print("[Cleanup] SD SPI released")
    except Exception as exc:
        print(f"[Cleanup] SD release warning: {exc}")

    time.sleep(1)
    display = None
    temp_ctrl = None
    us_controller = None
    experiment_logger = None
    gc.collect()
    print("[Cleanup] Cleanup complete")


def init_system():
    """Initialize every subsystem required for the test."""
    global display, temp_ctrl, us_controller, experiment_logger

    try:
        print("\n=== Smart Incubator Post-Training Test ===")
        print("[System] Initializing hardware...")

        init_output_pins()
        if not init_temp_sensor():
            raise RuntimeError("Temperature sensor initialization failed")

        display = init_display()
        temp_ctrl = init_temp_controller()
        us_controller = init_us_controller()

        print("[System] Initializing SD card...")
        if not init_sd():
            raise RuntimeError("SD card initialization failed")

        print("[System] Configuring experiment logger...")
        experiment_params = {
            "mode": "post_training_test",
            "training_temp": float(training_temp),
            "training_duration_minutes": training_duration_seconds / 60.0,
            "challenge_temp": float(challenge_temp),
            "challenge_duration_minutes": challenge_duration_seconds / 60.0,
            "us_led_intensity": int(us_led_intensity),
            "us_vibration_intensity": int(us_vibration_intensity),
            "notes": test_notes,
            "tubes": ["corr=1", "corr=0", "control"]
        }
        experiment_logger = ExperimentLogger(experiment_params)
        if not experiment_logger.init_experiment():
            raise RuntimeError("Experiment logger initialization failed")

        print("[System] Initialization complete")
        return True

    except Exception as exc:
        print(f"[ERROR] Initialization failed: {exc}")
        return False


def configure_us_for_training():
    """Configure US controller for constant 100% LED and vibration."""
    if not us_controller:
        raise RuntimeError("US controller is unavailable")

    us_controller.set_led_intensity(us_led_intensity)
    us_controller.set_vib_intensity(us_vibration_intensity)
    us_controller.set_vib_interval(f"{training_duration_seconds}:0")  # Keep vibration on


def refresh_display(stage_name, elapsed, duration_seconds, target_temp, current_temp, us_active, mode):
    """Render current stage status on the OLED (if available)."""
    if not display or current_temp is None:
        return

    metadata = stage_display_metadata.get(stage_name, {})
    display.update_display(
        current_temp=current_temp,
        set_temp=target_temp,
        elapsed_minutes=elapsed / 60.0,
        cycle_length=max(1, duration_seconds / 60.0),
        us_active=1 if us_active else 0,
        led_active=1 if us_active else 0,
        vib_active=1 if us_active else 0,
        tec_state=0 if mode == "Idle" else 1,
        cycle_num=metadata.get("cycle", 0),
        correlation=metadata.get("correlation", 0.0)
    )


def log_stage_snapshot(cycle_number, stage_name, elapsed, remaining, target_temp,
                       current_temp, power, mode, us_active):
    """Log a single snapshot for the current stage."""
    if not experiment_logger:
        return

    data = {
        "stage": stage_name,
        "elapsed_seconds": int(elapsed),
        "remaining_seconds": int(max(0, remaining)),
        "target_temp": float(target_temp),
        "current_temp": float(current_temp) if current_temp is not None else None,
        "power": float(power),
        "mode": mode,
        "us_active": bool(us_active),
        "led_intensity": us_led_intensity if us_active else 0,
        "vibration_intensity": us_vibration_intensity if us_active else 0
    }
    experiment_logger.log_snapshot(cycle_number, data)


def summarize_stage(cycle_number, stage_name, stats, duration_seconds, target_temp, us_active):
    """Persist a summary for the completed stage."""
    if not experiment_logger:
        return

    avg_temp = stats["temp_sum"] / stats["temp_count"] if stats["temp_count"] else None
    summary = {
        "stage": stage_name,
        "duration_seconds": duration_seconds,
        "target_temp": target_temp,
        "avg_temp": avg_temp,
        "min_temp": stats["min_temp"] if stats["temp_count"] else None,
        "max_temp": stats["max_temp"] if stats["temp_count"] else None,
        "error_count": stats["error_count"],
        "us_active": bool(us_active),
        "led_intensity": us_led_intensity if us_active else 0,
        "vibration_intensity": us_vibration_intensity if us_active else 0
    }
    experiment_logger.log_cycle_summary(cycle_number, summary)


def run_stage(stage_name, cycle_number, target_temp, duration_seconds, activate_us=False):
    """Run a single temperature-controlled stage."""
    if duration_seconds <= 0:
        print(f"[{stage_name}] Duration is zero, skipping stage.")
        return True

    if experiment_logger and not experiment_logger.sd_write_ok:
        raise RuntimeError("SD card is unhealthy; aborting test.")

    us_active = False
    last_valid_temp = None
    consecutive_invalid = 0
    max_invalid = 10
    start_time = time.time()
    last_log_time = start_time
    last_status_time = start_time
    last_gc_time = start_time

    stats = {
        "min_temp": float("inf"),
        "max_temp": float("-inf"),
        "temp_sum": 0.0,
        "temp_count": 0,
        "error_count": 0
    }

    try:
        print(f"\n[{stage_name}] Target {target_temp}°C for {duration_seconds / 60:.1f} minutes")

        if activate_us:
            configure_us_for_training()
            us_controller.activate(us_type)
            us_active = True
            print(f"[{stage_name}] US activated at {us_led_intensity}% LED / {us_vibration_intensity}% vibration")

        while True:
            now = time.time()
            elapsed = now - start_time
            remaining = duration_seconds - elapsed
            if elapsed >= duration_seconds:
                break

            time.sleep_ms(20)
            current_temp, power, mode = temp_ctrl.control_temp(target_temp)

            if current_temp is None:
                consecutive_invalid += 1
                stats["error_count"] += 1
                if consecutive_invalid >= max_invalid:
                    raise RuntimeError("Temperature sensor failure during stage")
                current_temp = last_valid_temp
                if current_temp is None:
                    continue
            else:
                last_valid_temp = current_temp
                consecutive_invalid = 0
                stats["min_temp"] = min(stats["min_temp"], current_temp)
                stats["max_temp"] = max(stats["max_temp"], current_temp)
                stats["temp_sum"] += current_temp
                stats["temp_count"] += 1

            if now - last_log_time >= log_interval_seconds:
                log_stage_snapshot(
                    cycle_number,
                    stage_name,
                    elapsed,
                    remaining,
                    target_temp,
                    current_temp,
                    power,
                    mode,
                    us_active
                )
                last_log_time = now

            if now - last_status_time >= status_interval_seconds:
                print(f"[{stage_name}] Elapsed {elapsed/60:.1f}m / {duration_seconds/60:.1f}m | "
                      f"Temp {current_temp:.2f}°C | Mode {mode} | Power {power:.1f}")
                last_status_time = now

            refresh_display(
                stage_name=stage_name,
                elapsed=elapsed,
                duration_seconds=duration_seconds,
                target_temp=target_temp,
                current_temp=current_temp,
                us_active=us_active,
                mode=mode
            )

            if now - last_gc_time >= gc_interval_seconds:
                gc.collect()
                last_gc_time = now

        summarize_stage(cycle_number, stage_name, stats, duration_seconds, target_temp, us_active)
        print(f"[{stage_name}] Stage complete")
        return True

    finally:
        if activate_us and us_active and us_controller:
            us_controller.deactivate(us_type)
            print(f"[{stage_name}] US deactivated")


def run_post_training_protocol():
    """Execute the training exposure then the lethal challenge."""
    print("\n[Test] Starting post-training protocol...")

    if not run_stage(
        stage_name="training_us",
        cycle_number=1,
        target_temp=training_temp,
        duration_seconds=training_duration_seconds,
        activate_us=True
    ):
        return False

    print("\n[Test] Heat challenge beginning...")
    if not run_stage(
        stage_name="heat_challenge",
        cycle_number=2,
        target_temp=challenge_temp,
        duration_seconds=challenge_duration_seconds,
        activate_us=False
    ):
        return False

    print("\n[Test] Protocol complete. Allow samples to cool before handling.")
    return True


def main():
    """Entry point for the dedicated test protocol."""
    gc.collect()
    print(f"[Memory] Initial free heap: {gc.mem_free()} bytes")

    attempts = 3
    init_delay = 5
    initialized = False

    for attempt in range(1, attempts + 1):
        print(f"\n[System] Initialization attempt {attempt}/{attempts}")
        if attempt > 1:
            cleanup_globals()

        if init_system():
            initialized = True
            break

        if attempt < attempts:
            print(f"[System] Retry in {init_delay} seconds...")
            time.sleep(init_delay)

    if not initialized:
        print("[System] Failed to initialize hardware. Check wiring and restart.")
        return

    try:
        success = run_post_training_protocol()
        if experiment_logger:
            if success:
                experiment_logger.finalize_experiment(status="completed")
            else:
                experiment_logger.finalize_experiment(status="error", error="Protocol failed")
    except Exception as exc:
        print(f"[ERROR] Protocol aborted: {exc}")
        if experiment_logger:
            experiment_logger.finalize_experiment(status="error", error=str(exc))
        raise
    finally:
        if temp_ctrl:
            temp_ctrl.heater.turn_off()
            temp_ctrl.cooler.turn_off()
        if us_controller:
            us_controller.deactivate(us_type)
        if display:
            display.clear()
        print("[System] Shutdown complete")


if __name__ == "__main__":
    main()
