# Smart Incubator Platform

**An automated experimental platform for studying phenotypic plasticity, predictive learning, and cellular memory through precise environmental control**

The Smart Incubator is a sophisticated ESP32-based system designed to subject cell cultures to complex, long-term environmental protocols with precise temporal control. This platform enables researchers to test hypotheses about biological prediction, memory formation, and adaptive plasticity at the cellular level—providing insights into the evolutionary origins of learning behaviors that preceded neural systems.

---

## Table of Contents

- [Overview](#overview)
- [Key Capabilities](#key-capabilities)
- [System Architecture](#system-architecture)
- [Hardware Components](#hardware-components)
- [Quick Start](#quick-start)
- [Experimental Protocols](#experimental-protocols)
- [Data Management](#data-management)
- [Documentation](#documentation)
- [Safety Features](#safety-features)
- [Troubleshooting](#troubleshooting)

---

## Overview

The Smart Incubator creates a controllable "learning environment" where organisms experience either predictable or unpredictable relationships between environmental cues (conditional stimuli) and subsequent stressors (heat shocks). This design allows researchers to:

- **Test predictive learning capacity** in microorganisms through temporal association experiments
- **Study memory formation** by examining cellular responses to learned cue-stress relationships
- **Investigate phenotypic plasticity** across multiple time scales and environmental conditions
- **Explore pre-neural learning** mechanisms at the single-cell and population levels

### Design Philosophy

The platform emphasizes:
- **Long-term autonomy**: Runs multi-week experiments without intervention
- **Temporal precision**: Microsecond-level control of stimulus timing
- **Data integrity**: Comprehensive logging with cryptographic verification
- **Operational resilience**: Automated recovery from transient failures
- **Experimental flexibility**: Support for diverse correlation modes and custom protocols

### Research Applications

**Predictive Learning Studies:**
- Temporal association between environmental cues and thermal stress
- Correlation-dependent phenotypic responses
- Memory formation and decay dynamics

**Habituation Research:**
- Long-term adaptation to repeated stress cycles
- Valence reassignment experiments
- Threshold modification studies

**Complex Protocol Execution:**
- Multi-parameter landscape experiments
- Synchronized multi-modal stimulus delivery
- Adaptive protocol adjustment during runtime

---

## Key Capabilities

### Thermal Control System

**Dual-Actuator Temperature Regulation:**
- **PTC Heater**: Programmable heating from ambient to 40°C
- **TEC1 Peltier Cooler**: Active cooling below ambient temperature
- **PID Control**: Custom-tuned controller (Kp=6.0, Ki=0.02, Kd=1.5)
- **Precision**: ±0.5°C at basal temperature (23°C), ±0.8°C during heat shock (32°C)
- **Rapid Transitions**: 2-3 minute heating, 5-8 minute cooling times

**Temperature Sensing:**
- MAX31865 RTD-to-digital converter with PT100 platinum sensor
- Advanced noise filtering with median-of-5 sampling
- Fault detection and automatic sensor recovery
- Temperature range: 15-40°C (software limited for biological safety)

### Multi-Modal Stimulus Delivery

**Optical Stimulation (LED):**
- High-brightness white LED with PWM intensity control
- 16-bit resolution (65,535 discrete levels)
- Instantaneous on/off switching
- Configurable intensity (default: 25%)

**Mechanical Stimulation (Vibration Motor):**
- Miniature vibration motor with PWM amplitude control
- Programmable pulsing patterns (default: 20s on, 60s off)
- Thermal protection via duty cycling
- Configurable intensity (default: 100%)

**Combined Modes:**
- Independent control of each modality
- Simultaneous multi-modal delivery
- Temporal precision: microsecond-level timing accuracy

### Experimental Protocol Framework

**Correlation Modes** (Testing Predictive Relationships):

| Mode | Description | US-HS Timing | Measured Δt | Biological Interpretation |
|------|-------------|--------------|-------------|---------------------------|
| 0 | Non-Temporal Control | Random | -58.1 ± 113.9 min | No predictive value |
| 1 | Temporal Predictive | US precedes HS | 30.0 ± 0.3 min | Perfect correlation |
| 2 | Temporal Post-stress | US follows HS | Variable | Reversed association |
| 3 | Testing Mode | Short cycle | 0.5 min | Hardware validation |

**Cycle-Based Design:**
- Randomized cycle durations (200-400 minutes) prevent temporal entrainment
- Distinct basal and heat shock phases within each cycle
- Long-term stability: weeks of continuous operation
- Automated parameter management and state preservation

### Advanced Features

**Data Acquisition:**
- 10-second sampling rate with complete system snapshots
- Real-time logging to SD card with FAT32 compatibility
- SHA-256 checksums for data integrity verification
- Comprehensive metadata and provenance tracking

**Safety and Resilience:**
- Temperature failsafe with stuck sensor detection
- Automated sensor recovery system
- Hardware protection with progressive response mechanisms
- Memory management via periodic garbage collection
- Robust initialization with exponential backoff retry

**User Interfaces:**
- Real-time OLED status display (128×64 SSD1306)
- Optional web server for remote monitoring
- Serial console with detailed diagnostic output
- Comprehensive diagnostic tools built-in

---

## System Architecture

### Multi-Layer Software Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Application Layer: main.py → run_experiment_cycle.py  │
├─────────────────────────────────────────────────────────┤
│  Control Layer: temp_controller.py → us_control.py     │
├─────────────────────────────────────────────────────────┤
│  Hardware Layer: max31865.py → sd_logger.py → oled     │
├─────────────────────────────────────────────────────────┤
│  Driver Layer: heater.py → tec.py → led → vibration    │
├─────────────────────────────────────────────────────────┤
│  Boot Layer: boot.py (GPIO securing, initialization)   │
└─────────────────────────────────────────────────────────┘
```

### Core Components

**System Orchestration (`main.py`):**
- Hardware initialization with 5-attempt retry logic
- Global parameter management (temperature, timing, correlation modes)
- Continuous cycle execution with error tracking
- Memory management and heap monitoring

**Experiment Logic (`run_experiment_cycle.py`):**
- Random cycle length generation (200-400 minutes)
- Phase transition management (basal → heat shock)
- Correlation-based stimulus timing
- Real-time data collection (10-second intervals)

**Temperature Regulation (`temp_controller.py`):**
- Dual-actuator PID control system
- Anti-windup protection and target change detection
- PWM interference mitigation
- Temperature validation and fault recovery

**Stimulus Management (`us_control.py`):**
- Multi-modal control (LED, vibration, or both)
- Configurable timing patterns
- State tracking and status reporting
- Temperature-synchronized operation

**Data Management (`sd_logger.py`):**
- Structured directory hierarchy
- JSON-based logging with checksums
- Manifest system for file integrity
- Thread-safe operations with mutex locks

**Hardware Drivers:**
- `max31865.py`: PT100 RTD temperature sensor with advanced filtering
- `heater.py`, `tec.py`: Thermal actuator PWM control
- `led_control.py`, `vibration_control.py`: Stimulus delivery drivers
- `oled_display.py`: Real-time status interface

**Safety Systems:**
- `temperature_failsafe.py`: Comprehensive protection mechanisms
- `sensor_recovery.py`: Automated sensor restoration
- `sensor_diagnostic.py`: Health monitoring and troubleshooting

---

## Hardware Components

### Electronic Components

| Component | Model/Spec | Function | Interface |
|-----------|-----------|----------|-----------|
| Microcontroller | ESP32-WROOM-32 | System control (240 MHz dual-core) | — |
| Temperature Sensor | MAX31865 + PT100 RTD | Precision temperature measurement | SPI (VSPI): SCK 18, MOSI 23, MISO 19, CS 5 |
| Heater | PTC Heating Element | Warming actuator | PWM Pin 33 (MOSFET-controlled) |
| Cooler | TEC1 Peltier Module | Cooling actuator | PWM Pin 27 (MOSFET-controlled) |
| LED | High-brightness white LED | Optical stimulus | PWM Pin 25 |
| Vibration Motor | Miniature motor | Mechanical stimulus | PWM Pin 16 |
| SD Card Module | MicroSD (SPI) | Data storage | HSPI: SCK 14, MOSI 13, MISO 12, CS 15 |
| Display | SSD1306 128×64 OLED | Real-time status | I2C: SCL 22, SDA 21 |
| MOSFETs | IRFZ44N or IRLZ44N | Power switching | Various control pins |

### Pin Assignments

**Power Control:**
- Pin 27: TEC1 cooler control
- Pin 33: PTC heater control
- Pin 25: LED control
- Pin 16: Vibration control

**SPI Bus (Temperature & SD Card):**
- SCK 14: HSPI Clock
- MOSI 13: HSPI MOSI
- MISO 12: HSPI MISO
- CS 5: MAX31865 Chip Select
- CS 15: SD Card Chip Select

**I2C Bus (Display):**
- SCL 22: I2C Clock
- SDA 21: I2C Data

### Physical Design Files

**PCB Design:**
- KiCad schematic file included in `Hardware/PCB/`
- ESP32-DEVKITC-32D footprint
- MOSFET power control circuits
- Sensor interfacing

---

## Quick Start

### 📱 WiFi Configuration Mode (v2.0)

The Smart Incubator now features a **phone-based WiFi setup** mode. On boot, the ESP32 creates its own WiFi hotspot, allowing you to configure experiments directly from your phone without modifying code.

**How to use:**

1. **Power on the ESP32** → It creates a WiFi hotspot with unique SSID (e.g., `Inc-6774`)
2. **Connect your phone** to the WiFi network
   - SSID: `Inc-XXXX` (where XXXX is your device's unique ID)
   - Password: `incubator123`
3. **Open a browser** and go to `http://192.168.4.1`
4. **Set the time** → Click "Use Phone Time" to sync automatically
5. **Configure your experiment:**
   - Experiment name
   - Correlation value (-1 to +1)
   - Temperature settings
   - Interval and duration parameters
6. **Press "START EXPERIMENT"** → The incubator begins running
7. **Disconnect from WiFi** → The experiment runs autonomously

**Multiple Incubators:** Each device gets a unique SSID based on its MAC address, so you can run multiple incubators simultaneously without WiFi conflicts.

**Correlation Values:**
| Value | Meaning |
|-------|---------|
| +1.0 | US always precedes heat shock (paired/predictive) |
| 0.0 | US delivered randomly (control) |
| -1.0 | No US delivered |

---

### ⚡ Fast Track (Recommended)

**For complete deployment instructions, see:**
- 📘 **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete deployment documentation
- 🚀 **[QUICK_START.md](QUICK_START.md)** - Visual workflows and examples

**Quick commands:**

```bash
# 1️⃣ First time setup (blank ESP32)
python Smart_incubator/sync_firmware.py --correlation 1 --yes

# 2️⃣ Redeploy with alternate correlation (control runs)
python Smart_incubator/sync_firmware.py --correlation 0 --yes

# (Windows example if auto-detect misses COM port)
python Smart_incubator/sync_firmware.py --correlation 1 --yes --port COM3

# 3️⃣ Format SD card - see SD Card Formatting section below

# 4️⃣ Or use VS Code (even easier!)
# Press Ctrl+Shift+B to deploy (pick correlation in the prompt)
# Press Ctrl+Shift+P → "Tasks: Run Task" → choose task
```

> 💡 Set `INCUBATOR_PORT=COM3` (Windows) or `ESP32_PORT=/dev/ttyUSB0` (Linux/macOS) to skip `--port` each time.
> ℹ️ `sync_firmware.py` auto-detects `mpremote` (`mpremote`, `py -m mpremote`, `python -m mpremote`, etc.) and prints the command it will use. Set `MPREMOTE="path/to/mpremote"` if you need a custom executable.

**Available VS Code Tasks:**
- **Sync Firmware (Full Redeploy)** - Safe redeploy with correlation picker (default: `Ctrl+Shift+B`)
- **Format SD Card** - Clean SD card for new experiments
- **Deploy Core HES Modules** - Upload only HES system files
- **Deploy Full Firmware** - Upload all firmware files
- **Deploy Config Files Only** - Upload experiment configs
- **Open REPL** - Interactive Python shell
- **Run Experiment** - Start an experiment
- **List Files on Device** - Show ESP32 filesystem
- **Reset Device** - Soft reset ESP32

---

### � SD Card Formatting

**Two methods available depending on your needs:**

#### Method 1: Full Local Reformat (Recommended for new/corrupted cards)
Creates a fresh FAT32 (MBR) filesystem with required directories.

**macOS:**
```bash
# List available disks
diskutil list
python3 Smart_incubator/format_sd_card_local.py --list

# Format (replace disk6 with your SD card identifier)
python3 Smart_incubator/format_sd_card_local.py /dev/disk6

# Eject safely
diskutil eject /dev/disk6
```

**Linux:**
```bash
# List available disks
lsblk
python3 Smart_incubator/format_sd_card_local.py --list

# Format (replace sdb with your SD card identifier)
sudo python3 Smart_incubator/format_sd_card_local.py /dev/sdb

# Eject safely
sudo eject /dev/sdb
```

#### Method 2: ESP32 Cleanup (Quick cleanup for existing cards)
Clears files without reformatting the filesystem.

```bash
python3 Smart_incubator/format_sd_card.py
```

**When to use each method:**
- **Full reformat**: New cards, corrupted filesystems, or complete reset needed
- **ESP32 cleanup**: Quick data wipe between experiments on working cards

📘 **For detailed instructions and troubleshooting, see [SD_CARD_FORMATTING_GUIDE.md](SD_CARD_FORMATTING_GUIDE.md)**

---

The Smart Incubator includes sophisticated deployment automation:

#### 1. **Full Redeploy Sync** (`sync_firmware.py`)
Safe, repeatable firmware deployment every time:
- Installs a temporary safe boot, wipes the device, and re-uploads all firmware
- Automatically reconfigures the SD card structure and required packages
- Optional `--correlation 0|1` flag rewrites `main.py` before upload so you never edit by hand
- `--yes` (or the VS Code task) skips prompts for unattended reflashes
- Auto-detects the ESP32 port, with `--port` override when needed
- Validates the `mpremote` command before flashing and falls back through multiple launchers; override with `MPREMOTE` if your setup is non-standard

#### 2. **SD Card Formatter** (`format_sd_card.py`)
Prepares SD card with proper structure:
- Removes all experiment data
- Clears old config files  
- Creates fresh directory structure
- Shows storage statistics
- Requires double confirmation for safety

#### 3. **Manual Deployment** (`deploy.sh`)
Traditional deployment script for specific scenarios:
- Core modules only
- Full firmware
- Config files only

---

### Prerequisites

**Hardware Setup:**
1. ESP32 development board properly wired according to pin assignments
2. MAX31865 + PT100 RTD sensor installed
3. PTC heater and TEC cooler with MOSFET drivers
4. LED and vibration motor connected
5. SD card formatted as DOS_FAT_32 with MBR partition scheme
6. SSD1306 OLED display (optional but recommended)

**Software Requirements:**
- MicroPython firmware (ESP32-GENERIC v1.24.1 or later)
- All firmware files from `Firmware/` directory uploaded to ESP32

### Installation Steps

1. **Format SD Card:**
   See the **SD Card Formatting** section above for complete instructions.
   - For new cards: Use full local reformat method
   - For existing cards: Use ESP32 cleanup method

2. **Upload Firmware:**
   Upload all `.py` files from `Firmware/` to ESP32 root directory using Thonny or ampy:
   ```bash
   ampy -p /dev/ttyUSB0 put boot.py
   ampy -p /dev/ttyUSB0 put main.py
   # ... (upload all firmware files)
   ```

3. **Verify Installation:**
   ```python
   # Run on ESP32 via REPL:
   import os
   print(os.listdir())
   # Confirm all required files are present
   ```

4. **Test Hardware:**
   ```python
   # Run hardware test suite:
   import Tests
   Tests.main()
   ```

5. **Power On:**
   - System will automatically initialize
   - Check OLED display for status
   - Monitor serial console for detailed logging

### Default Configuration

**Temperature Settings:**
- Basal temperature: 23°C
- Heat shock temperature: 32°C

**Cycle Parameters:**
- Duration: 200-400 minutes (randomized)
- US duration: 30 seconds
- Heat shock duration: 30 minutes

**Stimulus Configuration:**
- Type: Both LED and vibration
- LED intensity: 25%
- Vibration intensity: 100%
- Vibration pattern: 20s on / 60s off

**Correlation Mode:**
- Default: Mode 1 (US precedes heat shock by 30 minutes)

**Data Logging:**
- Sampling rate: Every 10 seconds
- Directory: `/sd/data/DDMMYYYY_correlation/`
- Format: JSON with SHA-256 checksums

---

## Experimental Protocols

### Standard Temporal Learning Protocol

**Goal:** Test whether organisms can learn to predict heat shock based on prior sensory cues.

**Configuration:**
```python
# In main.py:
basal_temp = 23.0      # Optimal growth temperature
heat_shock_temp = 32.0  # Stress temperature
correlation = 1         # US precedes heat shock
min_interval = 200      # Minimum cycle length (minutes)
max_interval = 400      # Maximum cycle length (minutes)
us_duration = 0.5       # US duration (minutes)
heat_duration = 30      # Heat shock duration (minutes)
```

**Experimental Timeline:**
1. **Basal Phase** (variable 170-370 min): Maintain 23°C
2. **US Delivery** (30 sec): Present LED/vibration stimulus
3. **Predictive Interval** (30 min): Continue at 23°C
4. **Heat Shock** (30 min): Increase to 32°C
5. **Recovery** (2-5 min): Return to basal conditions
6. **Repeat**: Begin next randomized cycle

**Expected Outcomes:**
- **Correlation = 1**: Cells may develop anticipatory responses to US
- **Correlation = 0**: No predictive relationship (control)

### Non-Temporal Control Protocol

**Goal:** Verify that responses are due to temporal association, not stimulus intensity.

**Configuration:**
```python
correlation = 0  # Random independent timing
# All other parameters identical to standard protocol
```

### Complex Landscape Execution

**Goal:** Run pre-programmed multi-parameter protocols.

**Setup:**
1. Create CSV landscape file with time-series data
2. Place in `/sd/` directory
3. Launch with `landscape_executor_enhanced.py`

**Features:**
- Simultaneous temperature, LED, and vibration control
- Complex waveforms (sinusoidal, ramp, step functions)
- Multi-day automated execution

---

## Data Management

### Directory Structure

```
/sd/data/
├── [DDMMYYYY_correlation]/       # Experiment directory
│   ├── meta.json                 # Experiment metadata
│   ├── manifest.json             # File integrity manifest
│   ├── cycle_N_TIMESTAMP.json    # Data snapshots (10-sec intervals)
│   └── cycle_N_summary.json      # End-of-cycle statistics
```

### Data File Formats

**Metadata (`meta.json`):**
```json
{
  "experiment_id": "9298_1",
  "start_time": 1635724800,
  "basal_temp": 23.0,
  "heat_shock_temp": 32.0,
  "correlation": 1,
  "firmware_version": "1.0.0"
}
```

**Data Snapshot (`cycle_N_TIMESTAMP.json`):**
```json
{
  "timestamp": 18883,
  "temp": 31.63,
  "set_temp": 23.0,
  "power": -89.55,
  "mode": "Cooling",
  "tec_state": "On",
  "us_active": 0,
  "elapsed_minutes": 0.17,
  "cycle_length": 242,
  "phase": "basal",
  "cycle_num": 2
}
```

**Cycle Summary (`cycle_N_summary.json`):**
```json
{
  "cycle": 5,
  "duration": 245.3,
  "temp_min": 22.8,
  "temp_max": 32.5,
  "temp_mean": 24.1,
  "temp_std": 3.2,
  "error_count": 0,
  "us_deliveries": 1,
  "heat_shock_success": true
}
```

### Data Integrity

**Cryptographic Verification:**
- SHA-256 checksums for all data files
- Manifest tracking with verification
- Automatic corruption detection

**Quality Assurance:**
- Range checking on sensor readings
- Temporal consistency validation
- Cross-parameter logical checks
- Missing data detection and flagging

### Analysis Tools

**Built-in Scripts:**
- `plot_experiment_data.py`: Visualization of cycle data
- `custom_analysis_*.py`: Statistical analysis examples
- Export utilities for external platforms

**Python Analysis (Run on PC):**
```python
import json
import matplotlib.pyplot as plt

# Load cycle data
with open('cycle_10_154510.json') as f:
    data = json.load(f)

# Plot temperature over time
plt.plot(data['timestamp'], data['temp'])
plt.xlabel('Time (s)')
plt.ylabel('Temperature (°C)')
plt.show()
```

---

## Documentation

### Included Documentation Files

**Core Documentation (`Docs/`):**
- `Smart Incubator Platform M&M.md`: Comprehensive methods and materials
- `Smart Incubator Platform M&M.tex`: LaTeX version for manuscript preparation
- `README.md` (this file): System operation guide
- `materials_and_methods.md`: Detailed experimental protocols

**Technical Specifications:**
- `BUG_ANALYSIS_AND_SOLUTION.md`: Critical bug fixes and failsafe solutions
- `SENSOR_RECOVERY_SOLUTION.md`: Enhanced sensor recovery documentation
- `PLOTTING_GUIDE.md`: Data visualization best practices

**Advanced Features:**
- `README_landscape.md`: Landscape mode protocol guide
- `landscape_documentation.md`: Advanced landscape executor details

### Firmware Documentation

Each firmware module includes comprehensive docstrings:
- Module purpose and architecture
- Class and function documentation
- Parameter descriptions and ranges
- Error handling procedures
- Usage examples

Access via REPL:
```python
import temp_controller
help(temp_controller)
```

---

## Safety Features

### Temperature Failsafe System

**Protective Mechanisms:**
1. **Stuck Sensor Detection**: Identifies frozen temperature readings
2. **Overheat Protection**: Emergency shutdown above safety threshold
3. **Progressive Response**: Graduated intervention based on severity
4. **Hardware Protection**: Automatic actuator disabling on critical errors

**Failsafe Triggers:**
- Sensor reading unchanged for >5 minutes
- Temperature exceeds 45°C (biological safety limit)
- Sensor fault flags from MAX31865
- Repeated temperature validation failures

**Response Actions:**
- Level 1: Increase monitoring frequency
- Level 2: Disable heating actuators
- Level 3: Enable cooling system
- Level 4: Complete system shutdown with error logging

### Automated Sensor Recovery

**Recovery System:**
- Detects stuck or noisy sensor readings
- Attempts automated sensor reinitialization
- Multi-stage recovery protocol
- Continues experiment if recovery successful

**Recovery Procedure:**
1. Identify anomalous readings (change < 0.01°C for 5 min)
2. Temporarily disable PWM interference sources
3. Power cycle sensor via SPI reset
4. Verify restored functionality
5. Resume normal operation or escalate to failsafe

### Error Resilience

**Initialization Resilience:**
- Up to 5 retry attempts for hardware components
- Exponential backoff delays between attempts
- Cleanup and reset between retries
- Detailed error logging for diagnostics

**Operational Resilience:**
- Graceful degradation on non-critical failures
- Continue operation without display if OLED fails
- Experiment continues if logging fails (with warnings)
- Consecutive error tracking with automatic restart

**Memory Management:**
- Periodic garbage collection (every 5 minutes)
- Heap monitoring and leak detection
- Global variable cleanup between cycles
- Resource cleanup on errors

---

## Troubleshooting

### Common Issues and Solutions

#### SD Card Initialization Failed

**Symptoms:** "SD card initialization failed" on startup

**Causes:**
- Incorrect SD card format (must be DOS_FAT_32 with MBR)
- Missing `/data/` directory
- Poor quality SD card
- Loose connections

**Solutions:**
1. Reformat SD card properly:
   ```bash
   # macOS:
   sudo diskutil eraseDisk MS-DOS INCUBATOR MBR /dev/diskX
   ```
2. Manually create `/data/` directory
3. Try a different high-quality SD card (Class 10 recommended)
4. Check SPI wiring (pins 12, 13, 14, 15)

#### Temperature Sensor Not Responding

**Symptoms:** Constant temperature readings or sensor errors

**Causes:**
- Loose RTD connections
- SPI communication issues
- PT100 sensor failure
- Incorrect reference resistor

**Solutions:**
1. Run sensor diagnostic:
   ```python
   import sensor_diagnostic
   sensor_diagnostic.run_full_diagnostic()
   ```
2. Check all RTD wiring (2, 3, or 4-wire configuration)
3. Verify 430Ω reference resistor installed correctly
4. Test with known-good sensor

#### Display Not Working

**Symptoms:** OLED shows no output or garbled display

**Causes:**
- Missing `ssd1306.py` library
- I2C address mismatch (0x3C vs 0x3D)
- I2C wiring issues
- Power supply insufficient

**Solutions:**
1. Verify `ssd1306.py` uploaded to ESP32
2. Try alternate I2C address in `oled_display.py`
3. Check I2C connections (pins 21, 22)
4. Ensure stable 3.3V/5V power supply
5. System continues without display—not critical

#### Temperature Control Unstable

**Symptoms:** Temperature oscillates or overshoots target

**Causes:**
- PID parameters need tuning
- PWM frequency too high/low
- Thermal mass insufficient
- Actuator sizing issues

**Solutions:**
1. Run PID tuning guide:
   ```python
   import pid_tuning_guide
   pid_tuning_guide.run_auto_tune()
   ```
2. Adjust PID constants in `temp_controller.py`
3. Increase thermal mass of chamber
4. Verify heater/cooler power ratings adequate

#### Experiment Not Starting

**Symptoms:** System initializes but cycles don't begin

**Causes:**
- Parameter configuration errors
- Hardware component initialization failed
- Memory issues
- Critical error state

**Solutions:**
1. Check serial console for error messages
2. Verify all parameters valid in `main.py`
3. Run hardware test suite:
   ```python
   import Tests
   Tests.main()
   ```
4. Power cycle system for fresh start
5. Check available heap memory

### Diagnostic Tools

**Built-in Diagnostics:**
```python
# Comprehensive sensor diagnostic
import sensor_diagnostic
sensor_diagnostic.run_full_diagnostic()

# SD card verification
import sd_logger
sd_logger.verify_sd_integrity()

# Hardware component test
import Tests
Tests.main()

# Memory status
import gc
gc.collect()
print(f"Free heap: {gc.mem_free()} bytes")
```

**Serial Console Monitoring:**
- Connect via USB serial (115200 baud)
- Real-time system status messages
- Detailed error reporting
- Component initialization logs

### Getting Help

**Diagnostic Information to Collect:**
1. Complete serial console output
2. SD card contents (especially `meta.json` and error logs)
3. Hardware configuration details
4. Firmware file list and versions
5. Description of observed behavior vs. expected

**Reporting Issues:**
- Document exact steps to reproduce
- Include all diagnostic tool outputs
- Note any recent changes to hardware/software
- Provide photos of hardware setup if relevant

---

## Advanced Features

### Web Server Mode

Optional remote monitoring and control interface:

```python
# Use main_with_server.py instead of main.py
# Access via browser at ESP32's IP address
# Features:
# - Real-time temperature display
# - Current cycle status
# - Parameter adjustment
# - System health monitoring
```

### Landscape Executor

Execute complex pre-programmed protocols:

```python
import landscape_executor_enhanced

# Load and execute CSV-based protocol
landscape_executor_enhanced.run_landscape('complex_protocol.csv')

# Features:
# - Multi-parameter control
# - Complex waveforms
# - Long-duration experiments
# - Synchronized multi-modal delivery
```

### Custom Analysis Pipeline

Built-in analysis scripts for data processing:

```python
# Generate publication-ready figures
python custom_analysis_0_0_publish_ready.py

# Correlation analysis
python custom_analysis_comparison_improved.py

# Exploratory analysis
python custom_analysis_exploratory_publication.py
```

---

## Research Context

### Manuscript Integration

This platform is described in the manuscript:

**"Beyond Diffusion: Bayesian Learning Strategies in Single-Cell Life"**

The Smart Incubator specifically supports experiments testing:
- Cue-based learning in microorganisms
- Valence assignment to environmental stimuli
- Prediction and memory at the cellular level
- Pre-neural Bayesian inference mechanisms

### Experimental Design Rationale

**Temporal Correlation Paradigm:**
The ability to create predictable vs. unpredictable cue-stress relationships allows direct testing of whether organisms use Bayesian-like inference to predict environmental changes.

**Randomized Cycle Lengths:**
Variable cycle durations prevent organisms from using simple timing
