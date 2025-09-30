# led_control.py - LED Control Module
from machine import PWM
import time

class LED:
    def __init__(self, pwm):
        """Initialize LED control.
        
        Args:
            pwm: PWM object for LED control
        """
        self.pwm = pwm
        self.is_on_state = False
        self.duty_cycle = 65535  # Full brightness (16-bit)
        
    def turn_on(self):
        """Turn on LED at full brightness."""
        self.pwm.duty_u16(self.duty_cycle)
        self.is_on_state = True
        
    def turn_off(self):
        """Turn off LED."""
        self.pwm.duty_u16(0)
        self.is_on_state = False
        
    def set_brightness(self, brightness):
        """Set LED brightness (0-100).
        
        Args:
            brightness: Brightness percentage (0-100)
        """
        brightness = max(0, min(100, brightness))  # Clamp to 0-100
        duty = int((brightness / 100) * 65535)  # Convert to 16-bit
        self.pwm.duty_u16(duty)
        self.is_on_state = (duty > 0)
        
    def is_on(self):
        """Check if LED is on."""
        return self.is_on_state 