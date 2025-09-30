### Smart Incubator Platform

The Smart Incubator is an automated experimental platform designed to subject cell cultures to complex, long-term environmental protocols with precise temporal control. The system enables the study of phenotypic plasticity, predictive learning, and memory in microorganisms through controlled delivery of thermal stresses and sensory cues. Built on a modular MicroPython framework running on ESP32 hardware, the platform supports fully autonomous, multi-week experiments with comprehensive data logging and real-time monitoring capabilities.

The incubator's design philosophy centers on creating a controllable "learning environment" where organisms experience predictable or unpredictable relationships between environmental cues (unconditional stimuli) and subsequent stressors (heat shocks). This approach allows researchers to test hypotheses about biological prediction, memory formation, and adaptive plasticity at the cellular level, providing insights into the evolutionary origins of learning behaviors that preceded neural systems.

#### Hardware and System Architecture

The platform is built around an ESP32-WROOM-32 microcontroller (240 MHz dual-core) that orchestrates all subsystems through a multi-layered software architecture. The system design emphasizes modularity, error resilience, and long-term stability, with comprehensive hardware safety features and automated recovery mechanisms.

**Table 1: Smart Incubator Hardware Components and GPIO Pinout** 

| Component | Interface | Pin(s) & Function | Specifications |
| ----- | ----- | ----- | ----- |
| Control Unit | — | ESP32-WROOM-32 | 240 MHz dual-core, 520 KB SRAM |
| Temperature Sensing | SPI (VSPI) | MAX31865 + PT100 RTD | SCK 18, MOSI 23, MISO 19, CS 5 |
| Thermal Actuators | PWM (1 kHz) | PTC Heater | Pin 33, MOSFET-controlled, 0-100% duty |
|  | PWM (1 kHz) | TEC1 Peltier Cooler | Pin 27, MOSFET-controlled, 0-100% duty |
| Unconditional Stimuli | PWM (1 kHz) | White LED Module | Pin 25, 0-100% intensity control |
|  | PWM (1 kHz) | Vibration Motor | Pin 16, pulsed operation (20s on/60s off) |
| Data Storage | SPI (HSPI) | MicroSD Card Module | SCK 14, MOSI 13, MISO 12, CS 15, FAT32 |
| User Interface | I2C | SSD1306 128×64 OLED | SCL 22, SDA 21, real-time status display |

##### Software Architecture

The system employs a multi-layered software architecture that separates high-level experimental logic from low-level hardware control, ensuring modularity, maintainability, and operational resilience:

**Core System Layers:**
1. **Hardware Abstraction Layer:** Individual driver modules for each component (MAX31865, PWM controllers, SD card, OLED display)
2. **Control Layer:** PID temperature controller, unconditional stimulus (US) controller with configurable timing patterns
3. **Experiment Logic Layer:** Cycle management, correlation mode implementation, randomization algorithms
4. **Data Management Layer:** Real-time logging, data integrity verification, manifest generation with SHA-256 checksums
5. **Safety and Recovery Layer:** Automated initialization with retry logic (up to 5 attempts), comprehensive error handling, periodic memory cleanup

**Key Software Features:**
- **Thread-safe SD card operations** with mutex locks for concurrent access
- **Robust initialization** with exponential backoff retry mechanisms
- **Memory management** via periodic garbage collection (every 5 minutes during operation)
- **Fault tolerance** with sensor noise filtering and temperature validation
- **Real-time monitoring** with OLED status updates and periodic system snapshots
- **Web server interface** (optional) for remote parameter adjustment and monitoring

#### Thermal and Stimulus Control System

##### Thermal Regulation System

The thermal control system employs a sophisticated dual-actuator design managed by a custom PID controller optimized for biological temperature ranges. The system provides both heating and cooling capabilities to achieve rapid, precise temperature transitions essential for learning paradigms.

**PID Controller Configuration:**
- **Proportional gain (Kp):** 6.0 - provides rapid response to temperature deviations
- **Integral gain (Ki):** 0.02 - eliminates steady-state error with minimal overshoot
- **Derivative gain (Kd):** 1.5 - dampens oscillations and improves stability
- **Control deadband:** ±0.5°C around setpoint to prevent actuator chatter
- **Anti-windup mechanism:** Prevents integral term saturation during large setpoint changes

**Dual-Actuator Control:**
- **PTC Heater (Pin 33):** MOSFET-controlled PWM (0-100%), provides heating from ambient to 40°C
- **TEC1 Peltier Cooler (Pin 27):** MOSFET-controlled PWM with safety cycling (3 min on/3 min off max), enables cooling below ambient temperature

**Temperature Sensing and Noise Filtering:**
The MAX31865 RTD-to-digital converter interfaces with a PT100 platinum resistance temperature detector via SPI at 250 kHz for noise reduction. Advanced filtering algorithms ensure measurement reliability:

- **Multi-sample median filtering:** Each reading is the median of 5 rapid successive samples
- **Change-rate limiting:** Readings deviating >5°C from previous measurement are rejected
- **Fault detection:** Automatic detection and reporting of RTD faults (opens, shorts, voltage issues)
- **Retry logic:** Up to 3 attempts per reading with 50ms delays between retries

**Thermal Performance:**
- **Basal temperature (23°C):** Maintains ±0.5°C accuracy during steady-state operation
- **Heat shock temperature (32°C):** Achieves target within 2-3 minutes, maintains ±0.8°C accuracy
- **Cooling performance:** Can reduce temperature from 32°C to 23°C in approximately 5-8 minutes
- **Temperature range:** Operational from 15°C to 40°C (software limited for biological safety)

##### Unconditional Stimulus (US) Delivery System

The platform delivers precisely timed unconditional stimuli through two independent modalities, allowing for complex multi-modal cueing paradigms or isolated stimulus presentation.

**Optical Stimulation (LED Module - Pin 25):**
- **Configuration:** High-brightness white LED with PWM intensity control
- **Intensity range:** 0-100% via 16-bit PWM resolution (65,535 discrete levels)
- **Default intensity:** 25% (configurable via software)
- **Response characteristics:** Instantaneous on/off switching, uniform illumination
- **Wavelength:** Broad spectrum white light (380-700 nm)

**Mechanical Stimulation (Vibration Motor - Pin 16):**
- **Configuration:** Miniature vibration motor with PWM amplitude control
- **Intensity range:** 0-100% via 16-bit PWM resolution
- **Default intensity:** 100% (configurable via software)
- **Pulsing pattern:** Programmable on/off intervals (default: 20s on, 60s off)
- **Safety features:** Thermal protection via duty cycling to prevent motor overheating
- **Frequency:** Motor-dependent (typically 100-200 Hz resonant frequency)

**US Controller Features:**
- **Independent control:** Each modality can be activated separately or simultaneously
- **Temporal precision:** Microsecond-level timing accuracy for stimulus onset/offset
- **Dynamic intensity adjustment:** Real-time modification of stimulus parameters
- **Pattern generation:** Supports complex temporal patterns including bursts, ramps, and irregular sequences
- **State tracking:** Maintains accurate records of stimulus timing for data correlation

**Multi-Modal Stimulus Modes:**
- **"LED":** Optical stimulation only
- **"VIB":** Mechanical stimulation only  
- **"BOTH":** Simultaneous optical and mechanical stimulation
- **"NONE":** No stimulus delivery (control condition)

### Experimental Protocol Framework

The Smart Incubator implements a sophisticated experimental paradigm designed to test predictive learning and memory formation in microorganisms through controlled temporal relationships between environmental cues and thermal stressors.

#### Cycle-Based Experimental Design

**Randomized Cycle Architecture:**
Each experiment consists of multiple discrete cycles with randomized durations to prevent temporal entrainment and habituation. This design ensures that organisms cannot rely on fixed timing patterns and must instead learn to associate cues with outcomes.

- **Cycle duration:** Randomized between configurable bounds (default: 200-400 minutes)
- **Phase structure:** Each cycle contains distinct basal and heat shock phases
- **Inter-cycle intervals:** Brief recovery periods (2-5 minutes) with system cleanup
- **Long-term stability:** Experiments can run continuously for weeks without intervention

**Thermal Protocol:**
- **Basal phase:** Extended period at optimal growth temperature (default: 23°C)
- **Heat shock phase:** Brief thermal stress period (default: 32°C for 30 minutes)
- **Temperature transitions:** Rapid heating (2-3 min) and controlled cooling (5-8 min)
- **Biological relevance:** Heat shock temperatures chosen to induce stress response without lethality

#### Correlation Modes: Testing Predictive Relationships

The system's key innovation lies in its ability to create either predictable or unpredictable relationships between sensory cues (US) and thermal stressors (HS), enabling direct tests of biological prediction and learning.

**Correlation Mode 0 (Non-Temporal Control):**
- **US timing:** Randomly distributed throughout the basal phase
- **HS timing:** Independently randomized within the cycle
- **Predictive value:** Zero correlation between cue and stressor
- **Measured stimulus-stress delta:** -58.1 ± 113.9 minutes (highly variable)
- **Biological interpretation:** Control condition testing non-associative responses

**Correlation Mode 1 (Temporal Predictive):**
- **US timing:** Fixed interval before heat shock onset (default: 30 minutes)
- **HS timing:** Consistent relative to US presentation
- **Predictive value:** Perfect correlation enabling prediction
- **Measured stimulus-stress delta:** 30.0 ± 0.3 minutes (highly precise)
- **Biological interpretation:** Tests capacity for predictive learning and preparation

#### Advanced Protocol Capabilities

**Landscape Execution Mode:**
The system supports complex, pre-programmed experimental landscapes loaded from CSV files, enabling:
- **Multi-parameter protocols:** Simultaneous control of temperature, LED, and vibration over time
- **Complex waveforms:** Sinusoidal, ramp, step, and custom temperature profiles
- **Synchronized stimuli:** Precise coordination of thermal and sensory modalities
- **Long-term experiments:** Automated execution of protocols lasting days to weeks

**Adaptive Parameter Control:**
- **Real-time adjustment:** Parameters can be modified during ongoing experiments
- **Web interface:** Remote monitoring and control capabilities
- **Fail-safe mechanisms:** Automatic parameter bounds checking and safety cutoffs
- **State preservation:** System maintains experimental state through power cycles

### Data Acquisition and Integrity Management

The Smart Incubator implements a comprehensive data logging system designed for high-resolution temporal tracking of all experimental parameters with robust integrity verification mechanisms.

#### High-Resolution Data Logging

**Temporal Resolution:**
- **Sampling rate:** Complete system snapshot every 10 seconds
- **Logging precision:** Microsecond-accurate timestamps for all events
- **Data synchronization:** All measurements time-locked to system clock
- **Buffer management:** Thread-safe data queuing with overflow protection

**Comprehensive Parameter Tracking:**
Each data snapshot captures the complete system state:

```json
{
  "timestamp": 18883,           // Unix timestamp (seconds)
  "temp": 31.63,               // Current temperature (°C)
  "set_temp": 23.0,            // Target temperature (°C)
  "power": -89.55,             // PID controller output (%)
  "mode": "Cooling",           // Controller state
  "tec_state": "On",           // Cooler activation status
  "us_active": 0,              // Stimulus delivery state
  "elapsed_minutes": 0.17,     // Time within current cycle
  "cycle_length": 242,         // Total cycle duration (minutes)
  "phase": "basal",            // Current experimental phase
  "cycle_num": 2,              // Sequential cycle identifier
  "experiment_id": "0_0",      // Unique experiment identifier
  "firmware": "1.0.0"          // System version tracking
}
```

#### Data Organization and File Structure

**Hierarchical Directory Structure:**
```
data/
├── [EXPERIMENT_ID]/          // Format: DDMMYYYY_correlation
│   ├── meta.json            // Experiment parameters and metadata
│   ├── manifest.json        // Data integrity verification
│   ├── cycle_[N]_[TIMESTAMP].json    // Individual data snapshots
│   └── cycle_[N]_summary.json       // Cycle statistics and summaries
```

**File Type Specifications:**

**Metadata Files (`meta.json`):**
- Complete experimental parameter set
- System configuration and hardware details
- Firmware version and initialization timestamp
- Correlation mode and protocol specifications

**Data Snapshots (`cycle_[N]_[TIMESTAMP].json`):**
- Real-time system measurements at 10-second intervals
- Complete thermal, stimulus, and timing information
- Error flags and diagnostic data
- Memory usage and system health metrics

**Cycle Summaries (`cycle_[N]_summary.json`):**
- Statistical analysis of cycle performance
- Temperature stability metrics (min/max/mean/std)
- Stimulus delivery statistics and timing accuracy
- Error counts and fault reports
- Cycle duration and phase transition timing

#### Data Integrity and Verification

**Cryptographic Integrity Checking:**
- **SHA-256 checksums:** Generated for all data files in real-time
- **Manifest tracking:** Central registry of all files with verification hashes
- **Corruption detection:** Automatic verification on system startup and data access
- **Recovery mechanisms:** Damaged file detection with automated alerts

**Robust Storage Management:**
- **FAT32 compatibility:** Cross-platform file system support
- **Atomic writes:** Ensures data consistency during power interruptions
- **Space monitoring:** Automatic disk usage tracking with low-space warnings
- **Backup strategies:** Support for redundant storage systems

**Data Validation:**
- **Range checking:** All sensor readings validated against physical limits
- **Temporal consistency:** Timestamp sequence verification
- **Cross-parameter validation:** Logical consistency checks between related measurements
- **Missing data detection:** Automatic identification and flagging of data gaps

#### Analysis and Export Capabilities

**Built-in Analysis Tools:**
- **Statistical summaries:** Automated calculation of experimental metrics
- **Correlation analysis:** Quantitative assessment of stimulus-response relationships
- **Performance visualization:** Real-time plotting of key parameters
- **Export utilities:** JSON, CSV, and binary format support for external analysis

**Research Integration:**
- **Standard formats:** Compatible with common scientific data analysis platforms
- **Metadata preservation:** Complete provenance tracking for reproducibility
- **Version control:** Built-in experiment versioning and comparison tools
- **Quality metrics:** Automated assessment of data completeness and reliability
