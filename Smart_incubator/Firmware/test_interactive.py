# test_interactive.py - Interactive actuator control for Thonny
# Run from Thonny REPL to manually control components

from machine import Pin, PWM
import time
import gc

# Pin definitions
LED_PIN = 25
VIB_PIN = 16
PTC_PIN = 33  # Heater
TEC_PIN = 27  # Cooler

print("Initializing...")

# Initialize PWM for all actuators
led = PWM(Pin(LED_PIN))
led.freq(1000)
led.duty_u16(0)

vib = PWM(Pin(VIB_PIN))
vib.freq(1000)
vib.duty_u16(0)

heater = PWM(Pin(PTC_PIN))
heater.freq(1000)
heater.duty_u16(0)

cooler = PWM(Pin(TEC_PIN))
cooler.freq(1000)
cooler.duty_u16(0)

# Initialize temp sensor
try:
    from max31865 import init_max31865, read_temperature
    init_max31865()
    temp_ok = True
except:
    temp_ok = False
    print("Warning: Temp sensor not available")

# Initialize display
try:
    from oled_display import OLEDDisplay
    display = OLEDDisplay()
    # Direct access to oled for simple text
    oled = display.oled
except:
    display = None
    oled = None

def show(line1, line2=""):
    """Show text on display"""
    if oled:
        oled.fill(0)
        oled.text(line1, 0, 0)
        if line2:
            oled.text(line2, 0, 16)
        oled.show()

# State tracking
state = {'led': False, 'vib': False, 'heater': False, 'cooler': False}

def temp():
    """Read and display temperature"""
    if temp_ok:
        t = read_temperature()
        print(f"Temp: {t:.2f}°C")
        show("Temperature", f"{t:.1f} C")
        return t
    else:
        print("Temp sensor not available")

def led_on(pct=50):
    """Turn LED on (default 50%)"""
    led.duty_u16(int(pct * 655.35))
    state['led'] = True
    print(f"LED ON ({pct}%)")

def led_off():
    """Turn LED off"""
    led.duty_u16(0)
    state['led'] = False
    print("LED OFF")

def vib_on(pct=100):
    """Turn vibration on (default 100%)"""
    vib.duty_u16(int(pct * 655.35))
    state['vib'] = True
    print(f"VIB ON ({pct}%)")

def vib_off():
    """Turn vibration off"""
    vib.duty_u16(0)
    state['vib'] = False
    print("VIB OFF")

def heater_on(pct=30):
    """Turn heater on (default 30% for safety)"""
    heater.duty_u16(int(pct * 655.35))
    state['heater'] = True
    print(f"HEATER ON ({pct}%)")

def heater_off():
    """Turn heater off"""
    heater.duty_u16(0)
    state['heater'] = False
    print("HEATER OFF")

def cooler_on(pct=50):
    """Turn cooler on (default 50%)"""
    cooler.duty_u16(int(pct * 655.35))
    state['cooler'] = True
    print(f"COOLER ON ({pct}%)")

def cooler_off():
    """Turn cooler off"""
    cooler.duty_u16(0)
    state['cooler'] = False
    print("COOLER OFF")

def all_off():
    """Turn everything off"""
    led_off()
    vib_off()
    heater_off()
    cooler_off()
    print("All OFF")

def status():
    """Show current status"""
    print("\n--- STATUS ---")
    if temp_ok:
        print(f"Temp: {read_temperature():.2f}°C")
    print(f"LED:    {'ON' if state['led'] else 'OFF'}")
    print(f"VIB:    {'ON' if state['vib'] else 'OFF'}")
    print(f"HEATER: {'ON' if state['heater'] else 'OFF'}")
    print(f"COOLER: {'ON' if state['cooler'] else 'OFF'}")
    print("--------------\n")

def watch(seconds=30, interval=2):
    """Watch temperature for N seconds"""
    print(f"Watching temp for {seconds}s (Ctrl+C to stop)...")
    try:
        for i in range(seconds // interval):
            t = read_temperature() if temp_ok else 0
            bar = "=" * int(t - 15) if t > 15 else ""
            print(f"[{i*interval:3d}s] {t:.2f}°C {bar}")
            show("Temperature", f"{t:.1f} C")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("Stopped")

def help():
    """Show available commands"""
    print("""
╔═══════════════════════════════════════════╗
║     Interactive Actuator Control          ║
╠═══════════════════════════════════════════╣
║ COMMANDS:                                 ║
║   temp()         - Read temperature       ║
║   watch(60)      - Watch temp for 60s     ║
║                                           ║
║   led_on(50)     - LED on at 50%          ║
║   led_off()      - LED off                ║
║                                           ║
║   vib_on(100)    - Vibration on at 100%   ║
║   vib_off()      - Vibration off          ║
║                                           ║
║   heater_on(30)  - Heater on at 30%       ║
║   heater_off()   - Heater off             ║
║                                           ║
║   cooler_on(50)  - Cooler on at 50%       ║
║   cooler_off()   - Cooler off             ║
║                                           ║
║   all_off()      - Turn everything off    ║
║   status()       - Show current status    ║
║   help()         - Show this message      ║
╚═══════════════════════════════════════════╝
""")

# Show help on start
print("\n✓ Ready!")
help()
status()
