# Experiment Failure Analysis - Cycle 8+ Crash

## Date: October 27, 2025

## Problem Summary

An experiment that was expected to run continuously got stuck after cycle 8, despite showing cycle 48 on the display. Analysis of the SD card data revealed critical issues with silent failures in the data logging system.

## Root Causes Identified

### 1. **Silent SD Card Write Failures**
- **Issue**: The `log_snapshot()` and `log_cycle_summary()` functions returned `False` when writes failed, but the main experiment loop **did not check these return values**
- **Impact**: The system continued running for 40+ cycles without saving any data after cycle 8
- **Evidence**: 
  - Only 8,489 JSON files found (up to cycle 8, timestamp 9879)
  - Manifest shows cycle 32+ data
  - Display showed cycle 48
  - Final error: "Too many invalid temperature readings"

### 2. **Memory Buildup in Manifest**
- **Issue**: The manifest file list was limited to 100 entries, but snapshots were logged every 10 seconds
- **Impact**: In a ~300 minute cycle, that's ~1,800 snapshots. The manifest list kept growing in RAM even though it wasn't being written to SD
- **Memory leak**: Each cycle added ~1,800 entries to `self.manifest['files']` list in memory
- **Old code**:
```python
if len(self.manifest['files']) > 100:
    self.manifest['files'] = self.manifest['files'][-100:]
```
This only trimmed when updating manifest, which couldn't happen if writes were failing!

### 3. **Poor Experiment ID Generation**
- **Issue**: Experiment ID was generated as `{timestamp/86400}_{correlation}` which often resulted in `0_0`
- **Impact**: Multiple experiments could overwrite each other, difficult to identify experiments
- **Evidence**: The failed experiment was in folder `0_0`

### 4. **Cascading Failure**
1. SD card write failures started (likely bad SD card)
2. System silently continued without saving data
3. Memory filled up with unsaved manifest entries
4. Temperature sensor SPI bus became unreliable (memory/resource contention)
5. System eventually crashed with "Too many invalid temperature readings"

## Fixes Implemented

### 1. **SD Write Failure Detection & Halt**
Added tracking of consecutive write failures:
```python
self.consecutive_write_failures = 0
self.max_write_failures = 10
self.sd_write_ok = True  # Health flag
```

When failures exceed threshold, the experiment **halts immediately** instead of continuing silently:
```python
if self.consecutive_write_failures >= self.max_write_failures:
    print(f"[CRITICAL] SD card write failures exceeded threshold!")
    self.sd_write_ok = False
```

### 2. **Temperature Sensor Error Handling Improvements**
**Problem**: Temperature errors only stopped the current cycle, then the next cycle would start and fail again.

**Fixes**:
- Changed from `return` to `raise RuntimeError()` when sensor fails - **stops entire experiment**
- Increased error threshold from 5 to 10 failed reads (more tolerant of transient errors)
- Added **gradual error recovery**: errors decrement after successful reads instead of immediate reset
- Better error messages distinguish between transient vs. critical failures
- Propagates sensor fault information from MAX31865 chip

```python
if consecutive_invalid_readings >= max_invalid_readings:
    print("[CRITICAL] Sensor fault detected - stopping experiment for safety")
    raise RuntimeError(f"Temperature sensor fault - {fault}")  # Stops everything
```

**Result**: System now distinguishes between:
- **Transient errors** (occasional bad reads) → uses last valid temp and recovers
- **Persistent errors** (sensor failure) → halts experiment immediately for safety

### 3. **Manifest Memory Management**
- Reduced manifest file list from 100 to **50 entries** (more conservative)
- Added warning when trimming occurs
- Made `_update_manifest()` return success/failure status

### 4. **Better Experiment ID Generation**
New format uses RTC if available: `YYYYMMDD_HHMMSS_corr`
```python
exp_id = f"{dt[0]:04d}{dt[1]:02d}{dt[2]:02d}_{dt[4]:02d}{dt[5]:02d}{dt[6]:02d}_{int(correlation)}"
```
Falls back to timestamp if RTC not available, but much more readable.

### 5. **Main Loop SD Health Checks**
Added pre-cycle health checks:
```python
# CRITICAL: Check SD health before starting cycle
if experiment_logger and not experiment_logger.sd_write_ok:
    print(f"[CRITICAL] SD card is unhealthy - cannot start cycle")
    experiment_logger.finalize_experiment(status='error', error='SD card write failures')
    break
```

### 6. **Memory Monitoring**
Added periodic memory checks:
```python
gc.collect()
free_mem = gc.mem_free()
print(f"[Memory] Free heap: {free_mem} bytes")
if free_mem < 10000:  # Less than 10KB free
    print(f"[WARNING] Low memory detected!")
```

### 7. **Critical Error Propagation**
SD failures now raise exceptions that stop the experiment:
```python
if not experiment_logger.sd_write_ok:
    raise RuntimeError("SD card write failures exceeded threshold - experiment halted for safety")
```

## Recommendations

### Immediate Actions
1. ✅ **Use better quality SD cards** (user mentioned this)
   - Class 10 or better
   - High endurance cards designed for continuous writing
   - Smaller capacity (8-16GB) often more reliable than large cards

2. **Format SD cards properly**
   - Use FAT32 filesystem
   - 4KB allocation unit size
   - Format on the device when possible

### Future Improvements

1. **Add SD card health monitoring**
   - Track write speeds
   - Monitor retry rates
   - Warning system before complete failure

2. **Implement data buffering**
   - Keep last N snapshots in RAM
   - Try to flush when SD recovers
   - Graceful degradation

3. **Add watchdog timer**
   - Reset system if main loop hangs
   - Prevent silent failures

4. **Implement experiment resume capability**
   - Save cycle state periodically
   - Allow experiments to continue after reboot

## Testing Recommendations

Before next experiment:
1. **SD Card Test**: Run a write-intensive test for several hours
2. **Memory Test**: Monitor memory usage over multiple cycles
3. **Failure Recovery Test**: Simulate SD card removal mid-cycle
4. **Long Duration Test**: Run 10+ cycles to verify fixes

## Files Modified

1. `sd_logger.py` - Added failure tracking, better ID generation, memory management
2. `run_experiment_cycle.py` - Added SD health checks, critical error propagation, **temperature error raises exceptions**
3. `main.py` - Added pre-cycle health checks, memory monitoring
4. `temp_controller.py` - **Improved error recovery, increased tolerance, better error messages**

## Summary

The experiment appeared to run for 48 cycles but actually stopped saving data after cycle 8 due to silent SD card failures. The system kept running in memory until resources were exhausted, causing temperature sensor failures. The fixes ensure the experiment **halts immediately** when SD card issues are detected, preventing data loss and unsafe operation.
