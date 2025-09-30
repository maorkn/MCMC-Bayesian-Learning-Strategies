import time
import urandom
import json
import gc
from utils import generate_random_interval
from sd_logger import ExperimentLogger, init_sd
from max31865 import init_max31865, read_temperature, check_fault
from machine import Pin

def run_experiment_cycle(
    cycle_number,
    display,
    temp_ctrl,
    us_controller,
    min_interval,
    max_interval,
    us_type,
    us_duration,
    correlation,
    heat_duration,
    basal_temp,
    heat_shock_temp,
    log_interval,
    experiment_logger=None  # Add experiment logger parameter
):
    """Run a single experiment cycle."""
    print(f"\n[Cycle {cycle_number}] Starting new cycle...")
    
    # Print input parameters
    print("\nInput Parameters:")
    print(f"min_interval: {min_interval} minutes")
    print(f"max_interval: {max_interval} minutes")
    print(f"us_duration: {us_duration} minutes")
    print(f"heat_duration: {heat_duration} minutes")
    
    # Calculate cycle parameters
    cycle_length = urandom.randint(min_interval, max_interval)
    
    # Calculate US and heat start times based on correlation
    if correlation == 0:
        # Correlation 0: Completely random US and heat shock
        heat_start = urandom.randint(0, cycle_length - heat_duration)
        us_start = urandom.randint(0, cycle_length - us_duration)
    elif correlation == 1:
        # Correlation 1: US precedes heat shock (at end of cycle)
        heat_start = cycle_length - heat_duration
        us_start = heat_start - us_duration
    elif correlation == 2:
        # Correlation 2: US follows heat shock
        heat_start = cycle_length - heat_duration - us_duration
        us_start = heat_start + heat_duration
    elif correlation == 3:
        # Correlation 3: Early stimuli for testing (heat shock at 1 minute, US before)
        heat_start = 1.0  # Start heat shock at 1 minute
        us_start = 0.5    # Start US at 30 seconds
    else:
        # Default to correlation 1 behavior
        heat_start = cycle_length - heat_duration
        us_start = heat_start - us_duration
    
    # Print cycle parameters
    print("\nCycle Parameters:")
    print(f"Cycle Length: {cycle_length} minutes")
    print(f"US Type: {us_type}")
    print(f"Correlation: {correlation}")
    print(f"US Start: {us_start} minutes")
    print(f"Heat Shock Start: {heat_start} minutes")
    print(f"Basal Temperature: {basal_temp}°C")
    print(f"Heat Shock Temperature: {heat_shock_temp}°C")
    print(f"Log Interval: {log_interval} seconds")
    print("-" * 40)
    
    # Initialize cycle data
    cycle_data = {
        "cycle": cycle_number,
        "start_time": time.time(),
        "cycle_length": cycle_length,
        "us_start": us_start,
        "heat_start": heat_start,
        "us_type": us_type,
        "correlation": correlation,
        "readings": []
    }
    
    # Run cycle
    start_time = time.time()
    last_log_time = start_time
    consecutive_invalid_readings = 0
    max_invalid_readings = 3
    last_valid_temp = None
    
    # Initialize cycle statistics
    cycle_stats = {
        'min_temp': float('inf'),
        'max_temp': float('-inf'),
        'temp_sum': 0,
        'temp_count': 0,
        'us_count': 0,
        'error_count': 0
    }
    
    # Track US state
    us_currently_active = False
    
    # Add status update tracking
    last_status_time = start_time
    status_interval = 60  # Print status every 60 seconds
    sd_card_failed = False  # Track if SD card has failed
    last_gc_time = start_time
    gc_interval = 300  # Run garbage collection every 5 minutes
    
    try:
        while time.time() - start_time < cycle_length * 60:
            current_time = time.time()
            elapsed_minutes = (current_time - start_time) / 60
            
            # Control temperature and get current reading
            target_temp = heat_shock_temp if elapsed_minutes >= heat_start else basal_temp
            
            # Debug output for heat shock
            if elapsed_minutes >= heat_start and elapsed_minutes < heat_start + 0.02:  # Print once when heat shock starts
                print(f"[DEBUG] Heat shock started at {elapsed_minutes:.2f} minutes")
                print(f"[DEBUG] Target temp changed from {basal_temp}°C to {heat_shock_temp}°C")
            
            # Small delay to avoid SPI conflicts
            time.sleep_ms(20)
            
            # Get temperature from controller (this reads the sensor internally)
            current_temp, power, mode = temp_ctrl.control_temp(target_temp)
            
            # Use the temperature from the controller
            if current_temp is None:
                print("[ERROR] Temperature controller returned None")
                consecutive_invalid_readings += 1
                cycle_stats['error_count'] += 1
                
                if consecutive_invalid_readings >= max_invalid_readings:
                    print("[ERROR] Too many consecutive invalid temperature readings")
                    print("[ERROR] Stopping experiment cycle")
                    if experiment_logger:
                        experiment_logger.finalize_experiment(status='error', error='Too many invalid temperature readings')
                    return
                
                # Use last valid temperature if available
                if last_valid_temp is not None:
                    current_temp = last_valid_temp
                    print(f"[Controller] Using last valid temperature: {current_temp}°C")
                else:
                    print("[ERROR] No valid temperature available")
                    continue
            else:
                # Check for invalid temperature readings
                if current_temp > 100 or current_temp < -50:
                    print(f"[ERROR] Invalid temperature reading: {current_temp}°C")
                    fault = check_fault()
                    if fault:
                        print(f"[MAX31865] Fault detected: {fault}")
                    
                    consecutive_invalid_readings += 1
                    cycle_stats['error_count'] += 1
                    
                    if consecutive_invalid_readings >= max_invalid_readings:
                        print("[ERROR] Too many consecutive invalid temperature readings")
                        print("[ERROR] Stopping experiment cycle")
                        if experiment_logger:
                            experiment_logger.finalize_experiment(status='error', error='Too many invalid temperature readings')
                        return
                    
                    # Use last valid temperature if available
                    if last_valid_temp is not None:
                        current_temp = last_valid_temp
                        print(f"[Controller] Using last valid temperature: {current_temp}°C")
                    else:
                        print("[ERROR] No valid temperature available")
                        continue
                else:
                    consecutive_invalid_readings = 0
                    last_valid_temp = current_temp
                    
                    # Update cycle statistics
                    cycle_stats['min_temp'] = min(cycle_stats['min_temp'], current_temp)
                    cycle_stats['max_temp'] = max(cycle_stats['max_temp'], current_temp)
                    cycle_stats['temp_sum'] += current_temp
                    cycle_stats['temp_count'] += 1
            
            # Calculate TEC state based on power value and temperature difference
            temp_diff = abs(current_temp - target_temp)
            tec_state = 1 if temp_diff > 0.1 else 0
            
            # Update US state
            us_active = (elapsed_minutes >= us_start) and (elapsed_minutes < us_start + us_duration)
            if us_active:
                if not us_currently_active:
                    us_controller.activate(us_type)
                    us_currently_active = True
                if us_type in ["VIB", "BOTH"]:
                    us_controller.update_vibration()
                cycle_stats['us_count'] += 1
            else:
                if us_currently_active:
                    us_controller.deactivate(us_type)
                    us_currently_active = False
            
            # Update display
            if display:
                display.update_display(
                    current_temp,  # current_temp from controller
                    target_temp,  # set_temp
                    elapsed_minutes,  # elapsed_minutes
                    cycle_length,  # cycle_length
                    1 if us_active else 0,  # us_active
                    1 if us_type in ["LED", "BOTH"] and us_active else 0,  # led_active
                    1 if us_type in ["VIB", "BOTH"] and us_active else 0,  # vib_active
                    tec_state,  # tec_state
                    cycle_number,  # cycle_num
                    correlation # Pass correlation value
                )
            
            # Log data if interval has passed
            if current_time - last_log_time >= log_interval and experiment_logger and not sd_card_failed:
                # --- PWM NOISE MITIGATION ---
                # Temporarily deactivate US system to ensure a clean temperature reading for the log
                if us_currently_active:
                    us_controller.deactivate(us_type)

                # Short delay for PWM noise to settle before logging
                time.sleep_ms(20)

                # Prepare snapshot data with a fresh, clean reading
                logged_temp, _, _ = temp_ctrl.control_temp(target_temp)
                if logged_temp is None:
                    logged_temp = last_valid_temp # Fallback to last known good temp

                snapshot_data = {
                    'temp': round(logged_temp, 2) if logged_temp is not None else -99,
                    'set_temp': round(target_temp, 2),
                    'us_active': 1 if us_active else 0,
                    'elapsed_minutes': round(elapsed_minutes, 2),
                    'cycle_length': cycle_length,
                    'mode': mode,
                    'power': round(power, 2),
                    'tec_state': "On" if temp_ctrl.cooler.is_on else "Off",
                    'phase': "heat_shock" if elapsed_minutes >= heat_start else "basal"
                }
                
                # Log snapshot with error handling
                try:
                    if not experiment_logger.log_snapshot(cycle_number, snapshot_data):
                        print("[ERROR] Failed to save data to SD card")
                        sd_card_failed = True
                except Exception as e:
                    print(f"[ERROR] SD card logging error: {e}")
                    sd_card_failed = True
                    print("[WARNING] SD card logging disabled for this cycle. Experiment continues.")
                    # Continue running even if logging fails
                    
                last_log_time = current_time

                # --- RESUME US SYSTEM ---
                if us_currently_active:
                    us_controller.activate(us_type)
            
            # Print periodic status update
            if current_time - last_status_time >= status_interval:
                print(f"[{elapsed_minutes:.1f}/{cycle_length} min] Temp: {current_temp:.1f}°C → {target_temp:.1f}°C | Mode: {mode} | Power: {power:.1f}% | Cycle: {cycle_number}")
                last_status_time = current_time
            
            # Periodic garbage collection
            if current_time - last_gc_time >= gc_interval:
                gc.collect()
                print(f"[Memory] Free heap: {gc.mem_free()} bytes")
                last_gc_time = current_time
            
            # Debug output
            if abs(temp_diff) > 2:  # Only print when there's significant difference
                # Commented out to prevent output flooding
                # print(f"[DEBUG] Current: {current_temp:.1f}°C, Target: {target_temp:.1f}°C, Diff: {temp_diff:.1f}°C")
                pass
            
            # Shorter sleep to prevent watchdog timeout
            time.sleep(0.1)  # 100ms delay between iterations
        
        # Calculate final statistics
        if cycle_stats['temp_count'] > 0:
            cycle_stats['avg_temp'] = cycle_stats['temp_sum'] / cycle_stats['temp_count']
        else:
            cycle_stats['avg_temp'] = 0
            cycle_stats['min_temp'] = 0
            cycle_stats['max_temp'] = 0
        
        # Remove temporary statistics
        del cycle_stats['temp_sum']
        del cycle_stats['temp_count']
        
        # Add cycle completion data
        cycle_stats.update({
            'end_time': time.time(),
            'duration': time.time() - start_time,
            'final_temp': last_valid_temp if last_valid_temp is not None else 0,
            'final_power': power,
            'final_mode': mode
        })
        
        # Log cycle summary
        if experiment_logger:
            if not experiment_logger.log_cycle_summary(cycle_number, cycle_stats):
                print("[ERROR] Failed to save cycle summary")
            
    except Exception as e:
        print(f"[Cycle {cycle_number}] Error: {e}")
        if experiment_logger:
            error_data = {
                'error': str(e),
                'end_time': time.time(),
                'final_temp': last_valid_temp if last_valid_temp is not None else 0,
                'error_count': cycle_stats['error_count']
            }
            experiment_logger.log_cycle_summary(cycle_number, error_data)
            experiment_logger.finalize_experiment(status='error', error=str(e))

    # Perform garbage collection
    gc.collect()
    
    # Print memory status after cycle
    print(f"[Memory] Free heap after cycle {cycle_number}: {gc.mem_free()} bytes")
    
    # Force a second collection to be thorough
    gc.collect()
