# us_control.py - Unconditional Stimulus Control Module
from led import LED
from vibration_control import Vibration
from machine import PWM, Pin
import time

class USController:
    def __init__(self, led_obj, vib_obj):
        """Initialize US controller with LED and vibration objects."""
        self.led = led_obj
        self.vib = vib_obj
        self.led_intensity = 25  # Default LED intensity (0-100)
        self.vib_intensity = 100  # Default vibration intensity (0-100)
        self.is_active = False
        self.last_vib_toggle = 0
        self.vib_on_time = 20  # Default on time in seconds
        self.vib_off_time = 60  # Default off time in seconds
        
        # Use the PWM object from the vibration object
        self.vib_pwm = self.vib.pwm

    def set_led_intensity(self, intensity):
        """Set LED intensity (0-100)."""
        self.led_intensity = max(0, min(100, intensity))
        if self.is_active and self.led:
            # Use LED class method instead of direct PWM
            self.led.set_brightness(self.led_intensity)

    def set_vib_intensity(self, intensity):
        """Set vibration intensity (0-100)."""
        self.vib_intensity = max(0, min(100, intensity))
        if self.is_active:
            # Convert percentage to 16-bit PWM value
            pwm_value = int((self.vib_intensity / 100) * 65535)
            self.vib_pwm.duty_u16(pwm_value)

    def set_vib_interval(self, interval):
        """Set vibration interval in format 'ON:OFF' (seconds)."""
        try:
            on_time, off_time = map(int, interval.split(':'))
            if on_time < 0 or off_time < 0:
                raise ValueError("Interval times must be positive")
            self.vib_on_time = on_time
            self.vib_off_time = off_time
            self.last_vib_toggle = time.time()  # Reset timer when changing interval
        except Exception as e:
            print(f"Invalid interval format. Use 'ON:OFF' in seconds. Error: {e}")

    def update_vibration(self):
        """Update vibration state based on interval timing."""
        if not self.is_active:
            return

        current_time = time.time()
        time_since_toggle = current_time - self.last_vib_toggle

        if self.vib_pwm.duty_u16() > 0:  # Vibration is on
            if time_since_toggle >= self.vib_on_time:
                self.vib_pwm.duty_u16(0)  # Turn off
                self.last_vib_toggle = current_time
        else:  # Vibration is off
            if time_since_toggle >= self.vib_off_time:
                # Turn on with current intensity
                pwm_value = int((self.vib_intensity / 100) * 65535)
                self.vib_pwm.duty_u16(pwm_value)
                self.last_vib_toggle = current_time

    def activate(self, us_type="BOTH", reset_timing=True):
        """Activate US with specified type and current settings.
        
        Args:
            us_type: Type of US to activate ("LED", "VIB", or "BOTH")
            reset_timing: If True, reset vibration timing. Set to False when
                          resuming after a brief pause (e.g., during logging)
        """
        was_active = self.is_active
        self.is_active = True
        
        # Only reset timing if this is a fresh activation, not a resume
        if reset_timing and not was_active:
            self.last_vib_toggle = time.time()
        
        if us_type in ["LED", "BOTH"] and self.led:
            # Use LED class method instead of direct PWM
            self.led.set_brightness(self.led_intensity)
            
        if us_type in ["VIB", "BOTH"]:
            # Start vibration with current intensity
            pwm_value = int((self.vib_intensity / 100) * 65535)
            self.vib_pwm.duty_u16(pwm_value)
            
        return 1, 1

    def deactivate(self, us_type="BOTH"):
        """Deactivate US with specified type."""
        self.is_active = False
        
        if us_type in ["LED", "BOTH"] and self.led:
            # Use LED class method to turn off
            self.led.turn_off()
            
        if us_type in ["VIB", "BOTH"]:
            self.vib_pwm.duty_u16(0)  # Turn off vibration
            
        return 0, 0

    def test(self, us_type="BOTH", duration=10, led_intensity=None, vib_intensity=None, vib_interval=None):
        """Test US with specified parameters.
        
        Args:
            us_type (str): Type of US to test ("LED", "VIB", or "BOTH")
            duration (int): Test duration in seconds
            led_intensity (int): LED intensity (0-100)
            vib_intensity (int): Vibration intensity (0-100)
            vib_interval (str): Vibration interval in "ON:OFF" format
        """
        print(f"\n=== Testing US Type: {us_type} ===")
        
        # Store original settings
        original_led_intensity = self.led_intensity
        original_vib_intensity = self.vib_intensity
        original_on_time = self.vib_on_time
        original_off_time = self.vib_off_time
        
        try:
            # Apply test settings
            if led_intensity is not None:
                print(f"Setting LED intensity to {led_intensity}%")
                self.set_led_intensity(led_intensity)
                
            if vib_intensity is not None:
                print(f"Setting vibration intensity to {vib_intensity}%")
                self.set_vib_intensity(vib_intensity)
                
            if vib_interval is not None:
                print(f"Setting vibration interval to {vib_interval}")
                self.set_vib_interval(vib_interval)
            
            # Print current settings
            print("\nCurrent Settings:")
            print(f"LED Intensity: {self.led_intensity}%")
            print(f"Vibration Intensity: {self.vib_intensity}%")
            print(f"Vibration Interval: {self.vib_on_time}:{self.vib_off_time}")
            
            # Activate US
            print(f"\nActivating {us_type} for {duration} seconds...")
            self.activate(us_type)
            
            # Wait for duration, updating vibration if needed
            start_time = time.time()
            while time.time() - start_time < duration:
                if us_type in ["VIB", "BOTH"]:
                    self.update_vibration()
                time.sleep(0.1)  # Small delay to prevent CPU hogging
            
            # Deactivate
            print("\nDeactivating...")
            self.deactivate(us_type)
            
        finally:
            # Restore original settings
            print("\nRestoring original settings...")
            self.set_led_intensity(original_led_intensity)
            self.set_vib_intensity(original_vib_intensity)
            self.vib_on_time = original_on_time
            self.vib_off_time = original_off_time
            
        print("\nTest complete!")

# For backward compatibility
def activate_us(led_obj, vib_obj):
    """Legacy function for backward compatibility."""
    controller = USController(led_obj, vib_obj)
    return controller.activate()

def deactivate_us(led_obj, vib_obj):
    """Legacy function for backward compatibility."""
    controller = USController(led_obj, vib_obj)
    return controller.deactivate()

# Test code
if __name__ == "__main__":
    # Create test instances
    test_led = LED(25)  # LED on pin 25
    test_vib = Vibration(16)  # Vibration on pin 16
    
    # Create controller
    controller = USController(test_led, test_vib)
    
    # Run tests
    print("\nRunning US tests...")
    
    # Test LED only
    controller.test(
        us_type="LED",
        duration=5,
        led_intensity=25
    )
    
    # Test Vibration only
    controller.test(
        us_type="VIB",
        duration=15,
        vib_intensity=100,
        vib_interval="2:3"
    )
    
    # Test both
    controller.test(
        us_type="BOTH",
        duration=15,
        led_intensity=100,
        vib_intensity=100,
        vib_interval="2:3"
    ) 