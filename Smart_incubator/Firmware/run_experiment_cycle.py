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
    print(f"us_duration: {us_duration} seconds")
    print(f"heat_duration: {heat_duration} seconds")
    
    # Normalize correlation into [-1, 1] and decide per-cycle behavior
    try:
        correlation_value = float(correlation)
    except (ValueError, TypeError):
        correlation_value = 0.0
    correlation_value = max(-1.0, min(1.0, correlation_value))

    def _random_unit():
        return urandom.getrandbits(16) / 65535.0

    def _select_correlation_mode(value):
        if value >= 1.0:
            return "paired"
        if value <= -1.0:
            return "no_us"
        if value == 0.0:
            return "random"
        if value > 0.0:
            return "paired" if _random_unit() < value else "random"
        probability_no_us = abs(value)
        return "no_us" if _random_unit() < probability_no_us else "random"

    correlation_mode = _select_correlation_mode(correlation_value)

    # Calculate cycle parameters
    cycle_length_minutes = urandom.randint(min_interval, max_interval)
    cycle_length_seconds = cycle_length_minutes * 60

    # Ensure durations are positive whole seconds
    us_duration_seconds = max(1, int(us_duration))
    heat_duration_seconds = max(1, int(heat_duration))

    us_start_seconds = None
    heat_start_seconds = None
    us_enabled = correlation_mode != "no_us"

    # Calculate US and heat start times based on correlation mode (all in seconds)
    if correlation_mode == "random":
        # Correlation 0: Completely random US and heat shock (independent)
        max_heat_start = max(0, cycle_length_seconds - heat_duration_seconds)
        max_us_start = max(0, cycle_length_seconds - us_duration_seconds)
        heat_start_seconds = urandom.randint(0, max_heat_start)
        us_start_seconds = urandom.randint(0, max_us_start)
    elif correlation_mode == "paired":
        # Correlation 1: US precedes heat shock (at end of cycle)
        heat_start_seconds = max(0, cycle_length_seconds - heat_duration_seconds)
        us_start_seconds = max(0, heat_start_seconds - us_duration_seconds)
    else:
        # No US: keep heat shock deterministic at end of cycle
        heat_start_seconds = max(0, cycle_length_seconds - heat_duration_seconds)
        us_enabled = False
        us_start_seconds = None

    # Print cycle parameters
    heat_start_minutes = heat_start_seconds / 60
    us_start_minutes = us_start_seconds / 60 if us_start_seconds is not None else None
    us_duration_minutes = us_duration_seconds / 60
    heat_duration_minutes = heat_duration_seconds / 60
    cycle_length_minutes_float = cycle_length_seconds / 60

    print("\nCycle Parameters:")
    print(f"Cycle Length: {cycle_length_minutes_float:.2f} minutes")
    print(f"US Type: {us_type}")
    print(f"Correlation: {correlation_value:.2f} (mode: {correlation_mode})")
    if us_start_minutes is None:
        print("US Start: disabled")
    else:
        print(f"US Start: {us_start_minutes:.2f} minutes ({us_start_seconds} seconds)")
    print(f"Heat Shock Start: {heat_start_minutes:.2f} minutes ({heat_start_seconds} seconds)")
    print(f"US Duration: {us_duration_seconds} seconds ({us_duration_minutes:.2f} minutes)")
    print(f"Heat Duration: {heat_duration_seconds} seconds ({heat_duration_minutes:.2f} minutes)")
    print(f"Basal Temperature: {basal_temp}°C")
    print(f"Heat Shock Temperature: {heat_shock_temp}°C")
    print(f"Log Interval: {log_interval} seconds")
    print("-" * 40)
    
    # Initialize cycle data
    cycle_data = {
        "cycle": cycle_number,
        "start_time": time.time(),
        "cycle_length_seconds": cycle_length_seconds,
        "us_start_seconds": us_start_seconds,
        "heat_start_seconds": heat_start_seconds,
        "us_duration_seconds": us_duration_seconds,
        "heat_duration_seconds": heat_duration_seconds,
        "us_type": us_type,
        "correlation": correlation_value,
        "correlation_mode": correlation_mode,
        "readings": []
    }
    
    # Run cycle
    start_time = time.time()
    last_log_time = start_time
    consecutive_invalid_readings = 0
    max_invalid_readings = 10
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
    invalid_log_interval = 30  # Throttle invalid sensor logs
    last_invalid_log_time = start_time - invalid_log_interval
    
    try:
        while time.time() - start_time < cycle_length_seconds:
            current_time = time.time()
            elapsed_seconds = current_time - start_time
            elapsed_minutes = elapsed_seconds / 60
            
            # Control temperature and get current reading
            target_temp = heat_shock_temp if elapsed_seconds >= heat_start_seconds else basal_temp
            
            # Debug output for heat shock
            if elapsed_seconds >= heat_start_seconds and elapsed_seconds < heat_start_seconds + 1:  # Print once when heat shock starts
                print(f"[DEBUG] Heat shock started at {elapsed_minutes:.2f} minutes")
                print(f"[DEBUG] Target temp changed from {basal_temp}°C to {heat_shock_temp}°C")
            
            # Small delay to avoid SPI conflicts
            time.sleep_ms(20)
            
            # Get temperature from controller (this reads the sensor internally)
            current_temp, power, mode = temp_ctrl.control_temp(target_temp)
            
            # Use the temperature from the controller
            if current_temp is None:
                if current_time - last_invalid_log_time >= invalid_log_interval:
                    print("[ERROR] Temperature controller returned None")
                    last_invalid_log_time = current_time
                consecutive_invalid_readings += 1
                cycle_stats['error_count'] += 1
                
                if consecutive_invalid_readings >= max_invalid_readings:
                    print("[CRITICAL] Too many consecutive invalid temperature readings")
                    print("[CRITICAL] This indicates a sensor hardware failure - stopping experiment")
                    if experiment_logger:
                        experiment_logger.finalize_experiment(status='error', error='Too many invalid temperature readings')
                    # Raise exception to stop the entire experiment, not just this cycle
                    raise RuntimeError("Temperature sensor failure - too many consecutive invalid readings")
                
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
                    if current_time - last_invalid_log_time >= invalid_log_interval:
                        print(f"[ERROR] Invalid temperature reading: {current_temp}°C")
                        last_invalid_log_time = current_time
                    fault = check_fault()
                    if fault:
                        print(f"[MAX31865] Fault detected: {fault}")
                    
                    consecutive_invalid_readings += 1
                    cycle_stats['error_count'] += 1
                    
                    if consecutive_invalid_readings >= max_invalid_readings:
                        print("[CRITICAL] Too many consecutive invalid temperature readings")
                        print("[CRITICAL] Sensor fault detected - stopping experiment for safety")
                        if experiment_logger:
                            experiment_logger.finalize_experiment(status='error', error=f'Too many invalid temperature readings, fault: {fault}')
                        # Raise exception to stop the entire experiment, not just this cycle
                        raise RuntimeError(f"Temperature sensor fault - {fault if fault else 'unknown fault'}")
                    
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
            us_active = (
                us_enabled and
                elapsed_seconds >= us_start_seconds and
                elapsed_seconds < us_start_seconds + us_duration_seconds
            )
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
                    cycle_length_minutes_float,  # cycle_length in minutes
                    1 if us_active else 0,  # us_active
                    1 if us_type in ["LED", "BOTH"] and us_active else 0,  # led_active
                    1 if us_type in ["VIB", "BOTH"] and us_active else 0,  # vib_active
                    tec_state,  # tec_state
                    cycle_number,  # cycle_num
                    correlation_value # Pass correlation value
                )
            
            # Log data if interval has passed
            if current_time - last_log_time >= log_interval and experiment_logger and not sd_card_failed:
                # --- PWM NOISE MITIGATION ---
                # Temporarily deactivate US system to ensure a clean temperature reading for the log
                was_us_active = us_currently_active
                if was_us_active:
                    us_controller.deactivate(us_type)

                try:
                    # Short delay for PWM noise to settle before logging
                    time.sleep_ms(20)

                    # Prepare snapshot data with a fresh, clean reading
                    logged_temp = current_temp if current_temp is not None else last_valid_temp
                    if logged_temp is not None:
                        logged_temp = round(logged_temp, 2)

                    snapshot_data = {
                        'temp': logged_temp if logged_temp is not None else -99,
                        'set_temp': round(target_temp, 2),
                        'us_active': 1 if us_active else 0,
                        'elapsed_minutes': round(elapsed_minutes, 2),
                        'elapsed_seconds': round(elapsed_seconds, 1),
                        'cycle_length_minutes': cycle_length_minutes_float,
                        'cycle_length_seconds': cycle_length_seconds,
                        'mode': mode,
                        'power': round(power, 2),
                        'tec_state': "On" if temp_ctrl.cooler.is_on else "Off",
                        'phase': "heat_shock" if elapsed_seconds >= heat_start_seconds else "basal"
                    }
                    
                    # Log snapshot with error handling
                    try:
                        if not experiment_logger.log_snapshot(cycle_number, snapshot_data):
                            print("[ERROR] Failed to save data to SD card")
                            sd_card_failed = True
                            
                            # CRITICAL: Check if SD is completely dead
                            if not experiment_logger.sd_write_ok:
                                print("[CRITICAL] SD card marked as unhealthy! Stopping experiment.")
                                raise RuntimeError("SD card write failures exceeded threshold - experiment halted for safety")
                                
                    except Exception as e:
                        print(f"[ERROR] SD card logging error: {e}")
                        sd_card_failed = True
                        
                        # If this is a critical SD failure, re-raise to stop the experiment
                        if "SD card write failures exceeded threshold" in str(e):
                            raise
                        
                        print("[WARNING] SD card logging disabled for this cycle. Experiment continues.")
                        # Continue running even if logging fails
                finally:
                    last_log_time = current_time

                    # --- RESUME US SYSTEM ---
                    # Restore US only if it should still be active
                    if was_us_active and us_active:
                        us_controller.activate(us_type, reset_timing=False)
                        us_currently_active = True
                    elif was_us_active and not us_active:
                        us_currently_active = False
            
            # Print periodic status update
            if current_time - last_status_time >= status_interval:
                print(f"[{elapsed_minutes:.1f}/{cycle_length_minutes_float:.1f} min] Temp: {current_temp:.1f}°C → {target_temp:.1f}°C | Mode: {mode} | Power: {power:.1f}% | Cycle: {cycle_number}")
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
        total_duration = time.time() - start_time
        cycle_stats.update({
            'end_time': time.time(),
            'duration_seconds': total_duration,
            'duration_minutes': total_duration / 60,
            'final_temp': last_valid_temp if last_valid_temp is not None else 0,
            'final_power': power,
            'final_mode': mode,
            'correlation_mode': correlation_mode
        })
        
        # Log cycle summary
        if experiment_logger:
            if not experiment_logger.log_cycle_summary(cycle_number, cycle_stats):
                print("[ERROR] Failed to save cycle summary")
                
                # CRITICAL: Check if SD is completely dead
                if not experiment_logger.sd_write_ok:
                    print("[CRITICAL] SD card marked as unhealthy! Stopping experiment.")
                    raise RuntimeError("SD card write failures exceeded threshold - experiment halted for safety")
            
    except Exception as e:
        print(f"[Cycle {cycle_number}] Error: {e}")
        if experiment_logger:
            error_data = {
                'error': str(e),
                'end_time': time.time(),
                'final_temp': last_valid_temp if last_valid_temp is not None else 0,
                'error_count': cycle_stats['error_count'],
                'correlation_mode': correlation_mode
            }
            experiment_logger.log_cycle_summary(cycle_number, error_data)
            experiment_logger.finalize_experiment(status='error', error=str(e))

    # Perform garbage collection
    gc.collect()
    
    # Print memory status after cycle
    print(f"[Memory] Free heap after cycle {cycle_number}: {gc.mem_free()} bytes")
    
    # Force a second collection to be thorough
    gc.collect()
