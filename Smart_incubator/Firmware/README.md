# Smart Incubator Firmware Directory

## Status: ✅ Fully Implemented

This directory contains the complete firmware for the Smart Incubator Control System v2.0.

## WiFi Configuration Mode (v2.0)

The firmware now includes a **phone-based WiFi setup** mode:

1. **Power on ESP32** → Creates WiFi hotspot `Inc-XXXX`
2. **Connect phone** → Password: `incubator123`
3. **Open browser** → Go to `http://192.168.4.1`
4. **Configure experiment** → Set time, name, correlation, parameters
5. **Press START** → Experiment runs autonomously

## Core Modules

### Main System:
- [x] `main.py` - Main program with WiFi setup and experiment loop
- [x] `boot.py` - Boot configuration and GPIO safety
- [x] `run_experiment_cycle.py` - Experiment cycle execution logic

### WiFi & Configuration:
- [x] `wifi_setup.py` - WiFi Access Point creation (unique SSIDs)
- [x] `experiment_setup_server.py` - Web-based experiment configuration

### Temperature Control:
- [x] `temp_controller.py` - PID temperature controller
- [x] `max31865.py` - PT100 RTD temperature sensor driver
- [x] `heater.py` - PTC heater control
- [x] `tec.py` - TEC cooler control

### Stimuli Control:
- [x] `us_control.py` - Unified stimulus (US) controller
- [x] `led_control.py` - LED PWM control
- [x] `vibration_control.py` - Vibration motor control

### Data & Display:
- [x] `sd_logger.py` - SD card data logging with integrity checks
- [x] `oled_display.py` - OLED status display
- [x] `sdcard.py` - SD card driver
- [x] `ssd1306.py` - OLED display driver

### Safety & Diagnostics:
- [x] `sensor_recovery.py` - Automated sensor recovery
- [x] `temperature_failsafe.py` - Temperature safety protection
- [x] `sensor_diagnostic.py` - Sensor health monitoring
- [x] `max31865_diagnostic.py` - MAX31865 diagnostics

### Utilities:
- [x] `utils.py` - Common utility functions
- [x] `pid_tuning_guide.py` - PID tuning assistance
- [x] `test_deployment.py` - Hardware deployment verification

## Correlation Values

The correlation parameter controls the relationship between the Unconditional Stimulus (US) and heat shock:

| Value | Meaning | Scientific Purpose |
|-------|---------|-------------------|
| **+1.0** | US always precedes heat shock | Test predictive learning (paired condition) |
| **0.0** | US at random times | Control for temporal association |
| **-1.0** | No US delivered | Heat shock only control |

Intermediate values (e.g., 0.5, -0.5) interpolate between behaviors for graded experiments.

## Deployment

Deploy all firmware files using:

```bash
# Using VS Code (recommended)
Cmd+Shift+B  # or Ctrl+Shift+B on Windows/Linux

# Or command line
python Smart_incubator/sync_firmware.py --yes
```

## Need Help?

- **Architecture:** See `../Docs/MARKOVIAN_HES_FEATURE_OUTLINE.md`
- **Deployment:** See `../DEPLOYMENT_GUIDE.md`
- **Quick start:** See `../QUICK_START.md`