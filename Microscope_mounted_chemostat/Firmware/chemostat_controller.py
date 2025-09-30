# chemostat_controller.py - Variable PWM Chemostat Flow Control
# 0-100% Duty Control - Time Coordination Algorithm:
# Pump 1 (Media) & Pump 3 (Chamber): T seconds at specified %
# Pump 4 (Overflow): 3T seconds at specified %  
# Pump 2 (Signal): Upon command only at specified %

from machine import Pin, PWM, Timer
import time
import os

# Configuration
PUMP_PINS = [32, 33, 25, 26]  # GPIO pins for pumps 1-4
LED_PIN = 27                  # LED pin
STATUS_LED_PIN = 2            # Built-in status LED
PWM_FREQUENCY = 20000         # 20kHz PWM frequency (from calibration system)

# Flow control parameters
OVERFLOW_MULTIPLIER = 3       # Pump 4 runs 3X longer than pumps 1&3
DEFAULT_SIGNAL_TIME = 5       # Default signal injection time

# PWM profiles for different supply voltages
PUMP_PROFILES = {
    12: dict(freq=20_000, max_duty=8191),   # 20 kHz, full 13-bit resolution
     5: dict(freq=10_000, max_duty=8191),   # 10 kHz – gentler for 5 V motors
}

# Default supply voltage (can be changed)
SUPPLY_VOLTAGE = 12

class Logger:
    def __init__(self):
        self.log_file = None
        self.start_time = 0

    def start_logging(self, filename):
        if self.log_file:
            self.log("⚠️ Log file is already open. Please stop first.")
            return False
        try:
            # Create a default filename if none is provided
            if not filename:
                timestamp = time.localtime()
                filename = f"chemostat_log_{timestamp[0]:04d}{timestamp[1]:02d}{timestamp[2]:02d}_{timestamp[3]:02d}{timestamp[4]:02d}.log"
            
            self.log_file = open(filename, 'w')
            self.start_time = time.time()
            self.log(f"Log started: {filename}")
            return True
        except Exception as e:
            self.log(f"❌ Error opening log file: {e}")
            self.log_file = None
            return False

    def stop_logging(self):
        if self.log_file:
            self.log("Log stopped.")
            self.log_file.close()
            self.log_file = None
            self.start_time = 0

    def log(self, message):
        elapsed_seconds = 0
        if self.start_time > 0:
            elapsed_seconds = time.time() - self.start_time
        
        formatted_message = f"[{elapsed_seconds:.2f}s] {message}"
        print(formatted_message)
        
        if self.log_file:
            self.log_file.write(formatted_message + '\n')
            self.log_file.flush()

class PumpCalibration:
    def __init__(self, file_path, logger):
        self.file_path = file_path
        self.logger = logger
        self.calibration_data = []
        self.load_calibration()

    def load_calibration(self):
        try:
            with open(self.file_path, 'r') as f:
                lines = f.readlines()
                # Skip header
                for line in lines[1:]:
                    parts = line.strip().split(',')
                    if len(parts) == 4:
                        duty, _, _, flow_gps = map(float, parts)
                        # Convert flow from g/s to g/min
                        self.calibration_data.append((duty, flow_gps * 60))
            # Sort by duty
            self.calibration_data.sort(key=lambda x: x[0])
            self.logger.log(f"✅ Loaded {len(self.calibration_data)} calibration points from {self.file_path}")
        except Exception as e:
            self.logger.log(f"❌ Could not load calibration file {self.file_path}: {e}")

    def get_duty_for_flow(self, target_flow_gpm):
        if not self.calibration_data:
            self.logger.log("❌ No calibration data available.")
            return 0
        
        if target_flow_gpm <= 0:
            return 0
        
        min_duty, min_flow = self.get_min_flow()
        if target_flow_gpm < min_flow:
            return int(min_duty)

        # Find two points to interpolate between
        for i in range(len(self.calibration_data) - 1):
            (d1, f1) = self.calibration_data[i]
            (d2, f2) = self.calibration_data[i+1]
            if f1 <= target_flow_gpm <= f2:
                if f2 == f1: return int(d1)
                duty = d1 + (d2 - d1) * (target_flow_gpm - f1) / (f2 - f1)
                return int(duty)
        
        self.logger.log(f"⚠️ Target flow {target_flow_gpm}gpm is above calibrated max, using max duty.")
        return int(self.calibration_data[-1][0])

    def get_min_flow(self):
        """Returns the lowest duty and flow rate that is not zero."""
        for duty, flow_gpm in self.calibration_data:
            if flow_gpm > 0:
                return int(duty), flow_gpm
        return 0, 0

class ChemostatController:
    def __init__(self):
        self.logger = Logger()
        self.logger.log("🧪 Initializing Chemostat Controller...")
        
        # Get pump profile for current supply voltage
        self.pump_profile = PUMP_PROFILES[SUPPLY_VOLTAGE]
        self.max_duty = self.pump_profile['max_duty']
        
        # Initialize pumps with variable PWM control
        self.pumps = {}
        self.pump_names = {1: "Media", 2: "Signal", 3: "Chamber", 4: "Overflow"}
        self.calibrations = {}

        # Load calibration data
        for i in range(1, 5):
            cal_file = f"pump{i}_{SUPPLY_VOLTAGE}V_calib.csv"
            if cal_file in os.listdir():
                self.calibrations[i] = PumpCalibration(cal_file, self.logger)
            else:
                self.logger.log(f"⚠️ Calibration file not found for pump {i}: {cal_file}")
                self.calibrations[i] = None

        # Ensure ALL pumps start from OFF before any action
        self.logger.log("🔄 Initializing pumps to OFF state...")
        for i, pin_num in enumerate(PUMP_PINS):
            pump_id = i + 1
            try:
                # Create a Pin object
                pin = Pin(pin_num, Pin.OUT)
                
                # Create PWM object, ensuring it starts with 0 duty
                pwm = PWM(pin, freq=self.pump_profile['freq'], duty=0)
                
                # For absolute certainty, set duty to 0 again.
                # This handles various MicroPython builds.
                if hasattr(pwm, "duty_u16"):
                    pwm.duty_u16(0)
                else:
                    pwm.duty(0)
                
                self.pumps[pump_id] = pwm
                self.logger.log(f"✅ Pump {pump_id} ({self.pump_names[pump_id]}) on GPIO {pin_num} - Initialized OFF")
            except Exception as e:
                self.logger.log(f"❌ Failed to init Pump {pump_id}: {e}")
        
        # Initialize LED and status
        try:
            # Initialize PWM with duty=0 in the constructor
            self.led = PWM(Pin(LED_PIN, Pin.OUT), freq=self.pump_profile['freq'], duty=0)
            if hasattr(self.led, "duty_u16"):
                self.led.duty_u16(0)
            else:
                self.led.duty(0)
            
            self.status_led = Pin(STATUS_LED_PIN, Pin.OUT)
            self.status_led.off()
            self.logger.log("✅ LED and Status LED initialized - OFF")
        except Exception as e:
            self.logger.log(f"❌ LED init failed: {e}")
            self.led = None
            self.status_led = None
        
        # Control state
        self.chemostat_running = False
        self.current_T = 0
        self.signal_queue = []
        self.signal_active = False
        
        # Current pump duty levels (0-100%) and flow rates (g/min)
        self.pump_duties = {1: 0, 2: 0, 3: 0, 4: 0}
        self.pump_flow_rates = {1: 0, 2: 0, 3: 0, 4: 0}
        
        # Timers for automatic pump control
        self.timer1 = Timer(1)
        self.timer2 = Timer(2)
        
        # Timer for low-flow pulsing
        self.pulsing_pumps = {}
        self.signal_pause_state = {'active': False}
        self.control_timer = Timer(3)
        self.control_timer.init(period=250, mode=Timer.PERIODIC, callback=self._main_control_loop)
        
        self.logger.log("🎮 Chemostat Controller Ready!")
        self.logger.log(f"⚡ Pumps operate at 0-100% duty ({SUPPLY_VOLTAGE}V profile)")
        self.logger.log(f"📊 PWM: {self.pump_profile['freq']}Hz, Max duty: {self.max_duty}")
    
    def _set_pump_pwm_duty(self, pump_id, duty_13bit):
        """Internal method to set raw 13-bit PWM duty."""
        if pump_id not in self.pumps: return False
        try:
            duty_13bit = max(0, min(duty_13bit, self.max_duty))
            if hasattr(self.pumps[pump_id], "duty_u16"):
                self.pumps[pump_id].duty_u16(duty_13bit * 8)
            else:
                self.pumps[pump_id].duty(duty_13bit >> 3)
            self.pump_duties[pump_id] = (duty_13bit / self.max_duty) * 100
            return True
        except Exception as e:
            self.logger.log(f"❌ Error setting duty for Pump {pump_id}: {e}")
            return False

    def set_pump_flow_rate(self, pump_id, flow_gpm):
        """Set pump to a specified flow rate in g/min, using pulsing for low flow."""
        self.pump_flow_rates[pump_id] = flow_gpm
        
        # Stop pulsing if it's active for this pump
        if pump_id in self.pulsing_pumps:
            del self.pulsing_pumps[pump_id]

        if flow_gpm <= 0:
            self._set_pump_pwm_duty(pump_id, 0)
            self.logger.log(f"🔧 {self.pump_names[pump_id]} Pump: OFF")
            return

        cal = self.calibrations.get(pump_id)
        if not cal:
            self.logger.log(f"⚠️ No calibration for pump {pump_id}. Interpreting flow as duty %.")
            duty_13bit = int((flow_gpm / 100.0) * self.max_duty)
            self._set_pump_pwm_duty(pump_id, duty_13bit)
            return

        min_duty, min_flow = cal.get_min_flow()

        if 0 < flow_gpm < min_flow:
            on_time = (flow_gpm / min_flow) * 60.0
            off_time = 60.0 - on_time
            self.pulsing_pumps[pump_id] = {
                'on_time': on_time, 'off_time': off_time, 'duty': min_duty,
                'state': 'off', 'next_change': time.time()
            }
            self.logger.log(f"🔧 {self.pump_names[pump_id]} Pump: Pulsing for {flow_gpm:.2f} g/min (on {on_time:.1f}s, off {off_time:.1f}s)")
        else:
            duty = cal.get_duty_for_flow(flow_gpm)
            self._set_pump_pwm_duty(pump_id, duty)
            duty_percent = (duty / self.max_duty) * 100
            self.logger.log(f"🔧 {self.pump_names[pump_id]} Pump: {flow_gpm:.2f} g/min ({duty_percent:.1f}% duty)")

    def _main_control_loop(self, timer):
        now = time.time()
        self._update_pulsing_pumps(now)
        self._update_signal_pause(now)

    def _update_pulsing_pumps(self, now):
        for pump_id, pulse_data in self.pulsing_pumps.items():
            if now >= pulse_data['next_change']:
                if pulse_data['state'] == 'on':
                    self._set_pump_pwm_duty(pump_id, 0)
                    pulse_data['state'] = 'off'
                    pulse_data['next_change'] = now + pulse_data['off_time']
                else: # state is 'off'
                    self._set_pump_pwm_duty(pump_id, pulse_data['duty'])
                    pulse_data['state'] = 'on'
                    pulse_data['next_change'] = now + pulse_data['on_time']
    
    def _update_signal_pause(self, now):
        if not self.signal_pause_state.get('active'):
            return

        state = self.signal_pause_state
        if now >= state['end_time']:
            phase = state['phase']
            if phase == 'inject':
                self.logger.log("⏱️  Signal Pause: Mix phase")
                self.set_pump_flow_rate(2, 0)
                state['phase'] = 'mix'
                state['end_time'] = now + state['mix_duration']
            elif phase == 'mix':
                self.logger.log("⏱️  Signal Pause: Pause phase")
                self.set_pump_flow_rate(1, 0)
                self.set_pump_flow_rate(3, 0)
                state['phase'] = 'pause'
                state['end_time'] = now + state['pause_duration']
            elif phase == 'pause':
                self.logger.log("⏱️  Signal Pause: Resuming normal operation")
                self.set_pump_flow_rate(1, state['original_flows'][1])
                self.set_pump_flow_rate(3, state['original_flows'][3])
                state['active'] = False
    
    def chemostat_cycle(self, T_seconds, media_flow, chamber_flow, overflow_flow, log_filename=None):
        """Run one chemostat cycle using timers with flow rate control."""
        if self.chemostat_running:
            self.logger.log("❌ Chemostat already running! Stop first.")
            return
        
        if log_filename and not self.logger.start_logging(log_filename):
            self.logger.log("❌ Could not start logging. Aborting cycle.")
            return

        self.logger.log(f"\n🚀 Starting Chemostat Cycle: T = {T_seconds} seconds")
        self.logger.log(f"   Media Pump (1): {T_seconds}s at {media_flow} g/min")
        self.logger.log(f"   Chamber Pump (3): {T_seconds}s at {chamber_flow} g/min")
        self.logger.log(f"   Overflow Pump (4): {T_seconds * OVERFLOW_MULTIPLIER}s at {overflow_flow} g/min")
        
        self.chemostat_running = True
        self.current_T = T_seconds
        
        # Start pumps 1, 3, 4 immediately with specified flow rates
        self.set_pump_flow_rate(1, media_flow)
        self.set_pump_flow_rate(3, chamber_flow)
        self.set_pump_flow_rate(4, overflow_flow)
        
        # Set timer to stop pumps 1&3 after T seconds
        self.timer1.init(period=T_seconds * 1000, mode=Timer.ONE_SHOT, 
                         callback=self._stop_media_chamber)
        
        # Set timer to stop pump 4 after 3T seconds
        self.timer2.init(period=T_seconds * OVERFLOW_MULTIPLIER * 1000, mode=Timer.ONE_SHOT,
                         callback=self._stop_overflow_and_finish)
        
        self.logger.log("✅ Chemostat cycle started!")
        self.logger.log("💡 You can now send signal() commands!")
        self.logger.log(">>> Ready for input")

    def chemostat_start(self, media_flow, chamber_flow, overflow_flow, log_filename):
        """Run chemostat in continuous mode."""
        if self.chemostat_running:
            self.logger.log("❌ Chemostat already running! Stop first.")
            return

        if not self.logger.start_logging(log_filename):
            self.logger.log("❌ Could not start logging. Aborting start.")
            return

        self.logger.log(f"\n🚀 Starting Chemostat in Continuous Mode")
        self.logger.log(f"   Media Pump (1): {media_flow} g/min")
        self.logger.log(f"   Chamber Pump (3): {chamber_flow} g/min")
        self.logger.log(f"   Overflow Pump (4): {overflow_flow} g/min")

        self.chemostat_running = True
        self.current_T = -1  # Indicate continuous mode

        # Start pumps
        self.set_pump_flow_rate(1, media_flow)
        self.set_pump_flow_rate(3, chamber_flow)
        self.set_pump_flow_rate(4, overflow_flow)

        self.logger.log("✅ Chemostat running continuously. Use stop() to end.")
    
    def _stop_media_chamber(self, timer):
        """Timer callback to stop media and chamber pumps"""
        self.logger.log("⏱️  Stopping Media + Chamber pumps")
        self.set_pump_flow_rate(1, 0)
        self.set_pump_flow_rate(3, 0)
        self.logger.log("💡 Signal commands still available!")
    
    def _stop_overflow_and_finish(self, timer):
        """Timer callback to stop overflow pump and finish cycle"""
        self.logger.log("⏱️  Stopping Overflow pump")
        self.set_pump_flow_rate(4, 0)
        
        if self.status_led:
            self.status_led.off()
        
        # Mark cycle as complete
        self.chemostat_running = False
        self.logger.log("✅ Chemostat cycle complete!")
        self.logger.stop_logging()
    
    
    def inject_signal(self, duration_sec=None, signal_flow=10):
        """Inject signal material with flow rate control."""
        duration_sec = duration_sec or DEFAULT_SIGNAL_TIME
        
        if self.signal_active or self.signal_pause_state.get('active'):
            self.logger.log("💉 Signal or sequence already active - please wait")
            return
        
        self.logger.log(f"💉 Signal Injection: {signal_flow} g/min for {duration_sec}s")
        
        # Start signal pump
        self.signal_active = True
        self.set_pump_flow_rate(2, signal_flow)
        
        # Set timer to stop signal pump
        signal_timer = Timer(0)  # Use timer 0 for signals
        signal_timer.init(period=duration_sec * 1000, mode=Timer.ONE_SHOT,
                         callback=lambda t: self._stop_signal(signal_timer))
    
    def _stop_signal(self, timer):
        """Timer callback to stop signal pump"""
        self.set_pump_flow_rate(2, 0)
        self.signal_active = False
        timer.deinit()
        self.logger.log("✅ Signal injection complete")
    
    def signal_pause(self, time_s, amount_gpm, mixing_time_s, pause_s):
        """Run the full inject-mix-pause sequence."""
        if self.signal_active or self.signal_pause_state.get('active'):
            self.logger.log("💉 Signal or sequence already active - please wait")
            return

        self.logger.log(f"\n🚀 Starting Signal-Pause Sequence...")
        self.logger.log(f"   Inject: {time_s}s at {amount_gpm} g/min")
        self.logger.log(f"   Mix: {mixing_time_s}s")
        self.logger.log(f"   Pause: {pause_s}s (Pumps 1 & 3 off)")

        self.signal_pause_state = {
            'active': True,
            'phase': 'inject',
            'end_time': time.time() + time_s,
            'mix_duration': mixing_time_s,
            'pause_duration': pause_s,
            'original_flows': {
                1: self.pump_flow_rates.get(1, 0),
                3: self.pump_flow_rates.get(3, 0)
            }
        }
        self.set_pump_flow_rate(2, amount_gpm)

    def stop_chemostat(self):
        """Stop current chemostat cycle or continuous run."""
        if not self.chemostat_running:
            self.logger.log("ℹ️  No chemostat cycle running")
            return
        
        self.logger.log("🛑 Stopping chemostat...")
        
        # Stop all timers safely
        try:
            self.timer1.deinit()
            self.timer2.deinit()
        except Exception:
            pass  # Timers may not be initialized
        
        # Reset any active sequences
        self.signal_pause_state = {'active': False}
        
        # Stop pumps 1, 3, 4 (leave signal pump alone)
        self.set_pump_flow_rate(1, 0)
        self.set_pump_flow_rate(3, 0)
        self.set_pump_flow_rate(4, 0)
        
        if self.status_led:
            self.status_led.off()
        
        self.chemostat_running = False
        self.logger.log("✅ Chemostat run stopped")
        self.logger.stop_logging()
    
    def get_status(self):
        """Get current system status with pump flow rates."""
        status = {
            'chemostat_running': self.chemostat_running,
            'current_T': self.current_T,
            'signal_active': self.signal_active,
            'pump_flow_rates': self.pump_flow_rates.copy()
        }
        
        self.logger.log(f"\n📊 System Status:")
        if status['chemostat_running']:
            if status['current_T'] == -1:
                run_mode = "RUNNING (Continuous)"
            else:
                run_mode = f"RUNNING (Cycle T={status['current_T']}s)"
        else:
            run_mode = "IDLE"
            
        self.logger.log(f"  Chemostat: {run_mode}")
        self.logger.log(f"  Signal: {'ACTIVE' if status['signal_active'] else 'IDLE'}")
        self.logger.log(f"  Pump Flows (g/min): Media={self.pump_flow_rates[1]:.2f}, Signal={self.pump_flow_rates[2]:.2f}, Chamber={self.pump_flow_rates[3]:.2f}, Overflow={self.pump_flow_rates[4]:.2f}")
        
        return status
    
    def emergency_stop(self):
        """Emergency stop all pumps"""
        self.logger.log("\n🚨 EMERGENCY STOP!")
        
        # Stop all timers
        try:
            self.timer1.deinit()
            self.timer2.deinit()
            self.led_timer.deinit()
        except:
            pass
        
        self.chemostat_running = False
        self.signal_active = False
        self.signal_pause_state = {'active': False}
        
        # Turn off all pumps
        for pump_id in self.pumps:
            self.set_pump_flow_rate(pump_id, 0)
        
        # Flash status LED
        if self.status_led:
            self.status_led.off()
            for _ in range(10):
                self.status_led.on()
                time.sleep(0.1)
                self.status_led.off()
                time.sleep(0.1)
        
        self.logger.log("✅ All systems stopped")
        self.logger.stop_logging()
    
    def set_voltage_profile(self, voltage):
        """Change voltage profile (5V or 12V) - requires restart"""
        global SUPPLY_VOLTAGE
        if voltage in PUMP_PROFILES:
            SUPPLY_VOLTAGE = voltage
            self.logger.log(f"⚡ Voltage profile set to {voltage}V - restart controller to apply")
        else:
            self.logger.log(f"❌ Invalid voltage: {voltage}V. Available: {list(PUMP_PROFILES.keys())}")

# Global controller instance
controller = None

def init():
    """Initialize chemostat controller"""
    global controller
    controller = ChemostatController()
    
    # The initial prints should not be logged as they happen before logging starts
    print("\n" + "="*50)
    print("🎮 Chemostat Commands:")
    print("  chemostat(T, m, c, o)    - Run fixed cycle: T=time, m,c,o=flow rate (g/min)")
    print("  start(m, c, o)           - Run continuously with flow rates (g/min)")
    print("  signal(time, flow)       - Inject signal with flow rate (g/min)")
    print("  signal_pause(t,a,m,p)    - Run inject-mix-pause sequence")
    print("  pump(id, duty)           - Set individual pump (e.g., pump(1, 50))")
    print("  stop()                   - Stop current cycle")
    print("  status()                 - Show system status")
    print("  emergency()              - Emergency stop all")
    print("  set_voltage(V)           - Set voltage profile (5 or 12)")
    print("\nExamples:")
    print("  chemostat(15, 10, 10, 30)# 15s cycle with specified flow rates")
    print("  start(10, 10, 30)        # Continuous run with specified flow rates")
    print("  signal(10, 5)            # 10s signal injection at 5 g/min")
    print("  pump(2, 2.5)             # Set signal pump to 2.5 g/min continuously")
    print("="*50)

def chemostat(T_seconds, media_flow, chamber_flow, overflow_flow):
    """Run chemostat cycle with flow rate control"""
    if controller:
        log_filename = input("Enter log file name (or press Enter for default): ").strip()
        controller.chemostat_cycle(T_seconds, media_flow, chamber_flow, overflow_flow, log_filename)
    else:
        print("❌ Call init() first!")

def start(media_flow, chamber_flow, overflow_flow):
    """Run chemostat continuously with specified flow rates."""
    if controller:
        log_filename = input("Enter log file name (or press Enter for default): ").strip()
        controller.chemostat_start(media_flow, chamber_flow, overflow_flow, log_filename)
    else:
        print("❌ Call init() first!")

def chemostat_custom(T_seconds, media_duty, chamber_duty, overflow_duty):
    """Run chemostat cycle with explicit duty cycles - alias for chemostat()"""
    return chemostat(T_seconds, media_duty, chamber_duty, overflow_duty)

def signal(duration=DEFAULT_SIGNAL_TIME, signal_flow=10):
    """Inject signal material with flow rate control"""
    if controller:
        controller.inject_signal(duration, signal_flow)
    else:
        print("❌ Call init() first!")

def signal_pause(time_s, amount_gpm, mixing_time_s, pause_s):
    """Run the full inject-mix-pause sequence."""
    if controller:
        controller.signal_pause(time_s, amount_gpm, mixing_time_s, pause_s)
    else:
        print("❌ Call init() first!")

def pump(pump_id, flow_gpm):
    """Set individual pump to specified flow rate"""
    if controller:
        return controller.set_pump_flow_rate(pump_id, flow_gpm)
    else:
        print("❌ Call init() first!")
        return False

def stop():
    """Stop current chemostat cycle or continuous run."""
    if controller:
        controller.stop_chemostat()
    else:
        print("❌ Call init() first!")

def status():
    """Show system status"""
    if controller:
        return controller.get_status()
    else:
        print("❌ Call init() first!")

def emergency():
    """Emergency stop"""
    if controller:
        controller.emergency_stop()
    else:
        print("❌ Call init() first!")

def set_voltage(voltage):
    """Set voltage profile (5V or 12V)"""
    if controller:
        controller.set_voltage_profile(voltage)
    else:
        print("❌ Call init() first!")

# Convenience aliases
def media(flow_gpm):
    """Set media pump (pump 1) flow rate"""
    return pump(1, flow_gpm)

def signal_pump(flow_gpm):
    """Set signal pump (pump 2) flow rate"""
    return pump(2, flow_gpm)

def chamber(flow_gpm):
    """Set chamber pump (pump 3) flow rate"""
    return pump(3, flow_gpm)

def overflow(flow_gpm):
    """Set overflow pump (pump 4) flow rate"""
    return pump(4, flow_gpm)

def all_off():
    """Turn off all pumps"""
    if controller:
        for pump_id in range(1, 5):
            controller.set_pump_flow_rate(pump_id, 0)
        controller.logger.log("🔧 All pumps OFF")
    else:
        print("❌ Call init() first!")

# Auto-initialize
# These prints are for initial user info and should not be logged.
print("\n" + "="*50)
print("🧪 MCMC Variable PWM Chemostat Controller")
print("=" * 50)
init()
