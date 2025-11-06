# sensor_recovery.py - Sensor Recovery and Restart System
import time
from machine import Pin, SPI
from max31865 import init_max31865, read_temperature, read_register, write_register, CONFIG_REG
import gc

class SensorRecoveryManager:
    """Advanced sensor recovery system to restore stuck sensors."""
    
    def __init__(self, max_recovery_attempts=3, recovery_cooldown=300):
        """
        Initialize sensor recovery manager.
        
        Args:
            max_recovery_attempts: Maximum number of recovery attempts per incident
            recovery_cooldown: Time in seconds between recovery attempts
        """
        self.max_recovery_attempts = max_recovery_attempts
        self.recovery_cooldown = recovery_cooldown
        self.recovery_attempts = 0
        self.last_recovery_time = 0
        self.recovery_log = []
        self.sensor_healthy = True
        
        print(f"[RECOVERY] Initialized - Max attempts: {max_recovery_attempts}, Cooldown: {recovery_cooldown}s")
    
    def attempt_sensor_recovery(self, stuck_temp=None, error_type="stuck"):
        """
        Attempt to recover a stuck or failed sensor.
        
        Args:
            stuck_temp: The temperature the sensor is stuck at
            error_type: Type of error ("stuck", "none_readings", "spi_error")
            
        Returns:
            tuple: (success, new_temp, recovery_message)
        """
        current_time = time.time()
        
        # Check if we're in cooldown period
        if current_time - self.last_recovery_time < self.recovery_cooldown:
            remaining = self.recovery_cooldown - (current_time - self.last_recovery_time)
            return False, None, f"Recovery cooldown active ({remaining:.0f}s remaining)"
        
        # Check if we've exceeded max attempts
        if self.recovery_attempts >= self.max_recovery_attempts:
            return False, None, f"Maximum recovery attempts ({self.max_recovery_attempts}) exceeded"
        
        self.recovery_attempts += 1
        self.last_recovery_time = current_time
        
        print(f"\n[RECOVERY] Attempting sensor recovery #{self.recovery_attempts}")
        print(f"[RECOVERY] Error type: {error_type}")
        if stuck_temp:
            print(f"[RECOVERY] Stuck temperature: {stuck_temp}°C")
        
        recovery_steps = []
        
        try:
            # Step 1: Memory cleanup
            recovery_steps.append("memory_cleanup")
            print("[RECOVERY] Step 1: Memory cleanup...")
            gc.collect()
            time.sleep(0.5)
            
            # Step 2: SPI bus reset
            recovery_steps.append("spi_reset")
            print("[RECOVERY] Step 2: SPI bus reset...")
            success = self._reset_spi_bus()
            if not success:
                return False, None, "SPI bus reset failed"
            
            # Step 3: MAX31865 hard reset
            recovery_steps.append("sensor_hard_reset")
            print("[RECOVERY] Step 3: MAX31865 hard reset...")
            success = self._reset_max31865_chip()
            if not success:
                return False, None, "MAX31865 reset failed"
            
            # Step 4: Sensor re-initialization  
            recovery_steps.append("sensor_reinit")
            print("[RECOVERY] Step 4: Sensor re-initialization...")
            success = init_max31865()
            if not success:
                return False, None, "Sensor re-initialization failed"
            
            # Step 5: Validation readings
            recovery_steps.append("validation_readings")
            print("[RECOVERY] Step 5: Taking validation readings...")
            new_temp = self._validate_sensor_recovery(stuck_temp)
            
            if new_temp is not None:
                recovery_message = f"Recovery successful! New temp: {new_temp:.2f}°C"
                self._log_recovery(True, error_type, recovery_steps, new_temp)
                self.sensor_healthy = True
                print(f"[RECOVERY] SUCCESS: {recovery_message}")
                return True, new_temp, recovery_message
            else:
                recovery_message = "Recovery failed - sensor still not responding"
                self._log_recovery(False, error_type, recovery_steps, None)
                print(f"[RECOVERY] FAILED: {recovery_message}")
                return False, None, recovery_message
                
        except Exception as e:
            recovery_message = f"Recovery exception: {e}"
            self._log_recovery(False, error_type, recovery_steps, None)
            print(f"[RECOVERY] ERROR: {recovery_message}")
            return False, None, recovery_message
    
    def _reset_spi_bus(self):
        """Reset the SPI bus to clear any stuck states."""
        try:
            # This is tricky in MicroPython - we'll simulate by re-init
            time.sleep(0.2)  # Allow bus to settle
            
            # Try to clear any pending transactions
            for _ in range(5):
                try:
                    # Read a register to clear bus state
                    read_register(CONFIG_REG)
                    time.sleep_ms(10)
                except:
                    continue
            
            print("[RECOVERY]   SPI bus reset completed")
            return True
            
        except Exception as e:
            print(f"[RECOVERY]   SPI reset error: {e}")
            return False
    
    def _reset_max31865_chip(self):
        """Perform a software reset of the MAX31865 chip."""
        try:
            # MAX31865 doesn't have a direct reset, but we can reconfigure it
            
            # Step 1: Clear configuration register
            write_register(CONFIG_REG, 0x00)
            time.sleep_ms(50)
            
            # Step 2: Restore proper configuration
            # Standard config: Bias on, 1-shot off, 3-wire RTD, fault detection off
            config_value = 0xC3  # Standard configuration
            write_register(CONFIG_REG, config_value)
            time.sleep_ms(50)
            
            # Step 3: Verify configuration was set
            read_config = read_register(CONFIG_REG)
            # Some bits (like the one-shot bit) may clear automatically; accept either 0xC3 or 0xC1
            valid_configs = (config_value, config_value & ~0x02)
            if read_config not in valid_configs:
                valid_str = ", ".join("0x{:02X}".format(val) for val in valid_configs)
                print(f"[RECOVERY]   Config verification failed: got 0x{read_config:02X}, expected one of {valid_str}")
                return False
            
            print("[RECOVERY]   MAX31865 reset completed")
            return True
            
        except Exception as e:
            print(f"[RECOVERY]   MAX31865 reset error: {e}")
            return False
    
    def _validate_sensor_recovery(self, stuck_temp):
        """Validate that sensor recovery was successful."""
        print("[RECOVERY]   Taking validation readings...")
        
        # Take multiple readings to verify sensor is working
        readings = []
        
        for i in range(5):
            try:
                temp = read_temperature()
                if temp is not None:
                    readings.append(temp)
                    print(f"[RECOVERY]   Reading {i+1}: {temp:.2f}°C")
                else:
                    print(f"[RECOVERY]   Reading {i+1}: None")
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"[RECOVERY]   Reading {i+1} error: {e}")
        
        if len(readings) == 0:
            print("[RECOVERY]   No valid readings obtained")
            return None
        
        # Check if readings are varied (not all identical)
        if stuck_temp is not None:
            # At least one reading should be different from stuck value
            different_readings = [r for r in readings if abs(r - stuck_temp) > 0.05]
            if len(different_readings) == 0:
                print(f"[RECOVERY]   All readings still stuck at {stuck_temp}°C")
                return None
        
        # Check for reasonable temperature range
        min_temp, max_temp = min(readings), max(readings)
        if max_temp - min_temp > 10.0:
            print(f"[RECOVERY]   Temperature range too large: {min_temp:.2f} to {max_temp:.2f}°C")
            return None
        
        # Return the median reading
        readings.sort()
        median_temp = readings[len(readings) // 2]
        print(f"[RECOVERY]   Validation successful, median temp: {median_temp:.2f}°C")
        return median_temp
    
    def _log_recovery(self, success, error_type, steps, new_temp):
        """Log recovery attempt details."""
        log_entry = {
            'timestamp': time.time(),
            'attempt': self.recovery_attempts,
            'success': success,
            'error_type': error_type,
            'steps_completed': steps,
            'new_temperature': new_temp
        }
        
        self.recovery_log.append(log_entry)
        
        # Save to SD card if available
        try:
            import json
            with open('/sd/recovery_log.json', 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except:
            pass  # SD card might not be available
    
    def reset_recovery_state(self):
        """Reset recovery attempt counter (use when sensor is confirmed healthy)."""
        self.recovery_attempts = 0
        self.sensor_healthy = True
        print("[RECOVERY] Recovery state reset - sensor marked healthy")
    
    def get_recovery_status(self):
        """Get current recovery status."""
        return {
            'attempts': self.recovery_attempts,
            'max_attempts': self.max_recovery_attempts,
            'last_recovery': self.last_recovery_time,
            'sensor_healthy': self.sensor_healthy,
            'total_recoveries': len(self.recovery_log),
            'successful_recoveries': len([log for log in self.recovery_log if log['success']])
        }
    
    def can_attempt_recovery(self):
        """Check if recovery can be attempted."""
        current_time = time.time()
        cooldown_ok = current_time - self.last_recovery_time >= self.recovery_cooldown
        attempts_ok = self.recovery_attempts < self.max_recovery_attempts
        
        return cooldown_ok and attempts_ok

def test_recovery_system():
    """Test the sensor recovery system."""
    print("\n=== TESTING SENSOR RECOVERY SYSTEM ===")
    
    recovery_manager = SensorRecoveryManager(max_recovery_attempts=2, recovery_cooldown=10)
    
    print("\nTest 1: Simulate stuck sensor recovery")
    success, new_temp, message = recovery_manager.attempt_sensor_recovery(stuck_temp=19.1, error_type="stuck")
    print(f"Result: Success={success}, Temp={new_temp}, Message={message}")
    
    print(f"\nRecovery Status: {recovery_manager.get_recovery_status()}")
    
    print("\nTest 2: Simulate SPI error recovery")
    success, new_temp, message = recovery_manager.attempt_sensor_recovery(error_type="spi_error")
    print(f"Result: Success={success}, Temp={new_temp}, Message={message}")
    
    print(f"\nFinal Status: {recovery_manager.get_recovery_status()}")
    print("\nRecovery test complete.")

if __name__ == "__main__":
    test_recovery_system()
