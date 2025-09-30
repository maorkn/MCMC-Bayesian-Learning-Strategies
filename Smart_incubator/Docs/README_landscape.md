# Complex Environmental Landscape for ESP32 Incubator

This directory contains scripts to generate, execute, and analyze complex environmental landscapes for the ESP32-based smart incubator.

## Overview

The system creates sophisticated temporal associations between temperature, light, and vibration to demonstrate advanced environmental control capabilities for biological research.

## Scripts and Files

### 1. Landscape Generation
- **`generate_complex_landscape.py`** - Creates 72-hour simulated landscape
- **`landscape.csv`** - Generated target data (4,320 1-minute intervals)
- **`landscape.png`** - Visualization of the simulated landscape

### 2. Analysis Tools
- **`analyze_landscape.py`** - Analyzes generated landscape statistics
- **`landscape_documentation.md`** - Detailed documentation for papers

### 3. Hardware Execution
- **`landscape_executor.py`** - ESP32 script to execute landscape on hardware
- **`landscape_comparison.py`** - Compare hardware vs simulation performance

## Current Landscape Parameters (25-30°C Range)

### Temperature Profile
- **Base**: 27.5°C ± 1.25°C circadian oscillation
- **Range**: 25-30°C (suitable for room temperature testing)
- **Heat Pulses**: 4 discrete 1°C pulses at 12h, 24h, 36h, 60h
- **Noise**: Gaussian (σ = 0.05°C) for realism

### LED Control
- **Inverse correlation** with temperature (-0.921 correlation)
- **Flashes**: 15-minute periods every 6 hours
- **Range**: 0.24 to 1.00 intensity

### Vibration Events
- **Triggered**: 15 minutes before each temperature pulse
- **Duration**: Continues until temperature drops
- **Random bursts**: 0.5% probability per minute
- **Total duty cycle**: 4.6% (3.3 hours over 72 hours)

## Usage Workflow

### Step 1: Generate Landscape
```bash
python generate_complex_landscape.py
python analyze_landscape.py
```
**Outputs**: `landscape.csv`, `landscape.png`

### Step 2: Prepare ESP32
1. Upload `landscape_executor.py` to ESP32
2. Copy `landscape.csv` to SD card `/sd/data/landscape.csv`
3. Ensure hardware is properly connected:
   - Heater: Pin 33
   - Cooler: Pin 27  
   - LED: Pin 25
   - Vibration: Pin 26

### Step 3: Execute on Hardware
```python
# On ESP32 (MicroPython)
import landscape_executor
# Will run for 72 hours, logging to SD card
```

### Step 4: Analyze Performance
```bash
# After copying hardware logs from SD card
python landscape_comparison.py
```
**Outputs**: Performance metrics, comparison plots

## Hardware Requirements

### Temperature Control
- **PTC Heater** (Pin 33) with PWM control
- **TEC Cooler** (Pin 27) with PWM control  
- **MAX31865 RTD** sensor for temperature feedback

### Actuators
- **White LED** (Pin 25) with PWM brightness control
- **Vibration Motor** (Pin 26) with PWM intensity control

### Data Logging
- **SD Card** for storing execution logs and comparison data

## Expected Performance Metrics

Based on previous testing, expect:
- **Temperature tracking**: <0.5°C RMSE
- **LED control**: >95% correlation with targets
- **Vibration timing**: >90% agreement with simulation

## Temporal Associations Demonstrated

1. **Temperature-Light Coupling**
   - Strong inverse correlation (-0.921)
   - Simulates natural thermal-optical relationships

2. **Anticipatory Vibration**
   - Activates 15 minutes before temperature peaks
   - Demonstrates predictive environmental control

3. **Multi-Modal Integration**
   - Coordinated thermal, optical, mechanical stimulation
   - Precise timing relationships

## For Research Papers

### Key Claims Supported
- ✅ Multi-parameter environmental control
- ✅ Complex temporal associations  
- ✅ Hardware-validated performance
- ✅ Biologically relevant patterns
- ✅ Reproducible experimental protocols

### Data Available
- Simulation targets vs. hardware performance
- Statistical validation metrics
- Publication-quality visualizations
- Complete parameter documentation

## Customization

### Modify Temperature Range
Edit `generate_complex_landscape.py`:
```python
TEMP_BASE = 27.5        # Center temperature
TEMP_SIN_AMP = 1.25     # Amplitude (±range)
PULSE_HEIGHT = 1.0      # Heat pulse magnitude
```

### Adjust Timing
```python
PULSE_CENTERS_H = [12, 24, 36, 60]  # Heat pulse times (hours)
FLASH_PERIOD_H = 6                   # LED flash interval
VIB_PRE_MIN = 15                     # Vibration pre-trigger time
```

### Hardware Pins
Edit `landscape_executor.py`:
```python
HEATER_PIN = 33         # PTC heater
COOLER_PIN = 27         # TEC cooler
LED_PIN = 25            # LED control
VIBRATION_PIN = 26      # Vibration motor
```

## Troubleshooting

### Common Issues
1. **SD Card not detected**: Check SPI connections and format
2. **Temperature sensor error**: Verify MAX31865 wiring
3. **Memory errors**: Increase garbage collection frequency
4. **Timing drift**: Use RTC for long experiments

### Debug Mode
Add to `landscape_executor.py`:
```python
DEBUG = True  # Enable verbose logging
```

## File Structure
```
Smart_incubator2/Smart_incubator/
├── generate_complex_landscape.py    # Landscape generation
├── landscape_executor.py            # ESP32 execution
├── landscape_comparison.py          # Performance analysis
├── analyze_landscape.py             # Statistics
├── landscape.csv                    # Target data
├── landscape.png                    # Visualization
├── landscape_documentation.md       # Detailed docs
└── README_landscape.md             # This file
```

## Publications

This landscape system demonstrates capabilities suitable for:
- **Environmental control papers**
- **Bioengineering applications** 
- **Systems biology studies**
- **Microfluidics integration**

The combination of precise hardware control and sophisticated temporal patterns provides a robust platform for biological research requiring complex environmental stimulation.

---
*ESP32 Smart Incubator v1.0 - Complex Environmental Landscape System* 