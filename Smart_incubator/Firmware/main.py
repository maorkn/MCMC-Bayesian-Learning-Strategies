# main.py - Smart Incubator Control System
from machine import Pin, PWM
import time
import gc
from max31865 import init_max31865, read_temperature
from sd_logger import ExperimentLogger, init_sd, deinit as sd_deinit
from oled_display import OLEDDisplay
from temp_controller import TempController
from led_control import LED
from vibration_control import Vibration
from us_control import USController
from run_experiment_cycle import run_experiment_cycle

# ---- PIN DEFINITIONS ----
TEC_PIN = 27  # TEC1 cooler control pin
LED_PIN = 25  # LED control pin
VIB_PIN = 16  # Vibration control pin
PTC_PIN = 33  # PTC heater control pin

# ---- GLOBAL VARIABLES ----
display = None
temp_ctrl = None
us_controller = None
led_pwm = None
vib_pwm = None
experiment_logger = None

# ---- EXPERIMENT CONFIGURATION ----
basal_temp = 23.0
heat_shock_temp = 32.0
us_type = "BOTH"
min_interval = 200      # minutes (not seconds!)
max_interval = 400      # minutes (not seconds!)
us_duration_seconds = 1800     # US window length in seconds (30 minutes)
heat_duration_seconds = 1800     # Heat shock duration in seconds (30 minutes)
correlation = 1       # US precedes heat shock at end of cycle

def init_output_pins():
    """Initialize all output pins with PWM."""
    global led_pwm, vib_pwm
    
    # Initialize PWM pins
    led_pwm = PWM(Pin(LED_PIN))
    vib_pwm = PWM(Pin(VIB_PIN))
    
    # Set PWM frequency for all pins
    for pwm in [led_pwm, vib_pwm]:
        pwm.freq(1000)  # 1kHz PWM frequency
        pwm.duty_u16(0)  # Start with 0% duty cycle using 16-bit resolution
    
    return True

def init_temp_sensor():
    """Initialize temperature sensor."""
    return init_max31865()

def init_display():
    """Initialize OLED display (optional - system continues if this fails)."""
    try:
        display = OLEDDisplay()
        print("[System] OLED display initialized successfully")
        return display
    except Exception as e:
        print(f"[WARNING] OLED display initialization failed: {e}")
        print("[WARNING] System will continue without display")
        return None

def init_temp_controller():
    """Initialize temperature controller."""
    # Reverted PID parameters to original values for 1kHz PWM frequency
    return TempController(PTC_PIN, TEC_PIN, kp=6.0, ki=0.02, kd=1.5)

def init_us_controller():
    """Initialize US controller."""
    global led_pwm, vib_pwm
    led = LED(led_pwm)
    vibration = Vibration(vib_pwm)
    return USController(led, vibration)

def cleanup_globals():
    """Clean up global variables for retry attempts."""
    global display, temp_ctrl, us_controller, experiment_logger
    
    print("[Cleanup] Cleaning up SPI and hardware resources...")
    
    # Deinitialize SD card SPI resources first
    try:
        sd_deinit()
        print("[Cleanup] SD card SPI deinitialized")
    except Exception as e:
        print(f"[Cleanup] SD deinit warning: {e}")
    
    # Add delay to ensure SPI buses are fully released
    time.sleep(1)
    
    # Reset all global variables
    display = None
    temp_ctrl = None
    us_controller = None
    experiment_logger = None
    
    # Force garbage collection
    gc.collect()
    print("[Cleanup] Global variables reset and memory cleaned")

def init_system():
    """Initialize all system components."""
    global display, temp_ctrl, us_controller, experiment_logger
    
    try:
        print("\n=== Smart Incubator Control System ===")
        print("Initializing...")
        
        # Initialize output pins
        print("[System] Initializing output pins...")
        init_output_pins()
        print("[System] All output pins initialized and cleared")
        
        # Initialize temperature sensor
        print("[System] Initializing temperature sensor...")
        temp_sensor = init_temp_sensor()
        if not temp_sensor:
            raise Exception("Temperature sensor initialization failed")
        
        # Initialize display (optional - don't fail if this doesn't work)
        print("[System] Initializing display...")
        display = init_display()
        if display is None:
            print("[System] Continuing without display...")
        
        # Initialize temperature controller
        print("[System] Initializing temperature controller...")
        temp_ctrl = init_temp_controller()
        if not temp_ctrl:
            raise Exception("Temperature controller initialization failed")
        
        # Initialize US controller
        print("[System] Initializing US controller...")
        us_controller = init_us_controller()
        if not us_controller:
            raise Exception("US controller initialization failed")
        
        # Initialize SD card
        print("[System] Initializing SD card...")
        if not init_sd():
            raise Exception("SD card initialization failed")
        
        # Initialize experiment logger with default name
        print("[System] Initializing experiment logger...")
        us_duration_minutes = us_duration_seconds / 60.0
        heat_duration_minutes = heat_duration_seconds / 60.0

        experiment_params = {
            'basal_temp': float(basal_temp),
            'heat_shock_temp': float(heat_shock_temp),
            'us_type': str(us_type),
            'min_interval': int(min_interval),
            'max_interval': int(max_interval),
            'us_duration': us_duration_minutes,
            'heat_duration': heat_duration_minutes,
            'us_duration_seconds': int(us_duration_seconds),
            'heat_duration_seconds': int(heat_duration_seconds),
            'correlation': int(correlation)
        }
        experiment_logger = ExperimentLogger(experiment_params)
        
        if not experiment_logger.init_experiment():
            raise Exception("Experiment logger initialization failed")
        
        print("[System] All components initialized successfully")
        return True
        
    except Exception as e:
        print(f"[ERROR] System initialization failed: {e}")
        return False

def main():
    """Main program loop."""
    print("\n=== Smart Incubator Control System ===")
    print("Initializing...")
    
    # Print initial memory status
    gc.collect()
    print(f"[Memory] Initial free heap: {gc.mem_free()} bytes")
    
    # Retry logic for system initialization
    max_init_attempts = 5
    init_delay = 10  # seconds
    
    initialization_successful = False
    
    for attempt in range(1, max_init_attempts + 1):
        print(f"\n[System] Initialization attempt {attempt}/{max_init_attempts}")
        
        # Clean up from previous attempt (except first attempt)
        if attempt > 1:
            print("[System] Cleaning up from previous attempt...")
            cleanup_globals()
        
        if init_system():
            print("\nSystem initialized successfully!")
            initialization_successful = True
            break
        else:
            print(f"[ERROR] System initialization failed on attempt {attempt}")
            
            if attempt < max_init_attempts:
                print(f"[System] Waiting {init_delay} seconds before retry...")
                time.sleep(init_delay)
                
                # Clean up memory before retry
                gc.collect()
                print(f"[Memory] Free heap before retry: {gc.mem_free()} bytes")
            else:
                print(f"[ERROR] System initialization failed after {max_init_attempts} attempts!")
                print("[ERROR] Please check hardware connections and restart.")
    
    # Exit if initialization failed
    if not initialization_successful:
        print("[SYSTEM] Initialization failed. System will not start experiment cycles.")
        print("[SYSTEM] Please fix hardware issues and restart.")
        return
    
    print("Starting experiment cycles...\n")
    
    # Configure US parameters (only if us_controller exists)
    if us_controller:
        us_controller.set_led_intensity(25)  # Set LED intensity to 25%
        us_controller.set_vib_intensity(100)  # Set vibration intensity to 100%
        us_controller.set_vib_interval("20:60")  # Set vibration interval to 20s ON, 60s OFF
        print("[System] US controller configured")
    else:
        print("[ERROR] US controller not available - cannot configure")
        return
    
    cycle_number = 1
    consecutive_errors = 0
    max_consecutive_errors = 3
    
    while True:
        try:
            # CRITICAL: Check SD health before starting cycle
            if experiment_logger and not experiment_logger.sd_write_ok:
                print(f"\n[CRITICAL] SD card is unhealthy - cannot start cycle {cycle_number}")
                print("[CRITICAL] Experiment halted to prevent data loss")
                experiment_logger.finalize_experiment(status='error', error='SD card write failures')
                break
            
            # Memory health check
            gc.collect()
            free_mem = gc.mem_free()
            print(f"\n[Memory] Free heap: {free_mem} bytes")
            if free_mem < 10000:  # Less than 10KB free
                print(f"[WARNING] Low memory detected! Free: {free_mem} bytes")
            
            print(f"\n{'='*50}")
            print(f"Starting Cycle {cycle_number}")
            print(f"{'='*50}\n")
            
            # Run experiment cycle with updated parameters
            run_experiment_cycle(
                cycle_number=cycle_number,
                display=display,
                temp_ctrl=temp_ctrl,
                us_controller=us_controller,
                min_interval=min_interval,
                max_interval=max_interval,
                us_type=us_type,
                us_duration=us_duration_seconds,
                correlation=correlation,
                heat_duration=heat_duration_seconds,
                basal_temp=basal_temp,
                heat_shock_temp=heat_shock_temp,
                log_interval=10,    # Log every 10 seconds
                experiment_logger=experiment_logger  # Pass the experiment logger
            )
            
            # Reset error counter on successful cycle
            consecutive_errors = 0
            cycle_number += 1
            
            # Add a small delay between cycles
            time.sleep(2)
            
            # Memory cleanup between cycles
            gc.collect()
            
        except Exception as e:
            consecutive_errors += 1
            print(f"\n[ERROR] Cycle {cycle_number} failed: {e}")
            print(f"[ERROR] Consecutive errors: {consecutive_errors}/{max_consecutive_errors}")
            
            # Attempt to recover by turning off all outputs
            if temp_ctrl:
                temp_ctrl.heater.turn_off()
                temp_ctrl.cooler.turn_off()
            if us_controller:
                us_controller.deactivate("BOTH")
                
            if consecutive_errors >= max_consecutive_errors:
                print("[ERROR] Too many consecutive errors. Stopping experiment.")
                if experiment_logger:
                    experiment_logger.finalize_experiment(status='error', error=f'Too many consecutive errors: {e}')
                break
                
            print("[ERROR] Attempting to recover...")
            cycle_number += 1
            time.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    main()