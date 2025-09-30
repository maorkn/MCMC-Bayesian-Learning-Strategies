# heater.py - Module for controlling PTC heater via MOSFET and PWM.
from machine import Pin, PWM
import time

# ---- CONFIGURATION ----
DEFAULT_MOSFET_PIN = 33  # Default GPIO connected to MOSFET Gate
PWM_FREQ = 1000  # 1kHz PWM frequency (restored for smoother control)

class PTCHeater:
    """Class to control PTC heater via MOSFET and PWM."""
    
    def __init__(self, pin=DEFAULT_MOSFET_PIN, freq=PWM_FREQ):  # Modified __init__
        self.pwm = PWM(Pin(pin, Pin.OUT))  # Set pin as PWM output
        self.pwm.freq(freq)  # Set PWM frequency
        self.current_power = 0
        self.turn_off()  # Start with heater off

    def set_power(self, percentage):
        """Set heater power (0-100%)."""
        percentage = max(0, min(100, percentage))  # Limit range
        self.current_power = percentage
        # Convert to 16-bit duty cycle (0-65535) for consistency with TEC
        duty = int((percentage / 100) * 65535)
        self.pwm.duty_u16(duty)
        return percentage

    def turn_off(self):
        """Turn off the heater."""
        self.current_power = 0
        # Explicitly set PWM duty to 0 using both methods for safety
        self.pwm.duty_u16(0)
        self.pwm.duty(0)

# ---- TEST CODE ----
if __name__ == "__main__":
    heater = PTCHeater()

    print("Testing PTC Heater...")
    
    try:
        while True:
            for p in range(0, 110, 10):  # Ramp power from 0 to 100%
                heater.set_power(p)
                print(f"Heater Power: {p}%")
                time.sleep(1)

            for p in range(100, -10, -10):  # Ramp down from 100% to 0%
                heater.set_power(p)
                print(f"Heater Power: {p}%")
                time.sleep(1)

    except KeyboardInterrupt:
        print("\nTurning off heater.")
        heater.turn_off()