# led.py - MOSFET-controlled LED module
from machine import Pin, PWM
import time

# ---- CONFIGURATION ----
DEFAULT_LED_PIN = 25  # Default LED GPIO (change as needed)
PWM_FREQ = 1000  # 1kHz PWM frequency (smooth dimming)

class LED:
    """Class to control an LED using a MOSFET and PWM."""

    def __init__(self, pin=DEFAULT_LED_PIN, freq=PWM_FREQ):  # Modified __init__
        """Initialize the LED with PWM control."""
        self.pwm = PWM(Pin(pin, Pin.OUT))
        self.pwm.freq(freq)
        self.set_brightness(0)  # Start with LED off

    def set_brightness(self, percentage):
        """Set LED brightness (0-100%)."""
        percentage = max(0, min(100, percentage))  # Clamp value
        duty = int((percentage / 100) * 1023)  # Convert to PWM duty cycle (0-1023)
        self.pwm.duty(duty)
        return percentage

    def turn_on(self):
        """Turn LED fully on (100% brightness)."""
        self.set_brightness(100)

    def turn_off(self):
        """Turn LED fully off."""
        self.set_brightness(0)

# ---- TEST CODE ----
if __name__ == "__main__":
    led = LED()
    print("Testing LED control...")

    try:
        while True:
            print("LED: Increasing brightness...")
            for p in range(0, 110, 10):  # Ramp up brightness from 0 to 100%
                led.set_brightness(p)
                print(f"Brightness: {p}%")
                time.sleep(0.5)

            print("LED: Decreasing brightness...")
            for p in range(100, -10, -10):  # Ramp down brightness from 100% to 0%
                led.set_brightness(p)
                print(f"Brightness: {p}%")
                time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nTurning off LED.")
        led.turn_off()