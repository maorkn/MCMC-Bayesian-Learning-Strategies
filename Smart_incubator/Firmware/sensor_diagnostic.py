# sensor_diagnostic.py - Temperature Sensor Diagnostic Tool
import time
from max31865 import init_max31865, read_temperature, check_fault, read_register, RTD_MSB_REG, RTD_LSB_REG, CONFIG_REG
import gc

def run_comprehensive_sensor_test(duration_minutes=10, log_interval=5):
    """Run comprehensive temperature sensor diagnostics."""
    print("\n=== TEMPERATURE SENSOR DIAGNOSTIC TEST ===")
    print(f"Duration: {duration_minutes} minutes")
    print(f"Logging interval: {log_interval} seconds")
    print("=" * 50)
    
    # Initialize sensor
    if not init_max31865():
        print("[ERROR] Sensor initialization failed!")
        return False
    
    print("[OK] Sensor initialized successfully")
    
    # Test variables
    start_time = time.time()
    end_time = start_time + (duration_minutes * 60)
    readings = []
    consecutive_same_readings = 0
    last_reading = None
    consecutive_none_readings = 0
    fault_count = 0
    
    print("\nStarting continuous monitoring...")
    print("Timestamp\tTemp(°C)\tRaw_MSB\tRaw_LSB\tFault\tConsec_Same\tConsec_None")
    print("-" * 80)
    
    while time.time() < end_time:
        current_time = time.time()
        elapsed = current_time - start_time
        
        # Read raw registers for debugging
        try:
            msb = read_register(RTD_MSB_REG)
            lsb = read_register(RTD_LSB_REG)
            config = read_register(CONFIG_REG)
        except Exception as e:
            print(f"[ERROR] Register read failed: {e}")
            msb = lsb = config = -1
        
        # Check for faults
        fault = check_fault()
        if fault:
            fault_count += 1
        
        # Read temperature
        temp = read_temperature()
        
        # Track consecutive identical readings (potential stuck sensor)
        if temp is not None:
            consecutive_none_readings = 0
            if last_reading is not None and abs(temp - last_reading) < 0.01:
                consecutive_same_readings += 1
            else:
                consecutive_same_readings = 0
            last_reading = temp
        else:
            consecutive_none_readings += 1
            
        # Log data
        readings.append({
            'timestamp': current_time,
            'elapsed': elapsed,
            'temp': temp,
            'msb': msb,
            'lsb': lsb,
            'config': config,
            'fault': fault,
            'consecutive_same': consecutive_same_readings,
            'consecutive_none': consecutive_none_readings
        })
        
        # Print current reading
        print(f"{elapsed:6.1f}s\t{temp if temp else 'None':>6s}\t{msb:>7}\t{lsb:>7}\t{fault if fault else 'None':>10s}\t{consecutive_same_readings:>10}\t{consecutive_none_readings:>11}")
        
        # Alert for suspicious patterns
        if consecutive_same_readings >= 5:
            print(f"[WARNING] Temperature stuck at {temp}°C for {consecutive_same_readings} consecutive readings!")
        
        if consecutive_none_readings >= 3:
            print(f"[WARNING] {consecutive_none_readings} consecutive None readings - sensor failure!")
        
        # Check for register corruption
        if config != 0xC3 and config != 0xC1:
            print(f"[WARNING] Configuration register corrupted: 0x{config:02X}")
        
        time.sleep(log_interval)
        
        # Memory cleanup
        if len(readings) % 20 == 0:
            gc.collect()
    
    # Analysis
    print("\n" + "=" * 50)
    print("DIAGNOSTIC RESULTS")
    print("=" * 50)
    
    valid_readings = [r['temp'] for r in readings if r['temp'] is not None]
    none_readings = [r for r in readings if r['temp'] is None]
    
    print(f"Total readings: {len(readings)}")
    print(f"Valid readings: {len(valid_readings)} ({len(valid_readings)/len(readings)*100:.1f}%)")
    print(f"None readings: {len(none_readings)} ({len(none_readings)/len(readings)*100:.1f}%)")
    print(f"Fault events: {fault_count}")
    
    if valid_readings:
        print(f"Temperature range: {min(valid_readings):.2f}°C to {max(valid_readings):.2f}°C")
        print(f"Temperature std dev: {calculate_std_dev(valid_readings):.3f}°C")
    
    # Check for stuck readings
    stuck_sequences = []
    current_stuck_value = None
    current_stuck_count = 0
    
    for reading in readings:
        if reading['consecutive_same'] >= 5:
            if current_stuck_value != reading['temp']:
                if current_stuck_count > 0:
                    stuck_sequences.append((current_stuck_value, current_stuck_count))
                current_stuck_value = reading['temp']
                current_stuck_count = 1
            else:
                current_stuck_count += 1
    
    if current_stuck_count > 0:
        stuck_sequences.append((current_stuck_value, current_stuck_count))
    
    if stuck_sequences:
        print("\nSTUCK READING SEQUENCES DETECTED:")
        for value, count in stuck_sequences:
            print(f"  Temperature stuck at {value}°C for {count} consecutive readings")
            print(f"  [CRITICAL] This is the bug pattern that caused overheating!")
    
    # Recommendations
    print("\nRECOMMENDATIONS:")
    if len(none_readings) > len(readings) * 0.1:
        print("- High rate of None readings suggests sensor or SPI communication issues")
        print("- Check PT100 RTD connections and MAX31865 chip")
        print("- Verify SPI wiring and reduce interference")
    
    if stuck_sequences:
        print("- CRITICAL: Stuck temperature readings detected")
        print("- This is likely the root cause of your overheating issue")
        print("- Implement failsafe mechanism immediately")
    
    if fault_count > 0:
        print(f"- {fault_count} fault events detected - check sensor connections")
    
    return len(stuck_sequences) == 0 and len(none_readings) < len(readings) * 0.05

def calculate_std_dev(values):
    """Calculate standard deviation."""
    if len(values) < 2:
        return 0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance ** 0.5

def test_spi_reliability():
    """Test SPI communication reliability."""
    print("\n=== SPI RELIABILITY TEST ===")
    
    # Test rapid register reads
    success_count = 0
    total_attempts = 100
    
    for i in range(total_attempts):
        try:
            config = read_register(CONFIG_REG)
            if config in [0xC3, 0xC1]:
                success_count += 1
            else:
                print(f"[ERROR] Attempt {i+1}: Invalid config 0x{config:02X}")
        except Exception as e:
            print(f"[ERROR] Attempt {i+1}: {e}")
        
        if i % 10 == 0:
            print(f"Progress: {i+1}/{total_attempts}")
        
        time.sleep_ms(10)
    
    success_rate = success_count / total_attempts * 100
    print(f"\nSPI Success Rate: {success_rate:.1f}% ({success_count}/{total_attempts})")
    
    if success_rate < 95:
        print("[WARNING] Poor SPI reliability - check connections and interference")
    else:
        print("[OK] SPI communication appears reliable")
    
    return success_rate >= 95

if __name__ == "__main__":
    print("Temperature Sensor Diagnostic Tool")
    print("This will help identify the cause of stuck temperature readings")
    
    # Quick SPI test
    spi_ok = test_spi_reliability()
    
    # Extended sensor test
    sensor_ok = run_comprehensive_sensor_test(duration_minutes=5, log_interval=2)
    
    print(f"\n{'='*50}")
    print("FINAL DIAGNOSIS")
    print(f"{'='*50}")
    print(f"SPI Communication: {'OK' if spi_ok else 'FAILED'}")
    print(f"Sensor Stability: {'OK' if sensor_ok else 'FAILED'}")
    
    if not spi_ok or not sensor_ok:
        print("\n[CRITICAL] Sensor issues detected that could cause overheating!")
        print("Recommend implementing failsafe mechanism immediately.")
