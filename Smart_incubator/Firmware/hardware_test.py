# hardware_test.py - Short unit preflight for Smart Incubator
from machine import Pin, PWM
import gc
import time

# Keep this module separate from main.py so normal experiments do not pay the
# RAM cost unless hardware-test mode is selected from the setup AP.

TEC_PIN = 27
LED_PIN = 25
VIB_PIN = 16
PTC_PIN = 33


def _clamp_percent(value):
    return max(0, min(100, int(value)))


def _init_output_pins():
    led_pwm = PWM(Pin(LED_PIN))
    vib_pwm = PWM(Pin(VIB_PIN))
    for pwm in (led_pwm, vib_pwm):
        pwm.freq(1000)
        pwm.duty_u16(0)
    return led_pwm, vib_pwm


def _init_display():
    try:
        from oled_display import OLEDDisplay

        display = OLEDDisplay()
        if display and getattr(display, "oled", None):
            print("[System] OLED display initialized successfully")
            return display
    except Exception as e:
        print(f"[WARNING] OLED display initialization failed: {e}")
    return None


def _init_temp_sensor():
    from max31865 import init_max31865

    return init_max31865()


def _read_temp_safe():
    try:
        from max31865 import read_temperature

        return read_temperature()
    except Exception:
        return None


def _init_us_controller(led_pwm, vib_pwm):
    from led_control import LED
    from vibration_control import Vibration
    from us_control import USController

    return USController(LED(led_pwm), Vibration(vib_pwm))


def _init_temp_controller():
    from temp_controller import TempController

    return TempController(PTC_PIN, TEC_PIN, kp=6.0, ki=0.02, kd=1.5)


def _reset_temp_sensor():
    """Drop and rebuild the MAX31865 SPI state after noisy actuator steps."""
    try:
        from max31865 import deinit

        deinit()
    except Exception:
        pass
    gc.collect()
    time.sleep(2)
    return _init_temp_sensor()


def run_hardware_test(config):
    """Run a short unit preflight from the AP setup server."""
    step_duration = int(config.get("step_duration_seconds", 30))
    led_intensity = _clamp_percent(config.get("led_intensity", 50))
    vib_intensity = _clamp_percent(config.get("vib_intensity", 100))
    cooler_power = _clamp_percent(config.get("cooler_power", 50))
    heater_power = _clamp_percent(config.get("heater_power", 30))
    max_safe_temp = 40.0

    display = None
    temp_ctrl = None
    us_controller = None
    led_pwm = None
    vib_pwm = None
    preflight_failures = []

    def show_test_status(step_name, remaining=None, detail="", temp_text=""):
        if not display or not getattr(display, "oled", None):
            return
        try:
            display.oled.fill(0)
            display.oled.text("HARDWARE TEST", 0, 0)
            display.oled.text(step_name[:16], 0, 12)
            if detail:
                display.oled.text(detail[:16], 0, 24)
            if remaining is not None:
                display.oled.text(f"Left: {int(remaining)}s", 0, 36)
            if temp_text:
                display.oled.text(temp_text[:16], 0, 48)
            display.oled.show()
        except Exception:
            pass

    def record_preflight(name, ok, detail=""):
        status = "OK" if ok else "FAIL"
        message = f"[Hardware Test] {name}: {status}"
        if detail:
            message += f" ({detail})"
        print(message)
        show_test_status(f"Check {name}", None, status)
        if not ok:
            preflight_failures.append(name)
        time.sleep(1)

    def all_outputs_off():
        if us_controller:
            try:
                us_controller.deactivate("BOTH")
            except Exception:
                pass
        if temp_ctrl:
            try:
                temp_ctrl.heater.turn_off()
                temp_ctrl.cooler.turn_off()
            except Exception:
                pass
        if led_pwm:
            led_pwm.duty_u16(0)
        if vib_pwm:
            vib_pwm.duty_u16(0)

    def test_oled():
        nonlocal display
        display = _init_display()
        if not display:
            record_preflight("OLED", False, "not detected")
            return False
        try:
            display.oled.fill(0)
            display.oled.text("OLED OK", 0, 0)
            display.oled.text("Preflight", 0, 18)
            display.oled.show()
            record_preflight("OLED", True)
            return True
        except Exception as e:
            record_preflight("OLED", False, str(e))
            return False

    def test_temp_sensor():
        try:
            if not _init_temp_sensor():
                record_preflight("Temp Sensor", False, "init failed")
                return False
            temp = _read_temp_safe()
            if temp is None:
                record_preflight("Temp Sensor", False, "read failed")
                return False
            record_preflight("Temp Sensor", True, f"{temp:.1f}C")
            return True
        except Exception as e:
            record_preflight("Temp Sensor", False, str(e))
            return False

    def test_sd_card():
        try:
            import os
            from sd_logger import init_sd, deinit as sd_deinit

            if not init_sd():
                try:
                    sd_deinit()
                except Exception:
                    pass
                record_preflight("SD Card", False, "mount failed")
                return False

            test_path = "/sd/hardware_test.tmp"
            with open(test_path, "w") as f:
                f.write("ok")
            with open(test_path, "r") as f:
                data = f.read()
            try:
                os.remove(test_path)
            except Exception:
                pass
            try:
                sd_deinit()
            except Exception:
                pass

            if data != "ok":
                record_preflight("SD Card", False, "readback mismatch")
                return False
            record_preflight("SD Card", True, "write/read")
            return True
        except Exception as e:
            try:
                from sd_logger import deinit as sd_deinit

                sd_deinit()
            except Exception:
                pass
            record_preflight("SD Card", False, str(e))
            return False

    def run_step(name, display_step, level_text, activate, deactivate, monitor_temp=True):
        print(f"[Hardware Test] {name} ON for {step_duration}s")
        activate()
        start = time.time()
        try:
            while time.time() - start < step_duration:
                remaining = step_duration - (time.time() - start)
                if monitor_temp:
                    temp = _read_temp_safe()
                    if temp is not None:
                        print(f"[Hardware Test] {name}: {temp:.1f}C, {int(remaining)}s left")
                        if temp >= max_safe_temp:
                            raise RuntimeError(f"temperature safety limit reached ({temp:.1f}C)")
                        temp_text = f"Temp: {temp:.1f}C"
                    else:
                        print(f"[Hardware Test] {name}: {int(remaining)}s left")
                        temp_text = "Temp: unavailable"
                else:
                    print(f"[Hardware Test] {name}: {int(remaining)}s left")
                    temp_text = "Temp: paused"
                show_test_status(display_step, remaining, level_text, temp_text)
                time.sleep(1)
        finally:
            deactivate()
            all_outputs_off()
            print(f"[Hardware Test] {name} OFF")
            time.sleep(1)

    print("\n[Hardware Test] Initializing unit preflight...")
    print(f"[Hardware Test] Step duration: {step_duration}s")
    print(f"[Hardware Test] LED {led_intensity}% | VIB {vib_intensity}% | Cool {cooler_power}% | Heat {heater_power}%")

    try:
        led_pwm, vib_pwm = _init_output_pins()

        test_oled()
        temp_sensor_ok = test_temp_sensor()
        test_sd_card()

        us_controller = _init_us_controller(led_pwm, vib_pwm)
        us_controller.set_led_intensity(led_intensity)
        us_controller.set_vib_intensity(vib_intensity)
        us_controller.set_vib_interval(f"{step_duration}:0")

        all_outputs_off()
        show_test_status("Starting", step_duration, "Preparing outputs")

        run_step(
            "LED",
            "1/4 LED",
            f"Level: {led_intensity}%",
            lambda: us_controller.activate("LED"),
            lambda: us_controller.deactivate("LED"),
            monitor_temp=False,
        )
        run_step(
            "Vibration",
            "2/4 Vibration",
            f"Level: {vib_intensity}%",
            lambda: us_controller.activate("VIB"),
            lambda: us_controller.deactivate("VIB"),
            monitor_temp=False,
        )

        if temp_sensor_ok:
            print("[Hardware Test] Rechecking temperature sensor after LED/VIB")
            if not _reset_temp_sensor():
                record_preflight("Temp After US", False, "reinit failed")
                temp_sensor_ok = False

        if temp_sensor_ok:
            temp_ctrl = _init_temp_controller()
            run_step(
                "Cooling",
                "3/4 Cooling",
                f"Power: {cooler_power}%",
                lambda: (
                    temp_ctrl.heater.turn_off(),
                    temp_ctrl.cooler.turn_on(),
                    temp_ctrl.cooler.set_power(cooler_power),
                ),
                lambda: temp_ctrl.cooler.turn_off(),
            )
            run_step(
                "Heating",
                "4/4 Heating",
                f"Power: {heater_power}%",
                lambda: (
                    temp_ctrl.cooler.turn_off(),
                    temp_ctrl.heater.set_power(heater_power),
                ),
                lambda: temp_ctrl.heater.turn_off(),
            )
        else:
            print("[Hardware Test] Skipping cooling/heating because temperature sensing failed")

        if preflight_failures:
            show_test_status("Result: FAILED", None, "Check console")
            raise RuntimeError("preflight failures: " + ", ".join(preflight_failures))
        show_test_status("Result: PASS", None, "All checks OK")
        print("\n[Hardware Test] Completed successfully!")
        return True

    except Exception as e:
        show_test_status("Result: FAILED", None, "Check console")
        print(f"\n[Hardware Test] Failed: {e}")
        raise
    finally:
        all_outputs_off()
        try:
            from sd_logger import deinit as sd_deinit

            sd_deinit()
        except Exception:
            pass
        gc.collect()
