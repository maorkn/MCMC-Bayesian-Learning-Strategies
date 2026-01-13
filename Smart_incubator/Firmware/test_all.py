# test_all.py - Simple actuator test script for Thonny
# Run this directly from Thonny REPL to test all components

from machine import Pin, PWM
import time
import gc

# Pin definitions
LED_PIN = 25
VIB_PIN = 16
PTC_PIN = 33  # Heater
TEC_PIN = 27  # Cooler

print("=" * 40)
print("Smart Incubator Component Test")
print("=" * 40)

# === TEST 1: OLED Display ===
print("\n[1/6] Testing OLED Display...")
try:
    from oled_display import OLEDDisplay
    display = OLEDDisplay()
    display.show_message("Test Mode", "Starting...")
    print("  ✓ Display OK")
    time.sleep(1)
except Exception as e:
    print(f"  ✗ Display FAILED: {e}")
    display = None

gc.collect()

# === TEST 2: Temperature Sensor ===
print("\n[2/6] Testing Temperature Sensor...")
try:
    from max31865 import init_max31865, read_temperature
    if init_max31865():
        temp = read_temperature()
        print(f"  ✓ Temp Sensor OK: {temp:.1f}°C")
        if display:
            display.show_message("Temp Sensor", f"{temp:.1f} C")
    else:
        print("  ✗ Temp Sensor init failed")
    time.sleep(1)
except Exception as e:
    print(f"  ✗ Temp Sensor FAILED: {e}")

gc.collect()

# === TEST 3: SD Card ===
print("\n[3/6] Testing SD Card...")
try:
    from sd_logger import init_sd
    if init_sd():
        print("  ✓ SD Card OK")
        if display:
            display.show_message("SD Card", "OK")
    else:
        print("  ✗ SD Card init failed")
    time.sleep(1)
except Exception as e:
    print(f"  ✗ SD Card FAILED: {e}")

gc.collect()

# === TEST 4: LED ===
print("\n[4/6] Testing LED...")
try:
    led_pwm = PWM(Pin(LED_PIN))
    led_pwm.freq(1000)
    
    if display:
        display.show_message("LED Test", "ON...")
    
    print("  LED ON (50%)")
    led_pwm.duty_u16(32768)  # 50%
    time.sleep(2)
    
    print("  LED OFF")
    led_pwm.duty_u16(0)
    print("  ✓ LED OK")
    time.sleep(0.5)
except Exception as e:
    print(f"  ✗ LED FAILED: {e}")

gc.collect()

# === TEST 5: Vibration Motor ===
print("\n[5/6] Testing Vibration Motor...")
try:
    vib_pwm = PWM(Pin(VIB_PIN))
    vib_pwm.freq(1000)
    
    if display:
        display.show_message("Vibration", "ON...")
    
    print("  Vibration ON (100%)")
    vib_pwm.duty_u16(65535)  # 100%
    time.sleep(2)
    
    print("  Vibration OFF")
    vib_pwm.duty_u16(0)
    print("  ✓ Vibration OK")
    time.sleep(0.5)
except Exception as e:
    print(f"  ✗ Vibration FAILED: {e}")

gc.collect()

# === TEST 6: Heater (PTC) ===
print("\n[6/6] Testing Heater...")
try:
    heater_pwm = PWM(Pin(PTC_PIN))
    heater_pwm.freq(1000)
    
    if display:
        display.show_message("Heater", "ON 30%...")
    
    print("  Heater ON (30% - safe)")
    heater_pwm.duty_u16(19660)  # ~30%
    time.sleep(3)
    
    print("  Heater OFF")
    heater_pwm.duty_u16(0)
    heater_pwm.deinit()
    Pin(PTC_PIN, Pin.OUT).value(0)
    print("  ✓ Heater OK")
    time.sleep(0.5)
except Exception as e:
    print(f"  ✗ Heater FAILED: {e}")

gc.collect()

# === TEST 7: Cooler (TEC) ===
print("\n[7/7] Testing Cooler...")
try:
    cooler_pwm = PWM(Pin(TEC_PIN))
    cooler_pwm.freq(1000)
    
    if display:
        display.show_message("Cooler", "ON 50%...")
    
    print("  Cooler ON (50%)")
    cooler_pwm.duty_u16(32768)  # 50%
    time.sleep(3)
    
    print("  Cooler OFF")
    cooler_pwm.duty_u16(0)
    cooler_pwm.deinit()
    Pin(TEC_PIN, Pin.OUT).value(0)
    print("  ✓ Cooler OK")
    time.sleep(0.5)
except Exception as e:
    print(f"  ✗ Cooler FAILED: {e}")

# === DONE ===
print("\n" + "=" * 40)
print("All tests complete!")
print("=" * 40)

if display:
    display.show_message("Tests Done", "All complete!")

# Ensure all pins are OFF
Pin(LED_PIN, Pin.OUT).value(0)
Pin(VIB_PIN, Pin.OUT).value(0)
Pin(PTC_PIN, Pin.OUT).value(0)
Pin(TEC_PIN, Pin.OUT).value(0)

print("\nAll actuators turned OFF")
print("Free memory:", gc.mem_free(), "bytes")
