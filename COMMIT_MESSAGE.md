# Git Commit Message

## Short Version (for commit title):
```
Fix: Add critical SD card and temperature sensor failure handling
```

## Detailed Version (for commit body):
```
Fix: Add critical SD card and temperature sensor failure handling

Problem Analysis:
- Experiment failed after cycle 8 but displayed cycle 48 on screen
- SD card silently stopped writing data without halting experiment
- Memory buildup from unsaved manifest entries (1800+ per cycle)
- Temperature sensor eventually failed due to resource exhaustion
- Poor experiment ID generation (always "0_0")

Critical Fixes:
1. SD Card Failure Detection
   - Track consecutive write failures (max 10)
   - Mark SD as unhealthy and halt experiment when threshold exceeded
   - Check SD health before each cycle starts
   - Proper error propagation to stop entire experiment

2. Temperature Sensor Robustness
   - Raise exceptions on critical sensor failures (stops experiment)
   - Increased error threshold from 5 to 10 (more tolerant)
   - Gradual error recovery (decrement vs immediate reset)
   - Better fault detection and reporting with MAX31865 codes

3. Memory Management
   - Reduced manifest file list from 100 to 50 entries
   - Added pre-cycle memory monitoring
   - Warning when free memory < 10KB

4. Experiment ID Generation
   - Changed from timestamp/86400 to YYYYMMDD_HHMMSS_corr format
   - Uses RTC when available, falls back to Unix timestamp
   - More readable and prevents ID collisions

5. Error Handling Improvements
   - All critical failures now raise exceptions
   - Clear error severity levels: [INFO], [WARNING], [ERROR], [CRITICAL]
   - Proper experiment finalization on failures
   - Detailed error messages with failure counts

Files Modified:
- sd_logger.py: Failure tracking, better ID generation, memory limits
- run_experiment_cycle.py: SD health checks, temperature error propagation
- main.py: Pre-cycle health checks, memory monitoring
- temp_controller.py: Gradual error recovery, increased tolerance

Documentation Added:
- EXPERIMENT_FAILURE_ANALYSIS.md: Root cause analysis and fixes
- TEMPERATURE_SENSOR_ROBUSTNESS.md: Detailed error handling guide

Result:
System now fails safely and loudly rather than running blind with data loss.
Both SD card and temperature sensor failures halt experiments immediately.
```

## One-liner for quick commits:
```
Fix critical silent failures in SD logging and temperature sensing that caused experiment to run 40+ cycles without saving data
```
