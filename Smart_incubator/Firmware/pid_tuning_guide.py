# pid_tuning_guide.py - PID Tuning Guide for Smart Incubator
"""
PID Tuning Guide for Smart Incubator Temperature Control

PWM Frequency Change Impact:
- Original: 1kHz PWM frequency
- New: 500Hz PWM frequency  
- Impact: Slower system response, requires PID retuning

Current PID Parameters (adjusted for 500Hz):
- kp = 5.0 (reduced from 6.0)
- ki = 0.015 (reduced from 0.02) 
- kd = 1.0 (reduced from 1.5)
"""

import time
from temp_controller import TempController
from max31865 import init_max31865

# Test configurations
TEST_DURATION = 300  # 5 minutes
TARGET_TEMP = 30.0   # Test target temperature
SAMPLE_INTERVAL = 5  # Sample every 5 seconds

def test_pid_step_response(kp, ki, kd, target_temp=TARGET_TEMP):
    """Test PID response to step change in temperature."""
    print(f"\n=== Testing PID Parameters ===")
    print(f"kp={kp}, ki={ki}, kd={kd}")
    print(f"Target temperature: {target_temp}°C")
    print(f"Test duration: {TEST_DURATION} seconds")
    
    # Initialize temperature controller with test parameters
    temp_ctrl = TempController(33, 27, kp=kp, ki=ki, kd=kd)  # heater_pin=33, cooler_pin=27
    
    results = []
    start_time = time.time()
    
    try:
        while time.time() - start_time < TEST_DURATION:
            current_time = time.time() - start_time
            
            # Control temperature
            current_temp, power, mode = temp_ctrl.control_temp(target_temp)
            
            if current_temp is not None:
                error = target_temp - current_temp
                results.append({
                    'time': current_time,
                    'temp': current_temp,
                    'error': error,
                    'power': power,
                    'mode': mode
                })
                
                print(f"t={current_time:6.1f}s | Temp={current_temp:5.1f}°C | Error={error:+5.1f}°C | Power={power:+6.1f}% | Mode={mode}")
            
            time.sleep(SAMPLE_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user.")
    finally:
        # Turn off all actuators
        temp_ctrl.heater.turn_off()
        temp_ctrl.cooler.turn_off()
    
    return results

def analyze_pid_performance(results):
    """Analyze PID performance metrics."""
    if not results:
        print("No data to analyze.")
        return
    
    # Calculate performance metrics
    errors = [abs(r['error']) for r in results]
    avg_error = sum(errors) / len(errors)
    max_error = max(errors)
    
    # Settling time (time to reach within ±1°C of target)
    settling_time = None
    for i, result in enumerate(results):
        if abs(result['error']) <= 1.0:
            settling_time = result['time']
            break
    
    # Overshoot (maximum positive error)
    overshoot = max([r['error'] for r in results]) if results else 0
    
    # Steady-state error (average error in last 25% of test)
    steady_start = int(len(results) * 0.75)
    steady_errors = [abs(r['error']) for r in results[steady_start:]]
    steady_state_error = sum(steady_errors) / len(steady_errors) if steady_errors else float('inf')
    
    print(f"\n=== Performance Analysis ===")
    print(f"Average error: {avg_error:.2f}°C")
    print(f"Maximum error: {max_error:.2f}°C")
    print(f"Settling time: {settling_time:.1f}s" if settling_time else "Did not settle within test duration")
    print(f"Overshoot: {overshoot:.2f}°C")
    print(f"Steady-state error: {steady_state_error:.2f}°C")
    
    # Performance recommendations
    print(f"\n=== Tuning Recommendations ===")
    if steady_state_error > 1.0:
        print("• Increase ki (integral gain) to reduce steady-state error")
    if settling_time is None or settling_time > 120:
        print("• Increase kp (proportional gain) for faster response")
    if overshoot > 3.0:
        print("• Decrease kp or increase kd to reduce overshoot")
    if max_error > 5.0:
        print("• System may be unstable - reduce all gains")
    
    return {
        'avg_error': avg_error,
        'max_error': max_error,
        'settling_time': settling_time,
        'overshoot': overshoot,
        'steady_state_error': steady_state_error
    }

def run_pid_tuning_sequence():
    """Run a sequence of PID tests with different parameters."""
    print("PID Tuning Sequence for Smart Incubator")
    print("======================================")
    print("This will test different PID parameter combinations.")
    print("Each test takes 5 minutes. Press Ctrl+C to skip a test.")
    
    # Initialize temperature sensor
    if not init_max31865():
        print("ERROR: Failed to initialize temperature sensor!")
        return
    
    # Test parameter sets
    test_cases = [
        {"name": "Current (Conservative)", "kp": 5.0, "ki": 0.015, "kd": 1.0},
        {"name": "More Aggressive", "kp": 6.0, "ki": 0.02, "kd": 1.2},
        {"name": "Less Aggressive", "kp": 4.0, "ki": 0.01, "kd": 0.8},
        {"name": "Fast Response", "kp": 7.0, "ki": 0.025, "kd": 1.5},
    ]
    
    all_results = {}
    
    for i, test_case in enumerate(test_cases):
        print(f"\n{'='*60}")
        print(f"Test {i+1}/{len(test_cases)}: {test_case['name']}")
        print(f"{'='*60}")
        
        try:
            results = test_pid_step_response(
                kp=test_case['kp'],
                ki=test_case['ki'], 
                kd=test_case['kd']
            )
            
            metrics = analyze_pid_performance(results)
            all_results[test_case['name']] = {
                'params': test_case,
                'metrics': metrics,
                'data': results
            }
            
            # Cool down between tests
            if i < len(test_cases) - 1:
                print(f"\nCooling down for 30 seconds before next test...")
                time.sleep(30)
                
        except KeyboardInterrupt:
            print(f"\nSkipping test: {test_case['name']}")
            continue
    
    # Final comparison
    print(f"\n{'='*60}")
    print("FINAL COMPARISON")
    print(f"{'='*60}")
    
    for name, result in all_results.items():
        params = result['params']
        metrics = result['metrics']
        print(f"\n{name}:")
        print(f"  Parameters: kp={params['kp']}, ki={params['ki']}, kd={params['kd']}")
        if metrics:
            print(f"  Avg Error: {metrics['avg_error']:.2f}°C")
            print(f"  Settling Time: {metrics['settling_time']:.1f}s" if metrics['settling_time'] else "  Did not settle")
            print(f"  Steady State Error: {metrics['steady_state_error']:.2f}°C")
    
    print(f"\nRecommendation: Choose the parameter set with:")
    print(f"• Lowest steady-state error (< 1.0°C)")
    print(f"• Reasonable settling time (< 120s)")
    print(f"• Minimal overshoot (< 3.0°C)")

def quick_stability_test():
    """Quick test to verify current PID parameters work reasonably."""
    print("Quick PID Stability Test")
    print("=======================")
    print("Testing current PID parameters for 2 minutes...")
    
    if not init_max31865():
        print("ERROR: Failed to initialize temperature sensor!")
        return
    
    # Use current parameters
    temp_ctrl = TempController(33, 27, kp=5.0, ki=0.015, kd=1.0)
    
    start_time = time.time()
    target = 28.0  # Mild target temperature
    
    try:
        while time.time() - start_time < 120:  # 2 minutes
            current_temp, power, mode = temp_ctrl.control_temp(target)
            if current_temp is not None:
                error = target - current_temp
                print(f"Temp={current_temp:5.1f}°C | Error={error:+5.1f}°C | Power={power:+6.1f}% | {mode}")
            time.sleep(10)  # Sample every 10 seconds
            
    except KeyboardInterrupt:
        print("\nTest interrupted.")
    finally:
        temp_ctrl.heater.turn_off()
        temp_ctrl.cooler.turn_off()
        print("Quick test complete.")

if __name__ == "__main__":
    print("PID Tuning Options:")
    print("1. Quick stability test (2 minutes)")
    print("2. Full tuning sequence (4 x 5 minutes)")
    print("3. Single parameter test")
    
    # For MicroPython, just run quick test
    quick_stability_test() 