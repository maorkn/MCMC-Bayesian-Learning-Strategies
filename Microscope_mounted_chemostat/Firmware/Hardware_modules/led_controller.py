# led_controller.py - LED Pair PWM Controller
from machine import Pin, PWM
import utime

class LEDController:
    """Controls LED pair with PWM and duration-based operation."""
    
    def __init__(self, pin, frequency=1000):
        """
        Initialize LED controller.
        
        Args:
            pin: GPIO pin number for PWM output
            frequency: PWM frequency in Hz
        """
        self.pin = pin
        self.frequency = frequency
        
        # Initialize PWM
        self.pwm = PWM(Pin(pin, Pin.OUT))
        self.pwm.freq(frequency)
        self.pwm.duty(0)  # Start off
        
        # State tracking
        self.current_duty = 0  # Current PWM duty cycle (0-100%)
        self.is_on = False
        self.start_time = 0
        self.target_duration = 0
        self.total_on_time_sec = 0  # Total time LED has been on
        
        print(f"[LED] Initialized on GPIO {pin} @ {frequency}Hz")
    
    def set_duty(self, duty_percent):
        """Set PWM duty cycle (0-100%)."""
        duty_percent = max(0, min(100, duty_percent))  # Clamp to valid range
        
        # Convert percentage to PWM duty value (0-1023 for 10-bit)
        pwm_duty = int((duty_percent / 100.0) * 1023)
        
        self.pwm.duty(pwm_duty)
        self.current_duty = duty_percent
        
        if duty_percent > 0:
            if not self.is_on:
                self.start_time = utime.ticks_ms()
                self.is_on = True
        else:
            self.turn_off()
    
    def turn_on(self, duty_percent, duration_sec=0):
        """
        Turn on LED with specified duty cycle.
        
        Args:
            duty_percent: PWM duty cycle (0-100%)
            duration_sec: Duration to stay on (0 = indefinite)
        """
        self.target_duration = duration_sec * 1000 if duration_sec > 0 else 0  # Convert to ms
        self.set_duty(duty_percent)
        
        if duration_sec > 0:
            print(f"[LED] On: {duty_percent}% for {duration_sec}s")
        else:
            print(f"[LED] On: {duty_percent}% (indefinite)")
        
        return True
    
    def turn_off(self):
        """Turn off LED and update on-time tracking."""
        if self.is_on:
            # Calculate total on time
            elapsed_ms = utime.ticks_diff(utime.ticks_ms(), self.start_time)
            self.total_on_time_sec += elapsed_ms / 1000.0
            
            print(f"[LED] Off. On time: {elapsed_ms/1000.0:.1f}s (Total: {self.total_on_time_sec:.1f}s)")
        
        self.pwm.duty(0)
        self.current_duty = 0
        self.is_on = False
        self.start_time = 0
        self.target_duration = 0
    
    def update(self):
        """Update LED state - call periodically to handle duration timeout."""
        if not self.is_on or self.target_duration == 0:
            return
        
        elapsed_ms = utime.ticks_diff(utime.ticks_ms(), self.start_time)
        
        # Check if duration expired
        if elapsed_ms >= self.target_duration:
            self.turn_off()
    
    def pulse(self, duty_percent, pulse_duration_sec, pulse_count=1, pulse_interval_sec=0.5):
        """
        Create pulsing pattern (for future use).
        Note: This is a blocking operation for simplicity.
        """
        for i in range(pulse_count):
            self.turn_on(duty_percent)
            utime.sleep(pulse_duration_sec)
            self.turn_off()
            
            if i < pulse_count - 1:  # Don't wait after last pulse
                utime.sleep(pulse_interval_sec)
    
    def get_status(self):
        """Get LED status dictionary."""
        current_on_time = 0.0
        
        if self.is_on:
            current_on_time = utime.ticks_diff(utime.ticks_ms(), self.start_time) / 1000.0
        
        return {
            "duty_percent": self.current_duty,
            "is_on": self.is_on,
            "current_on_time_sec": current_on_time,
            "total_on_time_sec": self.total_on_time_sec,
            "target_duration_sec": self.target_duration / 1000.0 if self.target_duration > 0 else 0
        }
    
    def reset_on_time(self):
        """Reset total on-time counter."""
        old_time = self.total_on_time_sec
        self.total_on_time_sec = 0.0
        print(f"[LED] On-time counter reset (was {old_time:.1f}s)")
    
    def emergency_stop(self):
        """Emergency stop - immediate shutdown."""
        self.pwm.duty(0)
        self.current_duty = 0
        self.is_on = False
        self.start_time = 0
        self.target_duration = 0
        print("[LED] EMERGENCY STOP")


# ================== QUEUE-BASED LED CONTROLLER ==================

class QueuedLEDController(LEDController):
    """LED controller with command queue capability."""
    
    def __init__(self, pin, frequency=1000, max_queue=5):
        super().__init__(pin, frequency)
        self.command_queue = []
        self.max_queue = max_queue
        self.current_command = None
    
    def queue_command(self, duty_percent, duration_sec, command_id=None):
        """Queue an LED command."""
        if len(self.command_queue) >= self.max_queue:
            print("[LED] Queue full")
            return False
        
        # Validate parameters
        duty_percent = max(0, min(100, duty_percent))
        duration_sec = max(0, min(3600, duration_sec))  # Max 1 hour
        
        command = {
            "duty": duty_percent,
            "duration": duration_sec,
            "command_id": command_id or f"led_cmd_{utime.ticks_ms()}",
            "queued_time": utime.ticks_ms()
        }
        
        self.command_queue.append(command)
        print(f"[LED] Queued: {duty_percent}% for {duration_sec}s")
        return True
    
    def update(self):
        """Update LED state and process queued commands."""
        # Call parent update for duration handling
        super().update()
        
        # Start next queued command if LED is off
        if not self.is_on and self.command_queue:
            self.current_command = self.command_queue.pop(0)  # FIFO
            self.turn_on(self.current_command["duty"], self.current_command["duration"])
    
    def get_status(self):
        """Get enhanced status with queue information."""
        status = super().get_status()
        status.update({
            "queue_length": len(self.command_queue),
            "current_command_id": self.current_command.get("command_id") if self.current_command else None
        })
        return status
    
    def emergency_stop(self):
        """Emergency stop - clear queue and stop LED."""
        super().emergency_stop()
        self.command_queue.clear()
        self.current_command = None
        print("[LED] EMERGENCY STOP - Queue cleared")


# ================== TEST CODE ==================
if __name__ == "__main__":
    # Test basic LED controller
    led = LEDController(pin=33)
    
    print("Testing LED...")
    led.turn_on(75, 3)  # 75% duty for 3 seconds
    
    for i in range(8):
        led.update()
        status = led.get_status()
        print(f"Status: {status}")
        utime.sleep(1)
    
    # Test queued LED controller
    print("\nTesting queued LED...")
    queued_led = QueuedLEDController(pin=33)
    
    # Queue multiple commands
    queued_led.queue_command(50, 2)
    queued_led.queue_command(100, 1)
    queued_led.queue_command(25, 3)
    
    for i in range(15):
        queued_led.update()
        status = queued_led.get_status()
        print(f"Queued Status: {status}")
        utime.sleep(1) 