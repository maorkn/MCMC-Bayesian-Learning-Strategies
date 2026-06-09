# readiness_soak.py - Continuous sensor and actuator readiness test
from machine import Pin, PWM
import gc
import time

from max31865 import (
    CONFIG_REG,
    REF_RESISTANCE,
    RTD_LSB_REG,
    RTD_MSB_REG,
    check_fault,
    deinit as temp_deinit,
    init_max31865,
    read_register,
    read_temperature,
)
from oled_display import OLEDDisplay
from sd_logger import ExperimentLogger, deinit as sd_deinit, init_sd
from heater import PTCHeater
from tec import TEC1Cooler

TEC_PIN = 27
LED_PIN = 25
VIB_PIN = 16
PTC_PIN = 33


def run(
    duration_minutes=10,
    cycle_seconds=60,
    actuator_seconds=10,
    sample_seconds=5,
    led_intensity=50,
    vibration_intensity=100,
    cooling_power=50,
    heating_power=30,
    max_safe_temp=40.0,
):
    """Run a sensor/logger soak with a short actuator sequence every minute."""
    led_pwm = None
    vib_pwm = None
    heater = None
    cooler = None
    display = None
    logger = None
    mode = None
    status = "error"
    error_message = None
    sample_count = 0
    valid_count = 0
    invalid_count = 0
    fault_count = 0
    config_bad_count = 0
    min_temp = None
    max_temp = None

    led_intensity = max(0, min(100, int(led_intensity)))
    vibration_intensity = max(0, min(100, int(vibration_intensity)))
    cooling_power = max(0, min(100, int(cooling_power)))
    heating_power = max(0, min(100, int(heating_power)))
    duration_seconds = int(duration_minutes * 60)
    actuator_seconds = int(actuator_seconds)
    cycle_seconds = int(cycle_seconds)

    if actuator_seconds * 4 > cycle_seconds:
        raise ValueError("Four actuator steps do not fit in one cycle")

    def outputs_off():
        if led_pwm:
            led_pwm.duty_u16(0)
        if vib_pwm:
            vib_pwm.duty_u16(0)
        if heater:
            heater.turn_off()
        if cooler:
            cooler.turn_off()

    def show_screen(minute_num, current_mode, elapsed, temp, valid, invalid):
        if not display or not getattr(display, "oled", None):
            return
        try:
            display.oled.fill(0)
            display.oled.text("READINESS SOAK", 0, 0)
            display.oled.text("M%02d %s" % (minute_num, current_mode[:11]), 0, 16)
            temp_text = "--" if temp is None else "%.2fC" % temp
            display.oled.text("T:%s %03ds" % (temp_text, int(elapsed)), 0, 32)
            display.oled.text("OK:%d ERR:%d" % (valid, invalid), 0, 48)
            display.oled.show()
        except Exception:
            pass

    def set_mode(new_mode):
        outputs_off()
        if new_mode == "LED":
            led_pwm.duty_u16(int(led_intensity * 65535 / 100))
        elif new_mode == "VIB":
            vib_pwm.duty_u16(int(vibration_intensity * 65535 / 100))
        elif new_mode == "Cooling":
            cooler.turn_on()
            cooler.set_power(cooling_power)
        elif new_mode == "Heating":
            heater.set_power(heating_power)
        print("[Soak] Mode:", new_mode)

    def stage_at(cycle_elapsed):
        if cycle_elapsed < actuator_seconds:
            return "LED"
        if cycle_elapsed < actuator_seconds * 2:
            return "VIB"
        if cycle_elapsed < actuator_seconds * 3:
            return "Cooling"
        if cycle_elapsed < actuator_seconds * 4:
            return "Heating"
        return "Idle"

    print("\n=== EXPERIMENT READINESS SOAK ===")
    print("Duration: %d minutes | Sample: %ds | Actuators: %ds each per minute" %
          (duration_minutes, sample_seconds, actuator_seconds))
    print("LED %d%% | VIB %d%% | Cooling %d%% | Heating %d%% | Safety %.1fC" %
          (led_intensity, vibration_intensity, cooling_power, heating_power, max_safe_temp))

    try:
        outputs_off()
        led_pwm = PWM(Pin(LED_PIN))
        vib_pwm = PWM(Pin(VIB_PIN))
        for pwm in (led_pwm, vib_pwm):
            pwm.freq(1000)
            pwm.duty_u16(0)
        heater = PTCHeater(PTC_PIN)
        cooler = TEC1Cooler(TEC_PIN)
        outputs_off()

        display = OLEDDisplay()
        if not getattr(display, "oled", None):
            raise RuntimeError("OLED initialization failed")
        if not init_max31865():
            raise RuntimeError("MAX31865 initialization failed")
        if not init_sd():
            raise RuntimeError("SD initialization failed")
        logger = ExperimentLogger({
            "mode": "experiment_readiness_soak",
            "duration_minutes": duration_minutes,
            "cycle_seconds": cycle_seconds,
            "actuator_seconds": actuator_seconds,
            "sample_seconds": sample_seconds,
            "led_intensity": led_intensity,
            "vibration_intensity": vibration_intensity,
            "cooling_power": cooling_power,
            "heating_power": heating_power,
        })
        if not logger.init_experiment():
            raise RuntimeError("Failed to initialize readiness log")

        start = time.time()
        next_sample = start
        while time.time() - start < duration_seconds:
            now = time.time()
            elapsed = now - start
            cycle_elapsed = elapsed % cycle_seconds
            new_mode = stage_at(cycle_elapsed)
            if new_mode != mode:
                mode = new_mode
                set_mode(mode)

            if now < next_sample:
                time.sleep(0.1)
                continue
            next_sample += sample_seconds

            config = read_register(CONFIG_REG)
            msb = read_register(RTD_MSB_REG)
            lsb = read_register(RTD_LSB_REG)
            raw = ((msb << 8) | lsb) >> 1
            resistance = raw * REF_RESISTANCE / 32768.0
            fault = check_fault()
            temp = read_temperature()
            sample_count += 1

            valid = temp is not None and raw not in (0, 0x7FFF) and config in (0xC1, 0xC3) and fault is None
            if valid:
                valid_count += 1
                min_temp = temp if min_temp is None else min(min_temp, temp)
                max_temp = temp if max_temp is None else max(max_temp, temp)
            else:
                invalid_count += 1
                if config not in (0xC1, 0xC3):
                    config_bad_count += 1
                if fault:
                    fault_count += 1

            minute_num = int(elapsed // cycle_seconds) + 1
            show_screen(minute_num, mode, elapsed, temp, valid_count, invalid_count)
            print("[Soak] %4ds %-7s temp=%s raw=0x%04X ohms=%.2f cfg=0x%02X fault=%s" %
                  (int(elapsed), mode, "--" if temp is None else "%.2fC" % temp,
                   raw, resistance, config, "-" if fault is None else fault))

            snapshot = {
                "elapsed_seconds": int(elapsed),
                "stage": mode,
                "temp": -99 if temp is None else temp,
                "raw": raw,
                "resistance_ohms": resistance,
                "config": config,
                "fault": "-" if fault is None else fault,
                "valid": valid,
            }
            if not logger.log_snapshot(minute_num, snapshot):
                raise RuntimeError("SD snapshot logging failed")
            if not valid:
                raise RuntimeError("Invalid sensor state during %s" % mode)
            if temp >= max_safe_temp:
                raise RuntimeError("Temperature safety limit reached: %.2fC" % temp)
            gc.collect()

        status = "completed"
        logger.log_cycle_summary(1, {
            "samples": sample_count,
            "valid_samples": valid_count,
            "invalid_samples": invalid_count,
            "fault_count": fault_count,
            "config_bad_count": config_bad_count,
            "min_temp": min_temp,
            "max_temp": max_temp,
        })
        print("[Soak] PASS: %d/%d valid samples, %.2fC to %.2fC" %
              (valid_count, sample_count, min_temp, max_temp))
        show_screen(int(duration_seconds // cycle_seconds), "PASS", duration_seconds,
                    max_temp, valid_count, invalid_count)
        return True

    except Exception as exc:
        error_message = str(exc)
        print("[Soak] FAILED:", error_message)
        show_screen(0, "FAILED", 0, None, valid_count, invalid_count)
        raise
    finally:
        outputs_off()
        if logger:
            logger.finalize_experiment(status=status, error=error_message)
        try:
            sd_deinit()
        except Exception:
            pass
        try:
            temp_deinit()
        except Exception:
            pass
        gc.collect()


if __name__ == "__main__":
    run()
