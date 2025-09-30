# pump_controller.py - Peristaltic Pump PWM Controller
from machine import Pin, PWM
import utime

class PumpController:
    """Controls a single peristaltic pump with PWM, calibration, and volume tracking."""
    
    def __init__(self, pin, pump_id, frequency=1000, calibration=None, debug=False):
        """
        Initialize pump controller.
        
        Args:
            pin: GPIO pin number for PWM output
            pump_id: Pump identifier (1-4)
            frequency: PWM frequency in Hz
            calibration: Dict with 'a' and 'b' coefficients (ml/h = a*PWM% + b)
            debug: Enable debug printing
        """
        self.pump_id = pump_id
        self.pin = pin
        self.frequency = frequency
        self.debug = debug
        
        # Initialize PWM
        self.pwm = PWM(Pin(pin, Pin.OUT))
        self.pwm.freq(frequency)
        self.pwm.duty(0)  # Start stopped
        
        # Store calibration coefficients as direct floats for performance
        calib = calibration or {"a": 2.5, "b": 0.0}
        self.calib_a = float(calib["a"])
        self.calib_b = float(calib["b"])
        
        # Warn if pump appears stalled
        if self.calib_a == 0.0:
            print(f"[Pump{pump_id}] WARNING: Zero calibration coefficient - pump may be stalled")
        
        # State tracking
        self.current_duty = 0  # Current PWM duty cycle (0-100%)
        self.is_running = False
        self.start_time = 0
        self.target_duration = 0
        self.total_volume_ml = 0.0  # Total volume dispensed since boot
        
        if self.debug:
            print(f"[Pump{pump_id}] Initialized on GPIO {pin} @ {frequency}Hz (calib: {self.calib_a:.3f}*PWM + {self.calib_b:.3f})")
    
    def set_duty(self, duty_percent):
        """Set PWM duty cycle (0-100%) with build compatibility."""
        duty_percent = max(0, min(100, duty_percent))  # Clamp to valid range
        
        # Convert percentage to PWM duty value
        pwm_val = int((duty_percent / 100.0) * 1023)
        
        # Handle different MicroPython PWM builds
        if hasattr(self.pwm, "duty_u16"):
            # 16-bit builds (RP2040 and some ESP32 builds)
            self.pwm.duty_u16(pwm_val << 6)  # Scale 10-bit to 16-bit
        else:
            # 10-bit builds (standard ESP32)
            self.pwm.duty(pwm_val)
        
        self.current_duty = duty_percent
        
        if duty_percent > 0:
            if not self.is_running:
                self.start_time = utime.ticks_ms()
                self.is_running = True
        else:
            self.stop()
    
    def set_frequency(self, frequency):
        """Update PWM frequency for quieter operation."""
        self.frequency = frequency
        self.pwm.freq(frequency)
        if self.debug:
            print(f"[Pump{self.pump_id}] Frequency updated to {frequency}Hz")
    
    def start(self, duty_percent, duration_sec):
        """Start pump with specified duty cycle for duration."""
        # Validate parameters at start() level too
        duty_percent = max(0, min(100, duty_percent))
        duration_sec = max(0, min(3600, duration_sec))  # Max 1 hour safety
        
        # Reject no-op commands early
        if duration_sec == 0 or duty_percent == 0:
            if self.debug:
                print(f"[Pump{self.pump_id}] Rejected no-op command: {duty_percent}% for {duration_sec}s")
            return False
            
        self.target_duration = duration_sec * 1000  # Convert to ms
        self.set_duty(duty_percent)
        
        if self.debug:
            print(f"[Pump{self.pump_id}] Started: {duty_percent}% for {duration_sec}s")
        return True
    
    def stop(self):
        """Stop pump and update volume tracking with proper tick handling."""
        if self.is_running:
            # Calculate volume dispensed using proper tick difference
            elapsed_ms = utime.ticks_diff(utime.ticks_ms(), self.start_time)
            volume_dispensed = self.calculate_volume(self.current_duty, elapsed_ms / 1000.0)
            self.total_volume_ml += volume_dispensed
            
            if self.debug:
                print(f"[Pump{self.pump_id}] Stopped. Volume: {volume_dispensed:.3f}ml (Total: {self.total_volume_ml:.3f}ml)")
        
        # Set duty to zero using same compatibility logic
        if hasattr(self.pwm, "duty_u16"):
            self.pwm.duty_u16(0)
        else:
            self.pwm.duty(0)
            
        self.current_duty = 0
        self.is_running = False
        self.start_time = 0
        self.target_duration = 0
    
    def update(self):
        """Update pump state - call periodically to handle duration timeout."""
        if not self.is_running:
            return
        
        elapsed_ms = utime.ticks_diff(utime.ticks_ms(), self.start_time)
        
        # Check if duration expired
        if elapsed_ms >= self.target_duration:
            self.stop()
    
    def calculate_volume(self, duty_percent, duration_sec):
        """Calculate volume dispensed based on calibration (optimized)."""
        if duration_sec <= 0:
            return 0.0
        
        # ml/h = a * PWM% + b (using direct float access)
        flow_rate_ml_per_hour = (self.calib_a * duty_percent) + self.calib_b
        
        # Convert to ml for the given duration
        volume_ml = flow_rate_ml_per_hour * (duration_sec / 3600.0)
        
        return max(0.0, volume_ml)  # Never negative
    
    def get_current_volume_rate(self):
        """Get current volume dispensing rate in ml/h."""
        if not self.is_running:
            return 0.0
        
        return (self.calib_a * self.current_duty) + self.calib_b
    
    def set_calibration(self, a, b):
        """Update calibration coefficients with validation."""
        self.calib_a = float(a)
        self.calib_b = float(b)
        
        # Warn if pump appears stalled
        if self.calib_a == 0.0:
            print(f"[Pump{self.pump_id}] WARNING: Zero calibration coefficient - pump may be stalled")
        
        if self.debug:
            print(f"[Pump{self.pump_id}] Calibration updated: ml/h = {self.calib_a:.3f}*PWM% + {self.calib_b:.3f}")
    
    def get_calibration(self):
        """Get current calibration as dict."""
        return {"a": self.calib_a, "b": self.calib_b}
    
    def reset_volume(self):
        """Reset total volume counter."""
        old_volume = self.total_volume_ml
        self.total_volume_ml = 0.0
        if self.debug:
            print(f"[Pump{self.pump_id}] Volume counter reset (was {old_volume:.3f}ml)")
    
    def get_status(self):
        """Get pump status dictionary."""
        current_volume_in_progress = 0.0
        
        if self.is_running:
            elapsed_sec = utime.ticks_diff(utime.ticks_ms(), self.start_time) / 1000.0
            current_volume_in_progress = self.calculate_volume(self.current_duty, elapsed_sec)
        
        return {
            "pump_id": self.pump_id,
            "duty_percent": self.current_duty,
            "is_running": self.is_running,
            "total_volume_ml": self.total_volume_ml,
            "current_volume_ml": current_volume_in_progress,
            "flow_rate_ml_h": self.get_current_volume_rate(),
            "calibration": self.get_calibration()
        }
    
    def emergency_stop(self):
        """Emergency stop - immediate shutdown with PWM deinit."""
        try:
            # Immediate PWM shutdown
            if hasattr(self.pwm, "duty_u16"):
                self.pwm.duty_u16(0)
            else:
                self.pwm.duty(0)
            
            # Release PWM pin for clean restart
            self.pwm.deinit()
            
            self.current_duty = 0
            self.is_running = False
            self.start_time = 0
            self.target_duration = 0
            
            print(f"[Pump{self.pump_id}] EMERGENCY STOP - PWM deinitialized")
            
        except Exception as e:
            print(f"[Pump{self.pump_id}] Error during emergency stop: {e}")


# ================== MULTI-PUMP CONTROLLER ==================

class PumpBank:
    """Controls multiple pumps with command queuing and coordination."""
    
    def __init__(self, pump_pins, calibrations=None, frequency=1000, debug=False):
        """
        Initialize pump bank.
        
        Args:
            pump_pins: List of GPIO pins for pumps 1-4
            calibrations: Dict of calibration coefficients per pump
            frequency: PWM frequency
            debug: Enable debug printing
        """
        self.pumps = {}
        self.command_queues = {}
        self.debug = debug
        
        # Initialize individual pumps
        for i, pin in enumerate(pump_pins):
            pump_id = i + 1
            calib = calibrations.get(pump_id) if calibrations else None
            
            self.pumps[pump_id] = PumpController(pin, pump_id, frequency, calib, debug)
            self.command_queues[pump_id] = []  # FIFO queue for each pump
        
        if self.debug:
            print(f"[PumpBank] Initialized {len(self.pumps)} pumps")
    
    def queue_command(self, pump_id, duty_percent, duration_sec, command_id=None, max_queue=5):
        """Queue a pump command with enhanced validation."""
        if pump_id not in self.pumps:
            return False
        
        # Check queue depth
        if len(self.command_queues[pump_id]) >= max_queue:
            if self.debug:
                print(f"[PumpBank] Queue full for pump {pump_id}")
            return False
        
        # Validate parameters with early rejection of no-ops
        duty_percent = max(0, min(100, duty_percent))
        duration_sec = max(0, min(3600, duration_sec))  # Max 1 hour
        
        # Reject no-op commands to avoid wasting queue slots
        if duty_percent == 0 or duration_sec == 0:
            if self.debug:
                print(f"[PumpBank] Rejected no-op command for pump {pump_id}")
            return False
        
        command = {
            "duty": duty_percent,
            "duration": duration_sec,
            "command_id": command_id or f"cmd_{utime.ticks_ms()}",
            "queued_time": utime.ticks_ms()
        }
        
        self.command_queues[pump_id].append(command)
        if self.debug:
            print(f"[PumpBank] Queued pump {pump_id}: {duty_percent}% for {duration_sec}s")
        return True
    
    def flush_queue(self, pump_id):
        """Flush command queue for specific pump to prevent stale commands."""
        if pump_id in self.command_queues:
            cleared_count = len(self.command_queues[pump_id])
            self.command_queues[pump_id].clear()
            if self.debug and cleared_count > 0:
                print(f"[PumpBank] Flushed {cleared_count} commands from pump {pump_id} queue")
            return cleared_count
        return 0
    
    def flush_all_queues(self):
        """Flush all command queues."""
        total_cleared = 0
        for pump_id in self.command_queues:
            total_cleared += self.flush_queue(pump_id)
        return total_cleared
    
    def update_all(self):
        """Update all pumps and process queued commands."""
        for pump_id, pump in self.pumps.items():
            # Update running pump
            pump.update()
            
            # Start next queued command if pump is idle
            if not pump.is_running and self.command_queues[pump_id]:
                command = self.command_queues[pump_id].pop(0)  # FIFO
                pump.start(command["duty"], command["duration"])
    
    def emergency_stop_all(self):
        """Emergency stop all pumps with PWM deinit."""
        for pump in self.pumps.values():
            pump.emergency_stop()
        
        # Clear all queues
        total_cleared = self.flush_all_queues()
        
        print(f"[PumpBank] EMERGENCY STOP - All pumps stopped, {total_cleared} commands cleared")
    
    def get_all_status(self):
        """Get status of all pumps."""
        status = {}
        for pump_id, pump in self.pumps.items():
            status[pump_id] = pump.get_status()
            status[pump_id]["queue_length"] = len(self.command_queues[pump_id])
        
        return status
    
    def update_calibration(self, calibrations):
        """Update calibration for multiple pumps."""
        for pump_id, calib in calibrations.items():
            if pump_id in self.pumps and "a" in calib and "b" in calib:
                self.pumps[pump_id].set_calibration(calib["a"], calib["b"])
    
    def reset_volumes(self, pump_ids=None):
        """Reset volume counters for specified pumps (or all if None)."""
        pump_ids = pump_ids or list(self.pumps.keys())
        
        for pump_id in pump_ids:
            if pump_id in self.pumps:
                self.pumps[pump_id].reset_volume()
    
    def set_debug(self, debug):
        """Enable/disable debug output for all pumps."""
        self.debug = debug
        for pump in self.pumps.values():
            pump.debug = debug


# ================== TEST CODE ==================
if __name__ == "__main__":
    # Test enhanced pump controller
    pump = PumpController(pin=25, pump_id=1, calibration={"a": 2.5, "b": 0.1}, debug=True)
    
    print("Testing enhanced pump...")
    
    # Test no-op rejection
    pump.start(0, 5)    # Should be rejected
    pump.start(50, 0)   # Should be rejected
    
    # Test valid command
    pump.start(50, 5)   # Should work
    
    for i in range(10):
        pump.update()
        status = pump.get_status()
        print(f"Status: duty={status['duty_percent']}% volume={status['total_volume_ml']:.3f}ml")
        utime.sleep(1)
    
    # Test emergency stop
    pump.emergency_stop() 