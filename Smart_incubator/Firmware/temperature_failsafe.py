# temperature_failsafe.py - Temperature Failsafe System
import time
try:
    from machine import Pin
except ImportError:
    Pin = None  # Allows import on host systems without machine module
import gc
try:
    from sensor_recovery import SensorRecoveryManager
except ImportError:
    class SensorRecoveryManager:
        """Fallback stub when sensor_recovery module is unavailable."""
        def __init__(self, *args, **kwargs):
            self._status = {
                'attempts': 0,
                'max_attempts': kwargs.get('max_recovery_attempts', 0),
                'cooldown': kwargs.get('recovery_cooldown', 0),
                'last_attempt_time': None,
                'cooldown_remaining': 0
            }

        def can_attempt_recovery(self):
            return False

        def attempt_sensor_recovery(self, *args, **kwargs):
            return False, None, "Sensor recovery module not available"

        def get_recovery_status(self):
            return self._status

        def reset_recovery_state(self):
            self._status['attempts'] = 0
            self._status['cooldown_remaining'] = 0

class TemperatureFailsafe:
    """Failsafe system to detect stuck temperature readings and prevent overheating."""
    
    def __init__(self, stuck_threshold_seconds=120, max_temp_limit=40.0, enable_emergency_shutdown=True):
        """
        Initialize temperature failsafe system.
        
        Args:
            stuck_threshold_seconds: Time in seconds before considering temp "stuck"
            max_temp_limit: Maximum allowed temperature before emergency shutdown
            enable_emergency_shutdown: Whether to enable automatic hardware shutdown
        """
        self.stuck_threshold = stuck_threshold_seconds
        self.max_temp_limit = max_temp_limit
        self.enable_emergency_shutdown = enable_emergency_shutdown
        
        # Tracking variables
        self.temperature_history = []
        self.stuck_start_time = None
        self.last_valid_temp = None
        self.consecutive_stuck_readings = 0
        self.failsafe_triggered = False
        self.emergency_shutdown_triggered = False
        self.stuck_temp_epsilon = 0.1  # Allow small natural fluctuations before flagging stuck
        self.stuck_reset_epsilon = 0.2  # Require meaningful movement before clearing stuck state
        self._last_stuck_warning_time = 0
        self._stuck_warning_interval = 30  # seconds between repeated stuck warnings
        
        # Initialize sensor recovery system
        self.recovery_manager = SensorRecoveryManager(
            max_recovery_attempts=3,
            recovery_cooldown=300  # 5 minutes between attempts
        )
        
        # Emergency shutdown pin (optional - can be connected to external relay)
        self.emergency_pin = None
        try:
            self.emergency_pin = Pin(32, Pin.OUT)  # Use an available pin
            self.emergency_pin.value(0)  # Start with normal operation
        except:
            print("[WARNING] Emergency shutdown pin not available")
        
        print(f"[FAILSAFE] Initialized - Stuck threshold: {stuck_threshold_seconds}s, Max temp: {max_temp_limit}°C")
        print(f"[FAILSAFE] Recovery system enabled - Max attempts: 3, Cooldown: 5min")
    
    def check_temperature(self, current_temp, heater_power, cooler_power):
        """
        Check temperature for failsafe conditions.
        
        Args:
            current_temp: Current temperature reading (can be None)
            heater_power: Current heater power level
            cooler_power: Current cooler power level
            
        Returns:
            tuple: (is_safe, failsafe_action, message)
        """
        current_time = time.time()
        
        # Handle None temperature readings
        if current_temp is None:
            return self._handle_none_temperature(current_time)
        
        # Add to history (keep last 20 readings for analysis)
        self.temperature_history.append({
            'temp': current_temp,
            'time': current_time,
            'heater_power': heater_power,
            'cooler_power': cooler_power
        })
        
        if len(self.temperature_history) > 20:
            self.temperature_history.pop(0)
        
        # Check for stuck temperature
        stuck_result = self._check_stuck_temperature(current_temp, current_time)
        if not stuck_result[0]:
            return stuck_result
        
        # Check for overheating
        overheat_result = self._check_overheating(current_temp)
        if not overheat_result[0]:
            return overheat_result
        
        # Check for abnormal heating patterns
        heating_result = self._check_abnormal_heating(current_temp, heater_power)
        if not heating_result[0]:
            return heating_result
        
        # All checks passed
        self.last_valid_temp = current_temp
        return True, None, "OK"
    
    def _handle_none_temperature(self, current_time):
        """Handle None temperature readings."""
        if self.last_valid_temp is None:
            return False, "emergency_stop", "No valid temperature readings - emergency stop"
        
        # If we've been getting None for too long, that's dangerous
        if len(self.temperature_history) > 0:
            last_valid_time = max(h['time'] for h in self.temperature_history if h['temp'] is not None)
            if current_time - last_valid_time > 60:  # 1 minute without valid reading
                return False, "emergency_stop", "No valid temperature readings for >1 minute"
        
        return True, "warning", "Using fallback temperature - sensor may be failing"
    
    def _check_stuck_temperature(self, current_temp, current_time):
        """Check if temperature is stuck at the same value."""
        # Need at least 3 readings to detect stuck temperature
        if len(self.temperature_history) < 3:
            return True, None, "Insufficient history"
        
        recent_entries = self.temperature_history[-10:]
        recent_temps = [h['temp'] for h in recent_entries if h['temp'] is not None]
        if recent_entries:
            avg_heater_power = sum(abs(h['heater_power']) for h in recent_entries) / len(recent_entries)
            avg_cooler_power = sum(abs(h['cooler_power']) for h in recent_entries) / len(recent_entries)

            # If actuators are essentially idle, treat flat temperature as normal stability
            if avg_heater_power < 5 and avg_cooler_power < 5:
                if self.stuck_start_time is not None:
                    print("[FAILSAFE] Temperature stable with low actuator power - clearing stuck state")
                self.stuck_start_time = None
                self.consecutive_stuck_readings = 0
                self._last_stuck_warning_time = 0
                return True, None, "Temperature stable within control deadband"
        
        if len(recent_temps) >= 5:
            temp_range = max(recent_temps) - min(recent_temps)
            if temp_range <= self.stuck_temp_epsilon:
                if self.stuck_start_time is None:
                    self.stuck_start_time = current_time
                    print(f"[FAILSAFE] Potential stuck temperature detected at {current_temp}°C")
                
                stuck_duration = current_time - self.stuck_start_time
                
                # Attempt sensor recovery at 75% of threshold (1.5 minutes for 2-minute threshold)
                recovery_trigger_time = self.stuck_threshold * 0.75
                
                if stuck_duration > recovery_trigger_time and self.recovery_manager.can_attempt_recovery():
                    print(f"[FAILSAFE] Attempting sensor recovery after {stuck_duration:.1f}s stuck")
                    
                    # Attempt recovery
                    success, recovered_temp, recovery_message = self.recovery_manager.attempt_sensor_recovery(
                        stuck_temp=current_temp, 
                        error_type="stuck"
                    )
                    
                    if success:
                        print(f"[FAILSAFE] RECOVERY SUCCESS: {recovery_message}")
                        # Reset stuck detection since sensor was recovered
                        self.stuck_start_time = None
                        self.consecutive_stuck_readings = 0
                        # Return the recovered temperature
                        return True, "recovery_success", f"Sensor recovered! New temp: {recovered_temp:.2f}°C"
                    else:
                        print(f"[FAILSAFE] RECOVERY FAILED: {recovery_message}")
                        # Continue with normal stuck detection flow
                
                # If we've reached the full threshold and recovery failed/unavailable
                if stuck_duration > self.stuck_threshold:
                    recovery_status = self.recovery_manager.get_recovery_status()
                    if recovery_status['attempts'] > 0:
                        message = f"Temperature stuck at {current_temp}°C for {stuck_duration:.1f}s - Recovery attempts exhausted ({recovery_status['attempts']}/{recovery_status['max_attempts']})"
                    else:
                        message = f"Temperature stuck at {current_temp}°C for {stuck_duration:.1f}s - No recovery attempted"
                    
                    self.failsafe_triggered = True
                    return False, "emergency_stop", message
                elif stuck_duration > self.stuck_threshold * 0.5:
                    if current_time - self._last_stuck_warning_time >= self._stuck_warning_interval:
                        self._last_stuck_warning_time = current_time
                        return True, "warning", f"Temperature may be stuck ({stuck_duration:.1f}s at {current_temp}°C)"
                    else:
                        return True, None, "Monitoring potential stuck condition"
            else:
                if self.stuck_start_time is not None and temp_range >= self.stuck_reset_epsilon:
                    print(f"[FAILSAFE] Temperature unstuck - sensor appears healthy")
                    self.recovery_manager.reset_recovery_state()
                    self.stuck_start_time = None
                    self.consecutive_stuck_readings = 0
                    self._last_stuck_warning_time = 0
        
        return True, None, "OK"
    
    def _check_overheating(self, current_temp):
        """Check for dangerous overheating."""
        if current_temp > self.max_temp_limit:
            self.emergency_shutdown_triggered = True
            return False, "emergency_stop", f"OVERHEATING: {current_temp}°C > {self.max_temp_limit}°C limit"
        
        # Warning at 90% of limit
        warning_temp = self.max_temp_limit * 0.9
        if current_temp > warning_temp:
            return True, "warning", f"Temperature approaching limit: {current_temp}°C"
        
        return True, None, "OK"
    
    def _check_abnormal_heating(self, current_temp, heater_power):
        """Check for abnormal heating patterns."""
        if len(self.temperature_history) < 5:
            return True, None, "Insufficient history"
        
        # Look for pattern: low temperature reading + high heater power
        # This could indicate sensor failure with dangerous heating
        if current_temp < 20.0 and heater_power > 50:
            return True, "warning", f"Suspicious: Low temp ({current_temp}°C) with high heater power ({heater_power}%)"
        
        # Check for rapid temperature rise that could indicate runaway heating
        recent_temps = [h['temp'] for h in self.temperature_history[-5:] if h['temp'] is not None]
        if len(recent_temps) >= 3:
            temp_rise = recent_temps[-1] - recent_temps[0]
            time_span = self.temperature_history[-1]['time'] - self.temperature_history[-len(recent_temps)]['time']
            
            if time_span > 0:
                rise_rate = temp_rise / (time_span / 60)  # °C per minute
                if rise_rate > 2.0:  # More than 2°C per minute is suspicious
                    return True, "warning", f"Rapid temperature rise: {rise_rate:.1f}°C/min"
        
        return True, None, "OK"
    
    def trigger_emergency_shutdown(self, reason):
        """Trigger emergency shutdown of all heating elements."""
        print(f"[EMERGENCY] FAILSAFE TRIGGERED: {reason}")
        
        # Set emergency pin if available
        if self.emergency_pin:
            self.emergency_pin.value(1)  # Signal emergency state
        
        self.failsafe_triggered = True
        
        # Log the emergency event
        try:
            with open('/sd/emergency_log.txt', 'a') as f:
                f.write(f"{time.time()},{reason}\n")
        except:
            pass  # SD card might not be available
        
        return False  # System should stop
    
    def get_status(self):
        """Get current failsafe status."""
        return {
            'failsafe_triggered': self.failsafe_triggered,
            'emergency_shutdown': self.emergency_shutdown_triggered,
            'stuck_start_time': self.stuck_start_time,
            'history_count': len(self.temperature_history),
            'last_valid_temp': self.last_valid_temp
        }
    
    def reset(self):
        """Reset failsafe state (use with caution)."""
        print("[FAILSAFE] Resetting failsafe state")
        self.failsafe_triggered = False
        self.emergency_shutdown_triggered = False
        self.stuck_start_time = None
        self.consecutive_stuck_readings = 0
        if self.emergency_pin:
            self.emergency_pin.value(0)

# Integration functions for existing temperature controller
def add_failsafe_to_temp_controller():
    """Patch existing temperature controller to include failsafe."""
    print("\n=== PATCHING TEMPERATURE CONTROLLER WITH FAILSAFE ===")
    
    # Create backup of original file
    try:
        with open('temp_controller.py', 'r') as f:
            original_content = f.read()
        
        with open('temp_controller_backup.py', 'w') as f:
            f.write(original_content)
        print("[OK] Created backup: temp_controller_backup.py")
        
    except Exception as e:
        print(f"[ERROR] Could not create backup: {e}")
        return False
    
    # The integration will be done manually by modifying the control_temp method
    print("[INFO] Manual integration required:")
    print("1. Import: from temperature_failsafe import TemperatureFailsafe")
    print("2. Initialize: self.failsafe = TemperatureFailsafe() in __init__")
    print("3. Check: Add failsafe.check_temperature() in control_temp method")
    print("4. Act: Implement emergency shutdown on failsafe trigger")
    
    return True

# Test function
def test_failsafe():
    """Test failsafe functionality."""
    print("\n=== TESTING FAILSAFE SYSTEM ===")
    
    failsafe = TemperatureFailsafe(stuck_threshold_seconds=10, max_temp_limit=35.0)
    
    print("\nTest 1: Normal operation")
    for i in range(5):
        temp = 25.0 + i * 0.1
        result = failsafe.check_temperature(temp, 50, 0)
        print(f"  Temp: {temp}°C -> {result}")
        time.sleep(0.1)
    
    print("\nTest 2: Stuck temperature")
    stuck_temp = 19.1
    for i in range(15):
        result = failsafe.check_temperature(stuck_temp, 75, 0)
        print(f"  Stuck temp: {stuck_temp}°C -> {result}")
        if not result[0]:
            print("  [OK] Failsafe correctly detected stuck temperature!")
            break
        time.sleep(0.1)
    
    print("\nTest 3: Overheating")
    failsafe.reset()
    result = failsafe.check_temperature(42.0, 0, 100)
    print(f"  High temp: 42.0°C -> {result}")
    
    if not result[0]:
        print("  [OK] Failsafe correctly detected overheating!")
    
    print("\nFailsafe test complete.")

if __name__ == "__main__":
    test_failsafe()
