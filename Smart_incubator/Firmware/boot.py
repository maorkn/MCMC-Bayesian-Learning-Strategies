# This is script that run when device boot up or wake from sleep.
import gc
import machine
import time

# Display welcome message
print("Capsaspora Incubator System Booting...")
print("ESP32 MicroPython Firmware")

# STAGE 1: Critical GPIO initialization
print("STAGE 1: Securing GPIO pins...")
try:
    # Initialize all control pins as outputs with safe states
    heater_pin = machine.Pin(33, machine.Pin.OUT)
    cooler_pin = machine.Pin(27, machine.Pin.OUT) 
    led_pin = machine.Pin(25, machine.Pin.OUT)
    vib_pin = machine.Pin(16, machine.Pin.OUT)
    
    # Set all to OFF/LOW state
    heater_pin.value(0)
    cooler_pin.value(0)
    led_pin.value(0)
    vib_pin.value(0)
    
    # Initialize SPI CS pins as outputs and set HIGH (inactive)
    cs_max_pin = machine.Pin(5, machine.Pin.OUT)
    cs_sd_pin = machine.Pin(15, machine.Pin.OUT)
    cs_max_pin.value(1)  # CS pins are active low
    cs_sd_pin.value(1)
    
    print("✓ GPIO pins secured")
    
except Exception as e:
    print(f"⚠ GPIO initialization failed: {e}")
    # Continue anyway - don't let this stop the boot

# STAGE 2: System stabilization
print("STAGE 2: System stabilization...")
time.sleep(0.5)  # Allow hardware to stabilize

# STAGE 3: CPU configuration
print("STAGE 3: CPU configuration...")
try:
    machine.freq(240000000)
    print("✓ CPU frequency set to 240MHz")
except:
    print("⚠ CPU frequency setting failed")

# STAGE 4: Memory management
print("STAGE 4: Memory management...")
gc.enable()
gc.collect()
print("✓ Memory cleanup completed")

# STAGE 5: Final stabilization
print("STAGE 5: Final stabilization...")
time.sleep(1.0)  # Longer delay for complete system stabilization

# BOOT button check temporarily disabled for external power compatibility
# Uncomment the section below if you need update mode functionality

# # Check if BOOT button is pressed to enter update mode
# # Use multiple readings to avoid false triggers from floating pins
# boot_pin = machine.Pin(0, machine.Pin.IN, machine.Pin.PULL_UP)
# time.sleep(0.1)  # Allow pin to stabilize
# 
# # Take multiple readings to confirm button state
# boot_pressed_count = 0
# for i in range(5):
#     if not boot_pin.value():  # BOOT button is pressed (active low)
#         boot_pressed_count += 1
#     time.sleep(0.02)  # 20ms between readings
# 
# # Only enter update mode if button is consistently pressed
# if boot_pressed_count >= 4:  # At least 4 out of 5 readings show pressed
#     print("\n=== UPDATE MODE ===")
#     print("BOOT button detected - entering update mode")
#     print("You can now update files via REPL")
#     print("Press Ctrl+D to restart when done")
#     print("===================")
#     # Don't run main, just stay in REPL
# else:

# Boot sequence complete
print("\n=== Boot Sequence Complete ===")
print("✓ All stages completed successfully")
print("✓ System ready for main program")
print("=== Starting Web Server Mode ===\n")

# Start the main program
time.sleep(0.5)
print("Starting Main Program...")

try:
    # Run the working main program
    import main
    main.main()
except Exception as e:
    print(f"Main program error: {e}")
    print("System will remain in REPL mode")
    # Do not automatically restart - just exit to REPL


