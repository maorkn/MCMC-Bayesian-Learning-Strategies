# temp_controller.py - Updated for spi.py with PWM Interference Protection
from heater import PTCHeater
from tec import TEC1Cooler
from max31865 import read_temperature, init_max31865  # Updated import
from temperature_failsafe import TemperatureFailsafe
import time

class PIDController:
    """PID controller for temperature regulation."""
    def __init__(self, kp, ki, kd, max_output=100, min_output=-100):  # Changed to -100 to 100 range
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.max_output = max_output
        self.min_output = min_output
        self.prev_error = 0
        self.integral = 0
        self.max_integral = 200  # Adjusted for new range

    def compute(self, setpoint, measured_value):
        error = setpoint - measured_value
        self.integral += error
        self.integral = max(-self.max_integral, min(self.max_integral, self.integral))
        derivative = error - self.prev_error
        self.prev_error = error
        output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)
        return max(self.min_output, min(self.max_output, output))

class TempController:
    """Controls temperature using a PID controller, heater, and cooler."""

    def __init__(self, heater_pin, cooler_pin, kp=20.0, ki=0, kd=0):
        """Initializes the temperature controller."""
        if not init_max31865():
            raise RuntimeError("Failed to initialize temperature sensor")
            
        self.heater = PTCHeater(pin=heater_pin)
        self.cooler = TEC1Cooler(pin=cooler_pin)
        self.pid = PIDController(kp=kp, ki=ki, kd=kd, max_output=100, min_output=-100)
        self.last_target = 23.0
        self.last_valid_temp = None
        self.temp_read_errors = 0
        self.max_temp_errors = 5
        
        # Initialize failsafe system
        self.failsafe = TemperatureFailsafe(
            stuck_threshold_seconds=120,  # 2 minutes as requested
            max_temp_limit=45.0,          # Maximum safe temperature
            enable_emergency_shutdown=True
        )
        
        self.cooler.turn_off()

    def control_temp(self, target_temp):
        """
        Adjusts heater and cooler power to maintain target temperature.
        """
        try:
            if abs(target_temp - self.last_target) > 2.0:
                print(f"[DEBUG] Target temp changed significantly: {self.last_target:.1f}°C -> {target_temp:.1f}°C")
                print(f"[DEBUG] Resetting PID integral to prevent windup")
                self.pid.integral = 0
                self.pid.prev_error = 0
                self.last_target = target_temp

            current_temp = None
            for attempt in range(3):
                try:
                    temp_reading = read_temperature()
                    
                    if temp_reading is not None and -50 <= temp_reading <= 100:
                        if self.last_valid_temp is not None:
                            temp_change = abs(temp_reading - self.last_valid_temp)
                            if temp_change > 10.0:
                                print(f"[WARNING] Large temperature change detected: {temp_change:.1f}°C")
                                if attempt < 2:
                                    time.sleep_ms(100)
                                    continue
                        
                        current_temp = temp_reading
                        self.last_valid_temp = current_temp
                        self.temp_read_errors = 0
                        break
                    else:
                        if attempt < 2:
                            time.sleep_ms(100)
                except Exception as e:
                    print(f"[ERROR] Temperature read attempt {attempt + 1} failed: {e}")
                    if attempt < 2:
                        time.sleep_ms(100)

            if current_temp is None:
                self.temp_read_errors += 1
                print(f"[ERROR] Failed to get valid temperature after 3 attempts (errors: {self.temp_read_errors})")
                
                if self.last_valid_temp is not None and self.temp_read_errors < self.max_temp_errors:
                    print(f"[WARNING] Using last valid temperature: {self.last_valid_temp:.1f}°C")
                    current_temp = self.last_valid_temp
                else:
                    print("[ERROR] No valid temperature available, stopping control")
                    return None, 0, "Error"
            
            temp_diff = current_temp - target_temp
            
            power = self.pid.compute(target_temp, current_temp)
            actual_power = power

            # When idle, ensure both heater and cooler are off.
            if -0.1 <= temp_diff <= 0.5:
                self.heater.turn_off()
                self.cooler.turn_off()
                return current_temp, 0, "Idle"
            
            if power > 0:
                self.cooler.turn_off()
                self.heater.set_power(power)
                mode = "Heating"
            elif power < 0:
                self.heater.turn_off()
                pid_power = abs(power)
                cooling_power = min(100, pid_power + 35)
                self.cooler.turn_on()
                self.cooler.set_power(cooling_power)
                actual_power = -cooling_power
                mode = "Cooling"
            
            # CRITICAL FAILSAFE CHECK - Prevent overheating from stuck sensors
            is_safe, failsafe_action, failsafe_message = self.failsafe.check_temperature(
                current_temp, 
                self.heater.current_power if hasattr(self.heater, 'current_power') else (actual_power if actual_power > 0 else 0),
                self.cooler.current_power if hasattr(self.cooler, 'current_power') else (abs(actual_power) if actual_power < 0 else 0)
            )
            
            if not is_safe:
                print(f"[EMERGENCY] FAILSAFE TRIGGERED: {failsafe_message}")
                
                # Emergency shutdown - turn off all heating/cooling immediately
                self.heater.turn_off()
                self.cooler.turn_off()
                
                if failsafe_action == "emergency_stop":
                    # This is critical - raise an exception to stop the entire system
                    raise RuntimeError(f"EMERGENCY SHUTDOWN: {failsafe_message}")
                
            elif failsafe_action == "warning":
                print(f"[FAILSAFE WARNING] {failsafe_message}")
            
            return current_temp, actual_power, mode
            
        except Exception as e:
            print(f"[ERROR] Temperature control error: {e}")
            self.temp_read_errors += 1
            self.heater.turn_off()
            self.cooler.turn_off()
            return None, 0, "Error"

def run_test(heater_pin, cooler_pin):
    """Run a test sequence of temperature control.
    
    Args:
        heater_pin: Pin number for the PTC heater
        cooler_pin: Pin number for the TEC1 cooler
    """
    DURATION = 5 * 60  # 5 minutes in seconds
    
    # Initialize the temperature controller
    print("\nInitializing temperature controller...")
    temp_ctrl = TempController(heater_pin, cooler_pin, kp=25.0, ki=0, kd=0)
    
    def run_phase(target_temp, duration):
        """Run a single phase of temperature control."""
        print(f"\nPhase: Holding at {target_temp}°C for 5 minutes...")
        start = time.time()
        while time.time() - start < duration:
            current_temp, power, mode = temp_ctrl.control_temp(target_temp)
            if current_temp is not None:
                print(f"Target: {target_temp}°C | Current: {current_temp}°C | Mode: {mode} | Power: {power}")
            time.sleep(1)
    
    try:
        # Phase 1: 20°C for 5 minutes (should activate cooling)
        print("\nStarting cooling test phase...")
        run_phase(20.0, DURATION)
        
        # Phase 2: 30°C for 5 minutes (should activate heating)
        print("\nStarting heating test phase...")
        run_phase(30.0, DURATION)
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    finally:
        # Shutdown: turn off actuators
        print("\nShutting down...")
        temp_ctrl.heater.turn_off()
        temp_ctrl.cooler.turn_off()
        print("Test complete.")

# ---- TEST CODE ----
if __name__ == "__main__":
    # Define pins for testing
    HEATER_PIN = 33  # PTC heater pin
    COOLER_PIN = 27  # TEC1 cooler pin
    
    print("Starting temperature control test...")
    run_test(HEATER_PIN, COOLER_PIN)
