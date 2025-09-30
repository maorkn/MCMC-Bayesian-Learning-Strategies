# Smart Incubator Control System

This repository contains the MicroPython source code for an advanced, automated Smart Incubator. The system is designed to run long-term biological experiments, providing precise temperature control and delivering timed stimuli (like ultrasound and light) according to a configurable scientific protocol.

## Features

- **Precise Temperature Control:** Utilizes a PID controller to manage a PTC heater and a TEC1 cooler, maintaining stable basal temperatures and executing programmed heat shocks.
- **Automated Experiment Cycles:** Runs experiments in cycles of variable length, managing different phases (e.g., basal temperature, heat shock).
- **Configurable Stimuli:** Delivers ultrasound (vibration) and LED light stimuli with configurable timing and intensity.
- **Flexible Protocols:** Supports different experimental protocols by correlating the timing of heat shock and other stimuli in various ways (e.g., stimulus before, during, or after heat shock).
- **Robust Data Logging:** Logs detailed time-series data for each experiment cycle to an SD card, including temperature, setpoints, power levels, and stimuli status. Also saves cycle summaries and experiment metadata.
- **Hardware Abstraction:** Modular code with clear separation between high-level experiment logic, mid-level controllers (temperature, ultrasound), and low-level hardware drivers.
- **Resilience:** Includes mechanisms for error handling, retrying hardware initializations, and recovering from transient sensor or SD card failures to ensure long-term operational stability.
- **Advanced Sensor Recovery:** Automated sensor recovery system that can detect stuck temperature readings and attempt to restore sensor functionality without terminating experiments.
- **Temperature Failsafe Protection:** Comprehensive failsafe system that detects dangerous conditions (stuck sensors, overheating) and automatically protects hardware with progressive response mechanisms.
- **Diagnostic Tools:** Built-in diagnostic systems for comprehensive sensor health monitoring and troubleshooting.
- **Real-time Monitoring:** An OLED display provides real-time feedback on the incubator's status, including current temperature, target temperature, cycle progress, and active stimuli.
- **(Optional) Web Server:** `main_with_server.py` provides an alternative entry point that includes a web server for remote monitoring.

## System Architecture

The Smart Incubator is built on a **sophisticated multi-layer architecture** designed for reliable biological experimentation with precise environmental control. The system follows a modular design pattern with clear separation of concerns across hardware abstraction, control logic, and scientific protocols.

### **Architectural Overview**

```
Application Layer:     main.py → run_experiment_cycle.py
                           ↓
Control Layer:        temp_controller.py → us_control.py
                           ↓
Hardware Layer:       max31865.py → sd_logger.py → oled_display.py
                           ↓
Driver Layer:         heater.py → tec.py → led_control.py → vibration_control.py
                           ↓
Boot Layer:           boot.py (GPIO securing, system initialization)
```

### **Core Components - Detailed Analysis**

#### **1. System Orchestration Layer**

**`main.py` - System Orchestrator & Entry Point**
- **Primary Functions**:
  - **Hardware initialization with retry logic**: 5-attempt initialization sequence with cleanup between attempts
  - **Global parameter management**: Temperature setpoints, timing parameters, correlation modes
  - **Continuous cycle execution**: Infinite loop managing experiment cycles
  - **Error recovery systems**: Consecutive error tracking, automatic restart mechanisms
  - **Memory management**: Garbage collection between cycles, heap monitoring
- **Key Variables**: 
  - `basal_temp = 23.0°C`, `heat_shock_temp = 32.0°C`
  - `min_interval = 200min`, `max_interval = 400min` (cycle length randomization)
  - `correlation = 1` (stimulus-heat shock timing relationship)
- **Error Handling**: Maximum 3 consecutive errors before system halt
- **Memory Optimization**: Explicit garbage collection, global variable cleanup

**`boot.py` - System Initialization & Safety**
- **Critical Safety Features**:
  - **GPIO securing**: All output pins initialized to OFF state on startup
  - **SPI CS management**: Chip select pins set to inactive (HIGH) state
  - **CPU optimization**: 240MHz frequency setting for optimal performance
  - **Memory preparation**: Garbage collection enabled, initial cleanup
  - **Hardware stabilization**: Timed delays for component settling

#### **2. Scientific Protocol Engine**

**`run_experiment_cycle.py` - Experiment Logic Core**
- **Cycle Management**:
  - **Random cycle length**: 200-400 minutes (3.3-6.7 hours) for biological variability
  - **Phase transitions**: Basal temperature maintenance → Heat shock delivery
  - **Correlation-based timing**: 4 different stimulus-heat shock relationships
  - **Real-time monitoring**: 10-second logging intervals throughout cycle
- **Correlation Modes Detailed**:
  - **Mode 0**: Random independent timing for US and heat shock
  - **Mode 1**: US immediately precedes heat shock (at cycle end) - DEFAULT
  - **Mode 2**: US immediately follows heat shock
  - **Mode 3**: Testing mode (heat at 1min, US at 0.5min)
- **Data Collection**:
  - **Snapshot logging**: Temperature, power, mode, phase every 10 seconds
  - **Cycle statistics**: Min/max/average temperatures, error counts, duration
  - **PWM noise mitigation**: Temporary stimulus deactivation during critical temperature logging
- **Error Recovery**: Temperature validation, fallback to last known good values

#### **3. Temperature Regulation System**

**`temp_controller.py` - PID-Based Thermal Control**
- **Advanced PID Implementation**:
  - **Dual-actuator system**: PTC heater (warming) + TEC cooler (cooling)
  - **PID parameters**: kp=6.0, ki=0.02, kd=1.5 (tuned for 1kHz PWM)
  - **Anti-windup protection**: Integral term limiting to prevent overshoot
  - **Target change detection**: PID reset on significant setpoint changes (>2°C)
- **Noise Management**:
  - **PWM interference mitigation**: Coordinated timing between control and measurement
  - **Temperature validation**: Range checking (-50°C to 100°C), spike detection
  - **Multiple reading attempts**: Up to 3 retries with delays for reliable measurement
- **Control Logic**:
  - **Idle zone**: -0.1°C to +0.5°C deadband to prevent actuator oscillation
  - **Heating mode**: Positive PID output → heater activation, cooler OFF
  - **Cooling mode**: Negative PID output → cooler activation + 35% boost, heater OFF
- **Error Handling**: Sensor fault detection, graceful degradation, safety shutdown

#### **4. Hardware Interface Layer**

**`max31865.py` - Precision Temperature Sensing**
- **Advanced Noise Filtering**:
  - **Median filtering**: 5-reading median calculation to eliminate spikes
  - **Change rate limiting**: Maximum 5°C/reading change validation
  - **Historical tracking**: 10-reading history for trend analysis
  - **Multi-attempt reading**: Up to 3 attempts per measurement cycle
- **SPI Communication**:
  - **Bus arbitration**: Coordination with SD card SPI to prevent conflicts
  - **Timing optimization**: 250kHz baudrate, extended delays for reliability
  - **Fault detection**: Real-time MAX31865 fault register monitoring
- **PT100 RTD Processing**:
  - **Resistance calculation**: 430Ω reference resistor compensation
  - **Temperature conversion**: Callendar-Van Dusen equation implementation
  - **Range validation**: 50-200Ω resistance range (≈-50°C to +150°C)

**`sd_logger.py` - Comprehensive Data Management**
- **Structured Data Architecture**:
  - **Experiment directories**: `/sd/data/DDMMYYYY_correlation/`
  - **JSON-based logging**: Individual snapshot files with timestamps
  - **Manifest system**: SHA-256 checksums for data integrity
  - **Metadata preservation**: Complete experiment parameter recording
- **Data Integrity Features**:
  - **Retry mechanisms**: Up to 3 write attempts with delays
  - **Checksum validation**: SHA-256 for all data files
  - **Memory management**: Limited manifest size (100 entries) to prevent memory issues
  - **Error recovery**: Continue operation even if SD logging fails
- **File Organization**:
  - `meta.json`: Experiment parameters and configuration
  - `cycle_N_TIMESTAMP.json`: Individual data snapshots
  - `cycle_N_summary.json`: End-of-cycle statistics
  - `manifest.json`: File integrity and experiment status

**`us_control.py` - Unified Stimulus Management**
- **Multi-Modal Control**:
  - **LED control**: PWM-based brightness (0-100%), default 25%
  - **Vibration control**: PWM-based intensity (0-100%), default 100%
  - **Combined modes**: LED, VIB, or BOTH simultaneously
- **Timing Pattern Management**:
  - **Configurable intervals**: Default 20s ON, 60s OFF for vibration
  - **State tracking**: Real-time activation status monitoring
  - **Synchronized operation**: Coordinated LED/vibration activation
- **Integration Features**:
  - **Temperature-synchronized**: Deactivation during critical temperature readings
  - **Display integration**: Status reporting to OLED display
  - **Error isolation**: Individual component failure handling

**`oled_display.py` - Real-Time Status Interface**
- **Information Display**:
  - **Temperature monitoring**: Current vs. target with 0.1°C precision
  - **Progress tracking**: Visual progress bar, cycle timing
  - **Component status**: US active/inactive, TEC on/off states
  - **Experimental context**: Cycle number, correlation mode display
- **Update Management**:
  - **Rate limiting**: 1-second update intervals to prevent flicker
  - **Error resilience**: Continues operation if display fails
  - **Memory efficient**: Minimal buffer usage for long-term stability

#### **5. Low-Level Hardware Drivers**

**Power Control Modules**:
- **`heater.py`**: PTC heater PWM control (1kHz, 16-bit resolution)
- **`tec.py`**: TEC cooler PWM control with on/off state management
- **`led_control.py`**: LED brightness control (0-100% mapping to 16-bit PWM)
- **`vibration_control.py`**: Vibration motor intensity control with timing patterns

### **Data Flow Architecture**

#### **Initialization Sequence**:
1. **Boot Safety**: GPIO securing, hardware stabilization
2. **Component Init**: Temperature sensor, display, thermal actuators
3. **Storage Setup**: SD card mounting, experiment directory creation
4. **Parameter Loading**: Configuration validation, PID initialization
5. **System Verification**: Initial temperature reading, component status check

#### **Cycle Execution Flow**:
1. **Cycle Planning**: Random duration calculation, correlation-based timing
2. **Temperature Control Loop**: 
   - Continuous PID regulation
   - Real-time power adjustment
   - Noise-mitigated sensor readings
3. **Stimulus Management**:
   - Phase-based activation (basal vs. heat shock periods)
   - Timing pattern execution (vibration intervals)
   - Display status updates
4. **Data Collection**:
   - 10-second snapshot logging
   - Real-time statistics calculation
   - End-of-cycle summary generation
5. **Cycle Completion**: Statistics finalization, cleanup, memory management

#### **Error Recovery Mechanisms**:
- **Temperature Sensor**: Multiple reading attempts, last-valid-value fallback
- **SD Card**: Write retries, continue without logging if persistent failure
- **Display**: Optional component, system continues if initialization fails
- **Power Control**: Safety shutdown on critical errors
- **Memory**: Periodic garbage collection, heap monitoring

### **Inter-Component Communication**

#### **SPI Bus Management**:
- **Shared Resources**: MAX31865 temperature sensor, SD card
- **Arbitration**: Explicit chip select management, timing coordination
- **Noise Prevention**: PWM synchronization, measurement windows

#### **PWM Coordination**:
- **Frequency Standardization**: 1kHz across all PWM channels
- **Interference Mitigation**: Coordinated activation/deactivation
- **Resolution Consistency**: 16-bit duty cycle resolution throughout

#### **State Synchronization**:
- **Global Variables**: Shared component instances across modules
- **Status Propagation**: Real-time state updates to display and logging
- **Error Broadcasting**: Component failure notification system

### Hardware Drivers & Abstractions

- **`heater.py` & `tec.py`**: Advanced PWM-based thermal actuator control with safety features and state management
- **`led_control.py` & `vibration_control.py`**: Low-level stimulus drivers with intensity control and pattern management
- **`max31865.py`**: Sophisticated PT100 RTD sensor driver with noise filtering and fault detection
- **`oled_display.py`**: Real-time status display with rate limiting and error resilience
- **`utils.py`**: Utility functions for random interval generation and JSON handling

### Configuration

The primary experiment parameters are configured at the top of the `main.py` file:

- `basal_temp`: The baseline temperature for the incubator.
- `heat_shock_temp`: The target temperature during the heat shock phase.
- `us_type`: The type of ultrasound stimulus ("LED", "VIB", or "BOTH").
- `min_interval` / `max_interval`: The minimum and maximum duration (in minutes) for a single experiment cycle. The actual length is randomized within this range.
- `us_duration` / `heat_duration`: The duration (in minutes) for the ultrasound stimulus and the heat shock phase.
- `correlation`: A key experimental parameter that defines the timing relationship between the ultrasound stimulus and the heat shock.
    - `0`: Random timing for both.
    - `1`: US immediately precedes the heat shock.
    - `2`: US immediately follows the heat shock.
    - `3`: A special short cycle for testing.

### Data Logging

The `ExperimentLogger` class creates a new directory for each experiment run on the SD card (e.g., `/sd/exp_001`, `/sd/exp_002`, etc.). Each directory contains:

- **`metadata.json`**: A JSON file storing the initial configuration parameters for the experiment.
- **`data.csv`**: A CSV file containing the time-series data for all cycles. Each row is a snapshot with columns for timestamp, cycle number, temperature, setpoint, power, mode, etc.
- **`cycle_summary.csv`**: A CSV file containing a summary for each completed cycle, including min/max/avg temperatures, duration, and error counts.

## How to Run

1.  **Hardware Setup:** Ensure all components (ESP32, temperature sensor, heater, cooler, display, SD card reader) are wired correctly according to the pin definitions in `main.py`.
2.  **Prepare SD Card:** Format an SD card with a FAT32 filesystem. The system will create the necessary files and directories.
3.  **Deploy Code:** Upload all the Python files from the `Smart_incubator` directory to the root of the ESP32's filesystem using a tool like Thonny or `ampy`.
4.  **Power On:** The `boot.py` file will run on startup, and then `main.py` will be executed, starting the initialization process and then the experiment cycles.

The system will print detailed status messages to the serial console (REPL), which is invaluable for monitoring and debugging.

## Hardware Requirements

- ESP32 Development Board
- MAX31865 Temperature Sensor with PT100 RTD
- PTC Heater
- TEC1 Peltier Cooler
- LED Module
- Vibration Module
- SD Card Module (SPI interface)
- SSD1306 OLED Display (128x64, I2C interface)
- MOSFETs for power control

## Pin Assignments

### Power Control
- TEC_PIN: 27 (TEC1 cooler control)
- PTC_PIN: 33 (PTC heater control)
- LED_PIN: 25 (LED control)
- VIB_PIN: 16 (Vibration control)

### SPI (Temperature Sensor & SD Card)
- SCK: 14 (HSPI Clock)
- MOSI: 13 (HSPI MOSI)
- MISO: 12 (HSPI MISO)
- CS_MAX: 5 (MAX31865 Chip Select)
- CS_SD: 15 (SD Card Chip Select)

### I2C (OLED Display)
- SCL: 22 (I2C Clock)
- SDA: 21 (I2C Data)

## SD Card Setup and Requirements

### Critical: SD Card Formatting Requirements

The ESP32 requires a specific SD card format to work reliably:

**Required Format:**
- **File System**: DOS_FAT_32 (not regular FAT32)
- **Partition Scheme**: MBR (Master Boot Record)
- **Size**: 4GB to 32GB recommended

### SD Card Preparation Procedure

#### Option 1: Using the Preparation Script (Recommended)

1. **Format the SD card** properly:
   ```bash
   # On macOS:
   sudo diskutil eraseDisk MS-DOS INCUBATOR MBR /dev/diskX
   
   # On Windows:
   # Use Disk Management to create MBR partition with FAT32
   
   # On Linux:
   sudo fdisk /dev/sdX  # Create MBR partition table
   sudo mkfs.fat -F 32 /dev/sdX1  # Format as FAT32
   ```

2. **Run the preparation script**:
   ```bash
   python prepare_sd_card.py
   ```

3. The script will:
   - Verify the SD card format
   - Create the required `/data/` directory structure
   - Add sample files for testing
   - Verify read/write functionality

#### Option 2: Manual Setup

1. **Format the SD card** as DOS_FAT_32 with MBR partition scheme
2. **Create directory structure**:
   ```
   /
   ├── data/
   │   └── readme.txt (optional test file)
   ```

### SD Card Verification

Use the included diagnostic script to verify your SD card setup:

```python
# Run on ESP32:
import sd_logger
if sd_logger.init_sd():
    print("SD card initialized successfully!")
else:
    print("SD card initialization failed!")
```

### Common SD Card Issues and Solutions

#### Issue: "SD card initialization failed"
**Causes:**
- Incorrect format (needs DOS_FAT_32 with MBR, not GUID)
- Missing `/data/` directory
- Poor SD card quality or corruption
- Loose connections

**Solutions:**
1. Reformat using the correct procedure above
2. Try a different SD card (Class 10 recommended)
3. Check SPI connections (pins 12, 13, 14, 15)

#### Issue: "Data directory creation failed"
**Cause:** SD card is read-only or corrupted

**Solution:** Reformat the SD card completely

#### Issue: Intermittent logging failures
**Causes:**
- Poor quality SD card
- Power supply issues
- SPI interference

**Solutions:**
1. Use a high-quality Class 10 SD card
2. Ensure stable 3.3V power supply
3. Keep SPI wires short and away from power lines

### Data Structure

The system automatically creates the following structure:

```
/sd/data/
├── [experiment_id]/
│   ├── meta.json           # Experiment metadata
│   ├── manifest.json       # File manifest with checksums
│   ├── cycle_X_TIMESTAMP.json  # Data snapshots
│   └── cycle_X_summary.json    # Cycle summaries
```

**Experiment ID Format:** `DDMMYYYY_correlation`
- Based on current date and correlation setting
- Example: `9298_1` (day 9298 since epoch, correlation 1)

## Software Structure

### Core Files
- `main.py`: Main program entry point
- `boot.py`: Boot sequence and initialization
- `temp_controller.py`: Temperature control logic
- `run_experiment_cycle.py`: Experiment cycle management

### Hardware Interfaces
- `max31865.py`: Temperature sensor interface
- `sd_logger.py`: SD card data logging functionality
- `oled_display.py`: OLED display interface
- `ssd1306.py`: SSD1306 OLED driver library

### Control Modules
- `led_control.py`: LED control
- `vibration_control.py`: Vibration control
- `us_control.py`: Unified US (Unconditional Stimulus) controller
- `tec.py`: TEC1 cooler control
- `heater.py`: PTC heater control

### Safety & Diagnostic Modules
- `temperature_failsafe.py`: Advanced failsafe system with stuck sensor detection
- `sensor_recovery.py`: Automated sensor recovery and restoration system
- `sensor_diagnostic.py`: Comprehensive sensor health monitoring and diagnostics

### Utilities
- `prepare_sd_card.py`: SD card preparation script (run on computer)
- `check_files.py`: Verify files are uploaded to ESP32
- `Tests.py`: Hardware test suite

### Documentation
- `BUG_ANALYSIS_AND_SOLUTION.md`: Critical bug analysis and failsafe solution documentation
- `SENSOR_RECOVERY_SOLUTION.md`: Enhanced sensor recovery system documentation
- `README_landscape.md`: Landscape mode experimental protocols
- `landscape_documentation.md`: Advanced landscape executor documentation

## Installation

### 1. Prepare SD Card
Follow the SD card setup procedure above **before** inserting into ESP32.

### 2. Upload Files to ESP32
Ensure all required files are uploaded to your ESP32:

**Required Files:**
- All `.py` files from the project
- Especially: `ssd1306.py` and `oled_display.py` for display
- `sdcard.py` for SD card interface (usually included in MicroPython)

**Verify Upload:**
```python
# Run check_files.py on ESP32 to verify all files are present
import check_files
check_files.check_files()
```

### 3. Hardware Connections
Connect all components according to the pin assignments above.

### 4. Test System
Run the test suite to verify all components:
```python
import Tests
Tests.main()
```

## Usage

### Automatic Operation
1. **Insert prepared SD card** into ESP32
2. **Power on the system**
3. The system will:
   - Initialize all components
   - Create experiment directory
   - Start running cycles with default parameters
   - Log data automatically

### Default Experiment Parameters
- **Basal Temperature**: 23°C
- **Heat Shock Temperature**: 32°C
- **Cycle Duration**: 200-400 minutes (random)
- **US Duration**: 30 seconds
- **Heat Duration**: 30 seconds
- **US Type**: Both LED and vibration
- **Correlation**: 1 (US precedes heat shock)

### Monitoring
- **OLED Display**: Shows real-time status
- **Serial Output**: Detailed logging information
- **SD Card**: All data automatically logged

## Troubleshooting

### Display Issues
- **Check files**: Ensure `ssd1306.py` and `oled_display.py` are uploaded
- **Check connections**: I2C pins 21 (SDA) and 22 (SCL)
- **Check I2C address**: Some displays use 0x3D instead of 0x3C

### Temperature Sensor Issues
- **Check SPI connections**: Pins 5, 12, 13, 14
- **Check RTD connections**: Ensure PT100 is properly connected
- **Check reference resistor**: Should be 430Ω

### Power Issues
- **Ensure adequate power supply**: ESP32 + peripherals need stable 3.3V/5V
- **Check MOSFET connections**: For heater and cooler control

## Data Analysis

Logged data can be analyzed using the included Python scripts:
- Raw JSON files contain detailed measurements
- Manifest files include checksums for data integrity
- Use `plot_data.py` for visualization (run on computer)

## Safety Features

- **Temperature limits**: Automatic shutdown if temperature exceeds safe ranges
- **Watchdog protection**: System resets if frozen
- **Error recovery**: Automatic retry on component failures
- **Data integrity**: Checksums verify logged data

## Support

For issues:
1. Run the test suite (`Tests.py`) to isolate problems
2. Check the SD card setup procedure
3. Verify all files are properly uploaded
4. Check hardware connections

## Contributing

Feel free to submit issues and enhancement requests!

## License

[Your chosen license]

## Author

[Your name/contact information]
