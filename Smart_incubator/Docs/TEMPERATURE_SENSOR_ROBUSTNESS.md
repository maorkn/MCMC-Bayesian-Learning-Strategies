# Temperature Sensor Robustness Improvements

## Overview

The temperature sensor errors in your failed experiment were likely a **symptom** of the SD card/memory issues (resource exhaustion affecting SPI bus). However, we've made the temperature error handling much more robust to handle both transient and persistent sensor failures properly.

## Problems with Original Code

### 1. **Silent Cycle Failures**
```python
# OLD CODE - in run_experiment_cycle.py
if consecutive_invalid_readings >= max_invalid_readings:
    print("[ERROR] Stopping experiment cycle")
    return  # ❌ Only stops this cycle, next cycle starts!
```
**Problem**: When temp sensor failed, the cycle would `return` early, but `main.py` would just start the next cycle, which would fail again. This created a loop of failing cycles.

### 2. **Aggressive Error Counter Reset**
```python
# OLD CODE - in temp_controller.py
if current_temp is not None:
    self.temp_read_errors = 0  # ❌ Immediate reset
```
**Problem**: A single successful read would reset the error counter to zero, even if the sensor was having intermittent problems. This masked degrading sensor health.

### 3. **Low Error Threshold**
```python
self.max_temp_errors = 5  # ❌ Only 5 failed reads before stopping
```
**Problem**: Too sensitive to transient errors (like brief SPI bus contention). Would stop experiments unnecessarily.

## Improvements Implemented

### 1. **Critical Error Propagation** ✅
```python
# NEW CODE - in run_experiment_cycle.py
if consecutive_invalid_readings >= max_invalid_readings:
    print("[CRITICAL] Sensor fault detected - stopping experiment for safety")
    raise RuntimeError(f"Temperature sensor fault - {fault}")  # ✅ Stops entire experiment!
```

**Benefits**:
- Stops the entire experiment, not just one cycle
- Provides detailed fault information from MAX31865 chip
- Clear distinction: `[CRITICAL]` vs `[ERROR]` vs `[WARNING]`

### 2. **Gradual Error Recovery** ✅
```python
# NEW CODE - in temp_controller.py
if self.temp_read_errors > 0:
    self.temp_read_errors = max(0, self.temp_read_errors - 1)  # ✅ Gradual recovery
    if self.temp_read_errors == 0:
        print("[INFO] Temperature sensor errors cleared")
```

**Benefits**:
- Errors decrement slowly after successful reads
- Catches sensor degradation (e.g., errors increasing over time)
- Provides early warning before complete failure

**Example**:
- Cycle starts: `errors = 0`
- 3 failures: `errors = 3`
- 1 success: `errors = 2` (not reset to 0)
- 2 more successes: `errors = 0` (cleared)
- If failures > successes, errors keep rising → eventual halt

### 3. **Increased Tolerance** ✅
```python
self.max_temp_errors = 10  # ✅ Increased from 5 to 10
```

**Benefits**:
- More tolerant of brief SPI bus contention
- Reduces false positives from transient issues
- Combined with gradual recovery, catches real problems

### 4. **Enhanced Error Reporting** ✅
```python
print(f"[ERROR] Failed to get valid temperature (errors: {self.temp_read_errors}/{self.max_temp_errors})")
print(f"[MAX31865] Fault detected: {fault}")  # Specific fault code
print("[CRITICAL] This may indicate a sensor hardware failure")
```

**Fault codes from MAX31865**:
- `0x01`: RTD High Threshold
- `0x02`: RTD Low Threshold  
- `0x04`: REFIN- > 0.85 x Bias
- `0x08`: REFIN- < 0.85 x Bias (FORCE- open)
- `0x10`: RTDIN- < 0.85 x Bias (FORCE- open)
- `0x20`: Overvoltage/undervoltage fault
- `0x40`: Reserved
- `0x80`: Reserved

## Error Handling Flow

```
┌─────────────────────────────────────────┐
│  Read Temperature (3 attempts)          │
└───────────┬─────────────────────────────┘
            │
            ├─ Success ──────────────────────────┐
            │                                    │
            │  - Use temperature                 │
            │  - Decrement error counter by 1    │
            │  - Continue experiment             │
            │                                    │
            └─ Failure ─────────────────────────┐
                                                 │
                - Increment error counter        │
                - Check if < max_temp_errors     │
                                                 │
                ├─ Yes: Use last valid temp ─────┤
                │       Continue with warning    │
                │                                │
                └─ No: CRITICAL FAILURE ─────────┤
                      - Finalize experiment      │
                      - Raise RuntimeError       │
                      - Stop entire system       │
                                                 ▼
                                        Experiment HALTED
```

## Transient vs. Persistent Failures

### Transient (System Recovers) ✅
**Example**: Brief SPI bus contention during US activation
```
Read 1: ✓ 23.1°C
Read 2: ✗ Failed (errors=1)
Read 3: ✓ 23.2°C (errors=0 after gradual recovery)
Read 4: ✓ 23.1°C
→ Experiment continues normally
```

### Degrading (Early Warning) ✅
**Example**: Loose connection, intermittent contact
```
Cycle 1: 2 failures, 18 successes (errors decrease to 0)
Cycle 2: 5 failures, 15 successes (errors decrease to 0)
Cycle 3: 8 failures, 12 successes (errors rising to 2)
Cycle 4: 11 failures, 9 successes (errors rising to 4)
→ Warning messages increase
→ Eventually halts before damage
```

### Persistent (Immediate Halt) ✅
**Example**: Sensor disconnected or hardware failure
```
Read 1: ✗ Failed (errors=1)
Read 2: ✗ Failed (errors=2)
...
Read 10: ✗ Failed (errors=10)
→ CRITICAL: Temperature sensor fault
→ Experiment HALTED immediately
→ Safety ensured
```

## Safety Features

### 1. **Fallback to Last Valid Temperature**
If sensor fails but we have a recent good reading:
- Uses last valid temperature for control
- Prints warning message
- Allows brief recovery time
- Prevents immediate shutdown from single glitch

### 2. **Multi-Level Error Detection**
1. **SPI Communication**: 3 retry attempts with delays
2. **Range Validation**: Rejects readings outside -50°C to 100°C
3. **Jump Detection**: Flags >10°C changes as suspicious
4. **Fault Register**: Reads MAX31865 fault codes
5. **Consecutive Counting**: Tracks sustained failures

### 3. **Emergency Temperature Failsafe**
Independent of sensor errors, the temperature failsafe system:
- Monitors for stuck sensor (no change for 2+ minutes)
- Checks for over-temperature (>45°C)
- Can trigger emergency shutdown
- Prevents heater runaway

## Testing Recommendations

### Test 1: Transient Error Recovery
```python
# Simulate occasional SPI bus contention
# Expected: System recovers, experiment continues
```

### Test 2: Sensor Disconnection
```python
# Physically disconnect RTD sensor
# Expected: Errors accumulate to 10, experiment halts with fault code
```

### Test 3: Long Duration Stability
```python
# Run 10+ cycles
# Expected: Error counter stays at 0 or near 0
# Any trend upward indicates degrading sensor
```

## Summary of Improvements

| Aspect | Before | After | Benefit |
|--------|--------|-------|---------|
| **Error threshold** | 5 failures | 10 failures | More tolerant of transients |
| **Error recovery** | Immediate reset | Gradual decrement | Catches degradation |
| **Failure action** | Return (silent) | Raise exception | Stops entire experiment |
| **Error messages** | Generic | Specific fault codes | Better debugging |
| **Failure detection** | Cycle-level only | Multi-level cascade | More robust |

## Result

The system is now **robust to temperature sensor errors**:
- ✅ Tolerates transient failures (brief SPI issues)
- ✅ Detects degrading sensor health early
- ✅ Halts safely on persistent failures
- ✅ Provides detailed error information for debugging
- ✅ Prevents dangerous operation with bad sensor data

Combined with the SD card fixes, the experiment will now **fail safely and loudly** rather than running blind with corrupted data.
