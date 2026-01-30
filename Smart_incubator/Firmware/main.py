# main.py - Smart Incubator Control System
from machine import Pin, PWM
import time
import gc

# Defer heavy imports until after WiFi setup to save memory
# These will be imported later:
# from max31865 import init_max31865, read_temperature
# from sd_logger import ExperimentLogger, init_sd, deinit as sd_deinit
# from oled_display import OLEDDisplay
# from temp_controller import TempController
# from led_control import LED
# from vibration_control import Vibration
# from us_control import USController
# from run_experiment_cycle import run_experiment_cycle

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
wifi_ap = None
setup_server = None

# ---- EXPERIMENT CONFIGURATION (defaults, will be overridden by web config) ----
basal_temp = 23.0
heat_shock_temp = 32.0
us_type = "BOTH"
min_interval = 200      # minutes (not seconds!)
max_interval = 400      # minutes (not seconds!)
us_duration_seconds = 1800     # US window length in seconds (30 minutes)
heat_duration_seconds = 1800     # Heat shock duration in seconds (30 minutes)
correlation = 1.0     # Range [-1, 1]: -1 = no US, 0 = random, 1 = paired US before heat
experiment_name = "default_experiment"

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
    from max31865 import init_max31865
    return init_max31865()

def init_display():
    """Initialize OLED display (optional - system continues if this fails)."""
    try:
        from oled_display import OLEDDisplay
        display = OLEDDisplay()
        print("[System] OLED display initialized successfully")
        return display
    except Exception as e:
        print(f"[WARNING] OLED display initialization failed: {e}")
        print("[WARNING] System will continue without display")
        return None

def init_temp_controller():
    """Initialize temperature controller."""
    from temp_controller import TempController
    # Reverted PID parameters to original values for 1kHz PWM frequency
    return TempController(PTC_PIN, TEC_PIN, kp=6.0, ki=0.02, kd=1.5)

def init_us_controller():
    """Initialize US controller."""
    global led_pwm, vib_pwm
    from led_control import LED
    from vibration_control import Vibration
    from us_control import USController
    led = LED(led_pwm)
    vibration = Vibration(vib_pwm)
    return USController(led, vibration)

def cleanup_globals():
    """Clean up global variables for retry attempts."""
    global display, temp_ctrl, us_controller, experiment_logger, wifi_ap, setup_server
    
    print("[Cleanup] Cleaning up resources...")
    
    # Stop WiFi AP if active
    if wifi_ap:
        try:
            wifi_ap.active(False)
            wifi_ap = None
        except:
            pass
    
    # Stop setup server if active
    if setup_server:
        try:
            setup_server.stop_server()
            setup_server = None
        except:
            pass
    
    # Deinitialize SD card SPI resources
    try:
        from sd_logger import deinit as sd_deinit
        sd_deinit()
    except:
        pass
    
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
    global basal_temp, heat_shock_temp, us_type, min_interval, max_interval
    global us_duration_seconds, heat_duration_seconds, correlation, experiment_name
    
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
        from sd_logger import ExperimentLogger, init_sd
        if not init_sd():
            raise Exception("SD card initialization failed")
        
        # Initialize experiment logger with current parameters
        print("[System] Initializing experiment logger...")
        us_duration_minutes = us_duration_seconds / 60.0
        heat_duration_minutes = heat_duration_seconds / 60.0

        experiment_params = {
            'experiment_name': str(experiment_name),
            'basal_temp': float(basal_temp),
            'heat_shock_temp': float(heat_shock_temp),
            'us_type': str(us_type),
            'min_interval': int(min_interval),
            'max_interval': int(max_interval),
            'us_duration': us_duration_minutes,
            'heat_duration': heat_duration_minutes,
            'us_duration_seconds': int(us_duration_seconds),
            'heat_duration_seconds': int(heat_duration_seconds),
            'correlation': float(correlation)
        }
        experiment_logger = ExperimentLogger(experiment_params)
        
        if not experiment_logger.init_experiment():
            raise Exception("Experiment logger initialization failed")
        
        print("[System] All components initialized successfully")
        return True
        
    except Exception as e:
        print(f"[ERROR] System initialization failed: {e}")
        return False

def wait_for_web_config():
    """
    Start WiFi AP and web server, wait for user to configure and start experiment.
    Returns the experiment configuration when user clicks start.
    """
    global wifi_ap, setup_server
    
    # Import WiFi modules now (deferred to save memory at boot)
    from wifi_setup import create_ap, get_unique_device_id
    from experiment_setup_server import ExperimentSetupServer
    
    # Force garbage collection before WiFi
    gc.collect()
    print(f"[Memory] Before WiFi: {gc.mem_free()} bytes")
    
    # Get unique device ID
    device_id = get_unique_device_id()
    print(f"[Setup] Device ID: {device_id}")
    
    # Create WiFi Access Point with unique SSID
    print("[Setup] Creating WiFi Access Point...")
    gc.collect()
    wifi_ap, ssid, ip = create_ap()
    
    gc.collect()
    print(f"[Memory] After WiFi: {gc.mem_free()} bytes")
    
    # Initialize temperature sensor for web display
    print("[Setup] Initializing temperature sensor...")
    try:
        from max31865 import init_max31865
        init_max31865()
    except Exception as e:
        print(f"[Setup] Temp sensor warning: {e}")
    
    gc.collect()
    
    # Create and start setup server
    setup_server = ExperimentSetupServer(device_id=device_id)
    setup_server.start_server(port=80)
    
    # Display connection info on OLED if available
    try:
        from oled_display import OLEDDisplay
        temp_display = OLEDDisplay()
        temp_display.clear()
        temp_display.show_message(f"WiFi: {ssid}", line=0)
        temp_display.show_message(f"Pass: incubator123", line=1)
        temp_display.show_message(f"IP: {ip}", line=2)
        temp_display.show_message("Waiting...", line=3)
    except:
        pass
    
    print(f"\nConnect to WiFi: {ssid}")
    print(f"Password: incubator123")
    print(f"Open: http://{ip}\n")
    
    # Wait for user to configure and start
    config = setup_server.serve_until_start()
    
    # Clean up server
    setup_server.stop_server()
    setup_server = None
    
    # Stop WiFi to free memory for experiment
    if wifi_ap:
        wifi_ap.active(False)
        wifi_ap = None
    
    gc.collect()
    mode = config.get('mode', 'experiment')
    if mode == 'stress':
        print("[Setup] Config received: stress test")
        print(f"[Setup] Test: {config.get('experiment_name', 'stress_test')}")
    else:
        print(f"[Setup] Config received: {config.get('experiment_name', 'experiment')}, corr={config.get('correlation', 0)}")
    print(f"[Memory] After cleanup: {gc.mem_free()} bytes")
    
    return config

def run_stress_test(config):
    """Run stress test protocol with web-configured parameters."""
    from main_test import (
        init_output_pins as test_init_pins,
        init_temp_sensor as test_init_sensor,
        init_display as test_init_display,
        init_temp_controller as test_init_temp_ctrl,
        init_us_controller as test_init_us_ctrl,
        run_stage,
        cleanup_globals as test_cleanup
    )
    from sd_logger import ExperimentLogger, init_sd
    import main_test
    
    # Apply web config to main_test module
    main_test.experiment_name = config.get('experiment_name', 'stress_test')
    main_test.training_temp = config['training_temp']
    main_test.challenge_temp = config['challenge_temp']
    main_test.training_duration_seconds = config['training_duration'] * 60
    main_test.challenge_duration_seconds = config['challenge_duration'] * 60
    main_test.us_led_intensity = config['us_led_intensity']
    main_test.us_vibration_intensity = config['us_vib_intensity']
    main_test.us_type = config['us_type']
    main_test.test_notes = config.get('notes', 'Web-configured stress test')
    
    print("\n[Stress Test] Initializing hardware...")
    
    test_init_pins()
    if not test_init_sensor():
        raise RuntimeError("Temperature sensor initialization failed")
    
    main_test.display = test_init_display()
    main_test.temp_ctrl = test_init_temp_ctrl()
    main_test.us_controller = test_init_us_ctrl()
    
    print("[Stress Test] Initializing SD card...")
    if not init_sd():
        raise RuntimeError("SD card initialization failed")
    
    # Create experiment logger with stress test params
    experiment_params = {
        "mode": "post_training_test",
        "experiment_name": config['experiment_name'],
        "training_temp": float(config['training_temp']),
        "training_duration_minutes": config['training_duration'],
        "challenge_temp": float(config['challenge_temp']),
        "challenge_duration_minutes": config['challenge_duration'],
        "us_led_intensity": int(config['us_led_intensity']),
        "us_vibration_intensity": int(config['us_vib_intensity']),
        "us_type": config['us_type'],
        "notes": config.get('notes', '')
    }
    main_test.experiment_logger = ExperimentLogger(experiment_params)
    if not main_test.experiment_logger.init_experiment():
        raise RuntimeError("Experiment logger initialization failed")
    
    print("[Stress Test] Starting protocol...")
    
    try:
        # Run training stage with US
        if not run_stage(
            stage_name="training_us",
            cycle_number=1,
            target_temp=main_test.training_temp,
            duration_seconds=main_test.training_duration_seconds,
            activate_us=True
        ):
            raise RuntimeError("Training stage failed")
        
        # Run heat challenge
        if not run_stage(
            stage_name="heat_challenge",
            cycle_number=2,
            target_temp=main_test.challenge_temp,
            duration_seconds=main_test.challenge_duration_seconds,
            activate_us=False
        ):
            raise RuntimeError("Challenge stage failed")
        
        print("\n[Stress Test] Protocol complete!")
        main_test.experiment_logger.finalize_experiment(status="completed")
        return True
        
    except Exception as e:
        print(f"[Stress Test] Error: {e}")
        if main_test.experiment_logger:
            main_test.experiment_logger.finalize_experiment(status="error", error=str(e))
        raise
    finally:
        if main_test.temp_ctrl:
            main_test.temp_ctrl.heater.turn_off()
            main_test.temp_ctrl.cooler.turn_off()
        if main_test.us_controller:
            main_test.us_controller.deactivate(main_test.us_type)
        if main_test.display:
            main_test.display.clear()


def main():
    """Main program loop."""
    global basal_temp, heat_shock_temp, us_type, min_interval, max_interval
    global us_duration_seconds, heat_duration_seconds, correlation, experiment_name
    global wifi_ap
    
    print("\n" + "="*60)
    print("   SMART INCUBATOR CONTROL SYSTEM v2.0")
    print("   WiFi Configuration Mode")
    print("="*60)
    
    # Print initial memory status
    gc.collect()
    print(f"[Memory] Initial free heap: {gc.mem_free()} bytes")
    
    # PHASE 1: Wait for web configuration
    print("\n[Phase 1] Starting WiFi setup mode...")
    try:
        config = wait_for_web_config()
        
        # Check if stress test mode was selected
        if config.get('mode') == 'stress':
            print("\n[Mode] Stress Test selected")
            print(f"  - Test Name: {config['experiment_name']}")
            print(f"  - Training: {config['training_temp']}°C for {config['training_duration']}m")
            print(f"  - Challenge: {config['challenge_temp']}°C for {config['challenge_duration']}m")
            print(f"  - US: LED {config['us_led_intensity']}% / Vib {config['us_vib_intensity']}%")
            
            try:
                run_stress_test(config)
                print("\n[Stress Test] Completed successfully!")
            except Exception as e:
                print(f"\n[Stress Test] Failed: {e}")
            return
        
        # Normal experiment mode
        experiment_name = config['experiment_name']
        correlation = config['correlation']
        basal_temp = config['basal_temp']
        heat_shock_temp = config['heat_shock_temp']
        us_type = config['us_type']
        min_interval = config['min_interval']
        max_interval = config['max_interval']
        us_duration_seconds = config['us_duration'] * 60  # Convert minutes to seconds
        heat_duration_seconds = config['heat_duration'] * 60  # Convert minutes to seconds
        
        print("\n[Config] Applied configuration:")
        print(f"  - Experiment: {experiment_name}")
        print(f"  - Correlation: {correlation}")
        print(f"  - Basal Temp: {basal_temp}°C")
        print(f"  - Heat Shock: {heat_shock_temp}°C")
        print(f"  - US Type: {us_type}")
        print(f"  - Interval: {min_interval}-{max_interval} min")
        print(f"  - US Duration: {us_duration_seconds}s")
        print(f"  - Heat Duration: {heat_duration_seconds}s")
        
    except Exception as e:
        print(f"[ERROR] Web configuration failed: {e}")
        print("[ERROR] Please restart device and try again.")
        return
    
    # PHASE 2: System initialization
    print("\n[Phase 2] Initializing system components...")
    
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
    
    # PHASE 3: Run experiment cycles
    print("\n[Phase 3] Starting experiment cycles...")
    print(f"Experiment: {experiment_name}")
    print(f"Correlation: {correlation}\n")
    
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
            from run_experiment_cycle import run_experiment_cycle
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
