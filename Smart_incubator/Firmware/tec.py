# tec.py - Module for controlling TEC1 cooling system via MOSFET
from machine import Pin, PWM
import time

# ---- CONFIGURATION ----
DEFAULT_MOSFET_PIN = 27  # GPIO for TEC1 MOSFET Gate
PWM_FREQ = 1000  # 1kHz PWM frequency (restored for smoother control)

class TEC1Cooler:
    """Controls the TEC1 cooler."""
    def __init__(self, pin=DEFAULT_MOSFET_PIN):
        self.pwm = PWM(Pin(pin))
        self.pwm.freq(PWM_FREQ)
        self.pwm.duty(0)
        self.is_on = False
        self.current_power = 0

    def set_power(self, power):
        """Set the cooler power (0-100)."""
        if not self.is_on:
            return
            
        # Ensure power is between 0 and 100
        power = max(0, min(100, power))
        self.current_power = power
        
        # Convert power (0-100) to duty cycle (0-65535)
        duty = int((power / 100) * 65535)
        self.pwm.duty_u16(duty)

    def turn_on(self):
        """Turn on the cooler."""
        self.is_on = True
        # Restore previous power setting
        if self.current_power > 0:
            self.set_power(self.current_power)

    def turn_off(self):
        """Turn off the cooler."""
        self.is_on = False
        self.pwm.duty(0)

    def get_status(self):
        """Get current status of the cooler."""
        return {
            "is_on": self.is_on,
            "current_power": self.current_power,
            "duty": self.pwm.duty()
        }

# ---- TEST CODE ----
if __name__ == "__main__":
    cooler = TEC1Cooler()
    print("Testing TEC1 Cooling System...")

    try:
        # First turn it on
        cooler.turn_on()
        
        while True:
            for p in range(0, 110, 10):  # Ramp power from 0 to 100%
                cooler.set_power(p)
                print(f"Cooling Power: {p}%")
                time.sleep(1)

            for p in range(100, -10, -10):  # Ramp down from 100% to 0%
                cooler.set_power(p)
                print(f"Cooling Power: {p}%")
                time.sleep(1)

    except KeyboardInterrupt:
        print("\nTurning off cooler.")
        cooler.turn_off()