# vibration_control.py - Vibration Control Module
from machine import PWM
import time

class Vibration:
    def __init__(self, pwm):
        """Initialize vibration control.
        
        Args:
            pwm: PWM object for vibration control
        """
        self.pwm = pwm
        self.is_on_state = False
        self.duty_cycle = 65535  # Full intensity
        self.last_cycle_start = 0
        self.cycle_period = 300  # 5 minutes total cycle (1min on + 4min off)
        self.on_time = 60  # 1 minute on time
        
    def start(self):
        """Start vibration with 1min on, 4min off pattern."""
        self.last_cycle_start = time.time()
        self.is_on_state = True
        self._update_duty_cycle()
        
    def stop(self):
        """Stop vibration."""
        self.pwm.duty_u16(0)
        self.is_on_state = False
        
    def set_intensity(self, intensity):
        """Set vibration intensity (0-100).
        
        Args:
            intensity: Vibration intensity percentage (0-100)
        """
        intensity = max(0, min(100, intensity))  # Clamp to 0-100
        self.duty_cycle = int((intensity / 100) * 65535)
        if self.is_on_state:
            self._update_duty_cycle()
        
    def is_on(self):
        """Check if vibration is active."""
        return self.is_on_state
        
    def _update_duty_cycle(self):
        """Update PWM duty cycle based on current time in cycle."""
        if not self.is_on_state:
            return
            
        current_time = time.time()
        time_in_cycle = (current_time - self.last_cycle_start) % self.cycle_period
        
        if time_in_cycle < self.on_time:
            # On period (first minute)
            self.pwm.duty_u16(self.duty_cycle)
        else:
            # Off period (remaining 4 minutes)
            self.pwm.duty_u16(0)
            
    def update(self):
        """Update vibration state based on current time.
        Should be called periodically in the main loop."""
        if self.is_on_state:
            self._update_duty_cycle() 