# main_with_server.py - Smart Incubator Control System with Web Server
from machine import Pin, PWM
import time
import gc
import _thread
from max31865 import init_max31865, read_temperature
from sd_logger import ExperimentLogger, init_sd
from oled_display import OLEDDisplay
from temp_controller import TempController
from led_control import LED
from vibration_control import Vibration
from us_control import USController
from run_experiment_cycle import run_experiment_cycle
from web_server import IncubatorWebServer

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
web_server = None
server_socket = None
last_snapshot_time = 0

# ---- SD CARD THREAD SAFETY ----
_sd_lock = _thread.allocate_lock()

def safe_sd_operation(operation_func, *args, **kwargs):
    """Thread-safe wrapper for SD card operations."""
    with _sd_lock:
        return operation_func(*args, **kwargs)

# ---- EXPERIMENT CONFIGURATION (from main.py) ----
basal_temp = 23.0
heat_shock_temp = 32.0
us_type = "BOTH"
min_interval = 5      # minutes (not seconds!)
max_interval = 10      # minutes (not seconds!)
us_duration = 1     # 30 seconds = 0.5 minutes
heat_duration = 2     # 2 minutes - increased for testing to see temp change
correlation = 1.0     # Range [-1, 1]: -1 disables US, 0 random, 1 paired

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
    """Initialize OLED display."""
    return OLEDDisplay()

def init_temp_controller():
    """Initialize temperature controller."""
    return TempController(PTC_PIN, TEC_PIN, kp=6.0, ki=0.02, kd=1.5)

def init_us_controller():
    """Initialize US controller."""
    global led_pwm, vib_pwm
    led = LED(led_pwm)
    vibration = Vibration(vib_pwm)
    return USController(led, vibration)

def init_system():
    """Initialize all system components - IDENTICAL TO main.py"""
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
        
        # Initialize display
        print("[System] Initializing display...")
        display = init_display()
        if not display:
            raise Exception("Display initialization failed")
        
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
        
        # Initialize SD card with thread safety
        print("[System] Initializing SD card...")
        with _sd_lock:
            if not init_sd():
                raise Exception("SD card initialization failed")
        
        # Add delay to ensure SD card SPI is stable before experiment logger
        time.sleep_ms(200)
        print("[System] SD card stabilized")
        
        # Initialize experiment logger with thread safety
        print("[System] Initializing experiment logger...")
        experiment_params = {
            'basal_temp': float(basal_temp),
            'heat_shock_temp': float(heat_shock_temp),
            'us_type': str(us_type),
            'min_interval': int(min_interval),
            'max_interval': int(max_interval),
            'us_duration': int(us_duration),
            'heat_duration': int(heat_duration),
            'correlation': float(correlation)
        }
        
        with _sd_lock:
            experiment_logger = ExperimentLogger(experiment_params)
            if not experiment_logger.init_experiment():
                raise Exception("Experiment logger initialization failed")
        
        print("[System] All components initialized successfully")
        return True
        
    except Exception as e:
        print(f"[ERROR] System initialization failed: {e}")
        return False

def web_server_thread():
    """Web server thread function"""
    global web_server, server_socket
    
    try:
        while True:
            if server_socket:
                try:
                    client_socket, addr = server_socket.accept()
                    client_socket.settimeout(5.0)
                    
                    # Receive request
                    request = client_socket.recv(1024).decode('utf-8')
                    
                    # Handle request
                    response = web_server.handle_request(request)
                    
                    # Send response
                    client_socket.send(response.encode('utf-8'))
                    client_socket.close()
                    
                except Exception as e:
                    print(f"[Web Server] Client error: {e}")
                    try:
                        client_socket.close()
                    except:
                        pass
            else:
                time.sleep(1)
                
    except Exception as e:
        print(f"[Web Server] Thread error: {e}")

def print_monitoring_snapshot():
    """Print a monitoring snapshot every minute - WEB SERVER ONLY FEATURE"""
    global last_snapshot_time
    
    current_time = time.time()
    if current_time - last_snapshot_time >= 60:  # Every 60 seconds
        try:
            # Read current temperature
            temp = read_temperature()
            
            # Get system status
            if temp_ctrl:
                current_temp, power, mode = temp_ctrl.control_temp(basal_temp)
            else:
                current_temp, power, mode = temp, 0, "Unknown"
            
            # Get US controller status
            us_status = "Unknown"
            if us_controller:
                # This is just for display, don't actually control anything
                us_status = "Ready"
            
            # Print snapshot
            print(f"\n=== MONITORING SNAPSHOT ===")
            print(f"Time: {time.time()}")
            print(f"Temperature: {temp}°C")
            print(f"Control Mode: {mode}")
            print(f"Power: {power}%")
            print(f"US Status: {us_status}")
            print(f"Experiment Running: {web_server.is_experiment_running() if web_server else False}")
            print(f"===========================\n")
            
            last_snapshot_time = current_time
            
        except Exception as e:
            print(f"[WARNING] Snapshot error: {e}")
            last_snapshot_time = current_time  # Still update time to avoid spam

def main():
    """Main program loop with web server integration."""
    global web_server, server_socket, display, temp_ctrl, us_controller, experiment_logger, last_snapshot_time
    
    print("\n=== Smart Incubator Control System with Web Server ===")
    print("Initializing...")
    
    # Print initial memory status
    gc.collect()
    print(f"[Memory] Initial free heap: {gc.mem_free()} bytes")
    
    # Initialize web server ONLY - no hardware yet
    print("[Web Server] Setting up web server...")
    web_server = IncubatorWebServer()
    ip = web_server.setup_ap()
    
    # Clean up any existing socket
    if server_socket:
        try:
            server_socket.close()
            server_socket = None
            time.sleep(0.5)
        except:
            pass
    
    # Try to start server with retry
    for attempt in range(3):
        try:
            server_socket = web_server.start_server()
            break
        except OSError as e:
            print(f"[Web Server] Server start attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(2)  # Wait before retry
                gc.collect()  # Clean up memory
            else:
                print("[ERROR] Failed to start web server after 3 attempts")
                return
    
    # Start web server in separate thread
    print("[Web Server] Starting web server thread...")
    
    # Test SD card functionality before starting web server (as suggested)
    try:
        print("[Test] Verifying SD card write capability...")
        with _sd_lock:
            with open('/sd/test.txt', 'w') as f:
                f.write('ok')
        print("[Test] SD card write test passed")
    except Exception as e:
        print(f"[WARNING] SD card write test failed: {e}")
        print("[WARNING] This may indicate power or hardware issues")
    
    _thread.start_new_thread(web_server_thread, ())
    
    print(f"\n=== Web Server Ready ===")
    print(f"Web interface: http://{ip}")
    print(f"WiFi: ESP32-Incubator")
    print(f"Password: incubator123")
    print("========================\n")
    print("Waiting for experiment activation from web interface...")
    print("Hardware will be initialized when experiment starts.")
    
    # Initialize snapshot timer
    last_snapshot_time = time.time()
    
    # Wait for experiment to be activated
    while not web_server.is_experiment_running():
        time.sleep(1)
    
    print("\n=== Experiment Activated - Initializing Hardware ===")
    
    # NOW initialize hardware components (identical to main.py)
    if not init_system():
        print("[ERROR] System initialization failed!")
        web_server.stop_experiment()
        return
    
    print(f"\n=== Hardware Initialized Successfully ===")
    print("Starting experiment cycles...\n")
    
    # Configure US parameters (identical to main.py)
    us_controller.set_led_intensity(25)  # Set LED intensity to 25%
    us_controller.set_vib_intensity(100)  # Set vibration intensity to 100%
    us_controller.set_vib_interval("20:60")  # Set vibration interval to 20s ON, 60s OFF
    
    cycle_number = 1
    consecutive_errors = 0
    max_consecutive_errors = 3
    
    # Main control loop - IDENTICAL TO main.py but with web server parameters
    while True:
        try:
            # Print monitoring snapshot every minute
            print_monitoring_snapshot()
            
            # Check if experiment should be running
            if web_server.is_experiment_running():
                print(f"\n{'='*50}")
                print(f"Starting Cycle {cycle_number}")
                mode = "Test Mode" if web_server.is_test_mode() else "Normal Mode"
                print(f"Mode: {mode}")
                print(f"{'='*50}\n")
                
                # Get current parameters from web server
                params = web_server.get_current_params()
                
                # Run experiment cycle with web server parameters
                run_experiment_cycle(
                    cycle_number=cycle_number,
                    display=display,
                    temp_ctrl=temp_ctrl,
                    us_controller=us_controller,
                    min_interval=params['min_interval'],
                    max_interval=params['max_interval'],
                    us_type=params['us_type'],
                    us_duration=params['us_duration'],
                    correlation=params['correlation'],
                    heat_duration=params['heat_duration'],
                    basal_temp=params['basal_temp'],
                    heat_shock_temp=params['heat_shock_temp'],
                    log_interval=10,    # Fixed log interval like main.py
                    experiment_logger=experiment_logger
                )
                
                # Reset error counter on successful cycle
                consecutive_errors = 0
                cycle_number += 1
                
                # Check if experiment was stopped during cycle
                if not web_server.is_experiment_running():
                    print("[System] Experiment stopped by user")
                    # Turn off all outputs
                    if temp_ctrl:
                        temp_ctrl.heater.turn_off()
                        temp_ctrl.cooler.turn_off()
                    if us_controller:
                        us_controller.deactivate("BOTH")
                
                # Add a small delay between cycles
                time.sleep(2)
                
                # Memory cleanup between cycles
                gc.collect()
                
            else:
                # Experiment not running, just wait and monitor
                time.sleep(1)
                
                # Ensure all outputs are off when not running
                if temp_ctrl:
                    temp_ctrl.heater.turn_off()
                    temp_ctrl.cooler.turn_off()
                if us_controller:
                    us_controller.deactivate("BOTH")
            
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
                web_server.stop_experiment()
                if experiment_logger:
                    experiment_logger.finalize_experiment(status='error', error=f'Too many consecutive errors: {e}')
                consecutive_errors = 0  # Reset for next attempt
                
            print("[ERROR] Attempting to recover...")
            cycle_number += 1
            time.sleep(5)  # Wait before retrying

if __name__ == "__main__":
    # Initialize global socket variable
    server_socket = None
    try:
        main()
    except Exception as e:
        print(f"Main program error: {e}")
        # Clean up socket on error
        if 'server_socket' in globals() and server_socket:
            try:
                server_socket.close()
            except:
                pass
        print("System will remain in REPL mode") 
