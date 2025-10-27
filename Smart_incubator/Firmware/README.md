# Smart Incubator Firmware Directory

## Status: Pending Implementation

This directory is where your Smart Incubator firmware files should be placed.

## Required Files (To Be Implemented)

Based on `MARKOVIAN_HES_FEATURE_OUTLINE.md`, you need to create:

### Core HES Modules:
- [ ] `markovian_hes_executor.py` - Main execution script
- [ ] `hes_config_loader.py` - JSON configuration parser
- [ ] `hes_transition_engine.py` - Markovian transition logic
- [ ] `hes_actuator_controller.py` - Coordinated actuator control
- [ ] `hes_logger.py` - HES-specific data logging

### Existing Smart Incubator Modules:
- [ ] `main.py` - Main program entry point
- [ ] `boot.py` - Boot configuration
- [ ] `temp_controller.py` - Temperature PID controller
- [ ] `led_control.py` - LED PWM control
- [ ] `us_control.py` - Ultrasound/vibration control
- [ ] `sd_logger.py` - SD card data logger
- [ ] `oled_display.py` - OLED display driver
- [ ] `tec.py` - TEC cooler control
- [ ] `heater.py` - PTC heater control
- [ ] `max31865.py` - Temperature sensor driver (if needed)

### Hardware Module Directory:
- [ ] `Hardware_modules/` - Additional hardware drivers

## Current Status

✅ **Test file created:** `test_deployment.py`
- This verifies the deployment system works
- You can deploy it now to test

❌ **Implementation files:** Not yet created
- You need to implement these based on your existing Smart Incubator code
- Or port them from your existing setup

## Next Steps

### Option 1: Test Deployment System Now
```bash
# Deploy test file to verify system works
python3 ../sync_firmware.py

# This will upload test_deployment.py to your ESP32
# Then you can test in REPL:
# >>> import test_deployment
# >>> test_deployment.test_function()
```

### Option 2: Copy Existing Firmware
```bash
# If you have existing Smart Incubator firmware:
cp /path/to/existing/firmware/*.py ./

# Then deploy:
python3 ../sync_firmware.py
```

### Option 3: Implement From Scratch
Follow the implementation plan in:
- `../Docs/MARKOVIAN_HES_FEATURE_OUTLINE.md`
- Start with Phase 1 (Core Infrastructure)
- Implement modules one by one
- Test each module before moving to next

## Implementation Order (Recommended)

1. **Week 1: Core Infrastructure**
   - `hes_config_loader.py` - Start here (parses JSON configs)
   - `hes_transition_engine.py` - Probability calculations
   - Test with simple configs

2. **Week 2: Actuator Control**
   - `hes_actuator_controller.py` - Unified actuator interface
   - `hes_logger.py` - Data logging
   - Integrate with existing hardware modules

3. **Week 3: Main Executor**
   - `markovian_hes_executor.py` - Brings everything together
   - Hardware initialization
   - Main experiment loop

4. **Week 4: Testing**
   - Create test configs
   - Hardware validation
   - Run test experiments

## Testing Strategy

After implementing each module:

1. **Local testing (on computer):**
   ```python
   python3 -m pytest tests/test_config_loader.py
   ```

2. **Deploy to ESP32:**
   ```bash
   python3 ../sync_firmware.py  # Only uploads changed file
   ```

3. **Test on device:**
   ```bash
   mpremote connect PORT repl
   >>> import hes_config_loader
   >>> # Test your module
   ```

## Need Help?

- **Architecture:** See `MARKOVIAN_HES_FEATURE_OUTLINE.md`
- **Deployment:** See `DEPLOYMENT_GUIDE.md`
- **Quick start:** See `QUICK_START.md`

## Current Test File

`test_deployment.py` is a minimal example showing:
- Module structure
- Function definitions
- How files will be deployed

You can deploy it now to verify your ESP32 connection works!
