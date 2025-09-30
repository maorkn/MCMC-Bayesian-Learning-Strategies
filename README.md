# Beyond Diffusion: Bayesian Learning Strategies in Single-Cell Life

**A comprehensive research framework for investigating predictive learning, memory formation, and Bayesian inference at the cellular level**

This repository contains the complete codebase, experimental platforms, and documentation for the paper **"Beyond Diffusion: Bayesian Learning Strategies in Single-Cell Life"**. The project demonstrates that single-celled organisms might exhibit sophisticated learning behaviors that extend beyond simple chemical diffusion, employing Bayesian-like inference strategies for environmental prediction and adaptive responses.

---

## Table of Contents

- [Overview](#overview)
- [Repository Structure](#repository-structure)
- [Research Components](#research-components)
  - [1. MBS Simulation](#1-mbs-simulation)
  - [2. Microscope-Mounted Chemostat](#2-microscope-mounted-chemostat)
  - [3. Smart Incubator](#3-smart-incubator)
  - [4. Manuscript](#4-manuscript)
- [Key Findings](#key-findings)
- [Getting Started](#getting-started)
- [Research Applications](#research-applications)
- [Hardware Platforms](#hardware-platforms)
- [Citation](#citation)
- [License](#license)
- [Contact](#contact)

---

## Overview

This research investigates whether single-celled organisms possess the capacity for **predictive learning** through Bayesian-like inference mechanisms that operate at sub-neural scales. The project combines:

1. **Agent-Based Simulations**: Computational models comparing Markovian-Bayesian Agents (MBAs) with memory-based learning against Blind Agents (BAs) that react only to current stimuli
2. **Experimental Validation**: Two custom-built automated platforms for long-term, high-precision biological experiments
3. **Theoretical Framework**: Mathematical models of cellular learning grounded in Bayesian inference and information theory

### Core Hypothesis

Single-celled organisms can:
- **Learn temporal associations** between environmental cues and subsequent stressors
- **Form cellular memories** that influence future behavioral responses
- **Predict environmental changes** using past experience encoded in molecular states
- **Optimize fitness** through anticipatory rather than purely reactive strategies

---

## Repository Structure

```
MCMC-Bayesian-Learning-Strategies/
├── README.md                           # This file
├── Manuscript/
│   └── Draft_18_09_25.tex             # LaTeX manuscript source
├── MBS_simulation/
│   └── MBA vs BA sim/                 # Agent-based simulation framework
│       ├── README.md                  # Simulation documentation
│       ├── mba_vs_ba_sim/            # Core simulation package
│       ├── wrappers/                  # Experiment wrappers
│       └── Fig_pub/                   # Publication figure generation
├── Microscope_mounted_chemostat/
│   ├── README.md                      # Platform documentation (400+ lines)
│   ├── Firmware/                      # ESP32 MicroPython code
│   ├── Hardware/                      # PCB Gerbers + 3D models
│   └── Docs/                          # Specifications & methods
└── Smart_incubator/
    ├── README.md                      # Platform documentation (400+ lines)
    ├── Firmware/                      # ESP32 MicroPython code (21 files)
    ├── Hardware/                      # PCB schematics + 3D models
    └── Docs/                          # Specifications, methods & analysis
```

---

## Research Components

### 1. MBS Simulation

**Location**: `MBS_simulation/MBA vs BA sim/`

**Purpose**: Agent-based simulations comparing learning strategies in evolutionary contexts.

#### Key Features

- **Markovian-Bayesian Agents (MBAs)**: Organisms that maintain memory of environmental patterns and use Bayesian inference to predict future conditions
- **Blind Agents (BAs)**: Memory-less organisms that respond only to immediate stimuli
- **Moran Process**: Population dynamics simulation with fitness-dependent reproduction
- **Multiple Experimental Paradigms**: Stress tests, genetic lock-in, continuous sweeps, topology scans

#### Agent Types

| Agent Type | Memory | Learning | Prediction | Fitness Strategy |
|------------|--------|----------|------------|------------------|
| MBA (Markovian-Bayesian) | ✓ | ✓ | ✓ | Anticipatory preparation |
| BA (Blind Agent) | ✗ | ✗ | ✗ | Reactive only |
| MBA-Gauss | ✓ | ✓ | ✓ | Gaussian environment model |

#### Simulation Capabilities

- **Population Evolution**: Track strategy dominance over thousands of generations
- **Fitness Landscapes**: Analyze preparatory response costs and benefits
- **Parameter Sweeps**: Systematic exploration of correlation, memory cost, environment variability
- **Statistical Analysis**: Permutation tests, effect size calculations, publication-ready visualizations

#### Quick Start

```bash
cd "MBS_simulation/MBA vs BA sim"
python -m wrappers.vanilla    # Basic MBA vs BA comparison
python -m wrappers.stress     # Stress test scenarios
```

**Documentation**: See `MBS_simulation/MBA vs BA sim/README.md` for detailed usage and `CLEANED_REPOSITORY_SUMMARY.md` for architecture overview.

---

### 2. Microscope-Mounted Chemostat

**Location**: `Microscope_mounted_chemostat/`

**Purpose**: Real-time microfluidic platform for studying habituation, valence reassignment, and threshold adaptation under microscopic observation.

#### Platform Capabilities

**Experimental Control:**
- **4-Pump Peristaltic System**: Independent control of 4 culture chambers
- **Variable Flow Rates**: 0-100% PWM control (13-bit resolution)
- **Programmable Protocols**: Chemostat, turbidostat, morbidostat modes
- **Temporal Precision**: Microsecond-level timing for stimulus delivery
- **Long-Term Stability**: Continuous operation for days to weeks

**Operational Modes:**
1. **Chemostat Mode**: Constant dilution rate, steady-state growth
2. **Turbidostat Mode**: Optical density (cellpose) feedback control
3. **Morbidostat Mode**: Dynamic drug concentration adjustment
4. **Custom Protocols**: User-defined temporal sequences

**Real-Time Integration:**
- **Microscope Compatibility**: Mounts directly on inverted microscopes
- **Cellpose Integration**: Optional AI-based cell counting
- **MQTT Communication**: Remote monitoring and control
- **Live Imaging**: Synchronized with image acquisition systems

#### Hardware Specifications

| Component | Specification | Function |
|-----------|--------------|----------|
| Microcontroller | ESP32-WROOM-32 (240 MHz dual-core) | System control |
| Pumps | 4× Peristaltic pumps | Media delivery (intake, waste, 2× drugs) |
| LED Control | PWM-controlled illumination | Growth chamber lighting |
| Communication | WiFi (MQTT protocol) | Remote operation |
| Cost | $250-$840 | Depending on pump choice |

#### Research Applications

- **Habituation Studies**: Long-term adaptation to repeated chemical stressors
- **Valence Reassignment**: Testing whether organisms reassign meaning to previously neutral cues
- **Threshold Adaptation**: Investigating changes in stress response thresholds
- **Chemotaxis Experiments**: Studying gradient-following behavior
- **Drug Resistance Evolution**: Real-time observation of resistance emergence

#### Quick Start

```bash
# 1. Upload firmware to ESP32
cd Microscope_mounted_chemostat/Firmware
# Use Thonny or ampy to upload *.py files

# 2. Calibrate pumps
python local_pump_calibration.py

# 3. Run experiment
python chemostat_controller.py
```

**Full Documentation**: See `Microscope_mounted_chemostat/README.md` (400+ lines) and `Docs/parts_list.md` for complete BOM.

---

### 3. Smart Incubator

**Location**: `Smart_incubator/`

**Purpose**: Autonomous platform for testing predictive learning through controlled temporal associations between environmental cues and thermal stressors.

#### Platform Capabilities

**Thermal Control System:**
- **Dual Actuators**: PTC heater + TEC1 Peltier cooler
- **PID Regulation**: Custom-tuned controller (Kp=6.0, Ki=0.02, Kd=1.5)
- **Temperature Range**: 15-40°C (software limited for biological safety)
- **Precision**: ±0.5°C at basal (23°C), ±0.8°C during heat shock (32°C)
- **Rapid Transitions**: 2-3 min heating, 5-8 min cooling

**Multi-Modal Stimulus Delivery:**
- **Optical (LED)**: High-brightness white LED with 16-bit PWM control
- **Mechanical (Vibration)**: Programmable vibration motor with pulsing patterns
- **Combined Modes**: Independent or simultaneous multi-modal delivery
- **Temporal Precision**: Microsecond-level timing accuracy

**Experimental Protocol Framework:**

| Correlation Mode | Description | US-HS Timing | Measured Δt | Interpretation |
|------------------|-------------|--------------|-------------|----------------|
| 0 | Non-Temporal Control | Random | -58.1 ± 113.9 min | No predictive value |
| 1 | Temporal Predictive | US precedes HS | 30.0 ± 0.3 min | Perfect correlation |
| 2 | Temporal Post-stress | US follows HS | Variable | Reversed association |
| 3 | Testing Mode | Short cycle | 0.5 min | Hardware validation |

**Data Management:**
- **10-Second Sampling**: Complete system state snapshots
- **SD Card Logging**: FAT32 with SHA-256 checksums
- **Structured Hierarchy**: Experiment directories with metadata
- **Data Integrity**: Cryptographic verification and manifest tracking

**Safety Features:**
- **Temperature Failsafe**: Stuck sensor detection and overheat protection
- **Automated Recovery**: Sensor reinitialization and error resilience
- **Progressive Protection**: Graduated intervention based on severity
- **Memory Management**: Periodic garbage collection and heap monitoring

#### Hardware Specifications

| Component | Specification | Function |
|-----------|--------------|----------|
| Microcontroller | ESP32-WROOM-32 (240 MHz dual-core) | System orchestration |
| Temperature Sensor | MAX31865 + PT100 RTD | Precision measurement |
| Heater | PTC element (5-15W) | Warming actuator |
| Cooler | TEC1 Peltier module | Cooling actuator |
| Stimuli | LED + vibration motor | Multi-modal cues |
| Display | SSD1306 128×64 OLED | Real-time status |
| Storage | MicroSD card (4-32 GB) | Data logging |
| Cost | $180-$320 | Depending on configuration |

#### Research Applications

- **Predictive Learning**: Testing temporal association between cues and stress
- **Memory Formation**: Examining cellular response persistence
- **Phenotypic Plasticity**: Multi-timescale environmental adaptation
- **Pre-Neural Learning**: Investigating sub-neural inference mechanisms
- **Complex Protocols**: Custom landscape execution with multi-parameter control

#### Quick Start

```bash
# 1. Format SD card as DOS_FAT_32 with MBR
diskutil eraseDisk MS-DOS INCUBATOR MBR /dev/diskX

# 2. Upload firmware to ESP32
cd Smart_incubator/Firmware
# Use Thonny or ampy to upload *.py files

# 3. Power on - system auto-initializes and starts cycles
# Monitor via OLED display or serial console
```

**Full Documentation**: See `Smart_incubator/README.md` (400+ lines) and `Docs/parts_list.md` for complete BOM.


## Getting Started

### Prerequisites

**For Simulations:**
```bash
# Python 3.8+ with scientific computing stack
pip install numpy scipy matplotlib pandas seaborn
```

**For Hardware Platforms:**
- ESP32 development boards
- MicroPython firmware (v1.24.1+)
- Electronic components (see respective parts lists)
- Basic electronics assembly skills

### Installation

**Clone Repository:**
```bash
git clone https://github.com/your-repo/MCMC-Bayesian-Learning-Strategies.git
cd MCMC-Bayesian-Learning-Strategies
```

**Run Simulations:**
```bash
cd "MBS_simulation/MBA vs BA sim"
python -m wrappers.vanilla
```

**Build Hardware:**
1. Review platform-specific README files for detailed instructions
2. Order components from parts_list.md BOMs
3. Follow assembly guides in respective Docs/ directories
4. Upload firmware and configure for your experiments

---

## Hardware Platforms

### Comparison Matrix

| Feature | Microscope-Mounted Chemostat | Smart Incubator |
|---------|------------------------------|-----------------|
| **Primary Use** | Real-time microscopy + microfluidics | Autonomous thermal learning experiments |
| **Control Variables** | Flow rates, drug concentrations, LED | Temperature, LED, vibration |
| **Observation** | Live imaging (Cellpose compatible) | End-point sampling + logging |
| **Chambers** | 4 independent cultures | 1 main chamber |
| **Duration** | Hours to days | Weeks to months |
| **Sampling** | Continuous video + OD sensing | 10-second data snapshots |
| **Correlation Modes** | Chemical gradients | 4 temporal correlation modes |
| **Cost** | $250-$840 | $180-$320 |
| **Build Difficulty** | Moderate (fluidics + optics) | Moderate (thermal + electronics) |

### Common Features

Both platforms share:
- **ESP32-based control** with MicroPython
- **PWM actuation** for precise analog control
- **SD card data logging** with integrity verification
- **Real-time monitoring** (MQTT/OLED display)
- **Safety systems** (sensor recovery, failsafes)
- **Modular design** for easy modification
- **Open-source firmware** and hardware designs

---

## Citation

If you use this work in your research, please cite:

```bibtex
@article{your_paper_2025,
  title={Beyond Diffusion: Bayesian Learning Strategies in Single-Cell Life},
  author={[Authors]},
  journal={[Journal]},
  year={2025},
  doi={[DOI]}
}
```

---

## License

[Specify license - e.g., MIT, GPL, CC-BY, etc.]

This repository contains:
- **Software**: Simulation code and firmware (specify license)
- **Hardware**: PCB designs and 3D models (specify license, e.g., CERN-OHL)
- **Documentation**: Guides and specifications (specify license, e.g., CC-BY-4.0)

---

## Contact

**Institution**: [IBE, CSIC Barcelona, MCG Lab ]  

### Contributing

We welcome contributions! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request with clear description

For hardware modifications, include:
- Updated BOMs
- Revised schematics/PCB files
- Testing notes and validation data

### Support

- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Use GitHub Discussions for questions
- **Documentation**: Refer to platform-specific README files
- **Hardware**: See respective parts_list.md for component sourcing


---

## Project Status

**Current Version**: 1.0 (September 2025)

**Status**: 
- ✅ Simulations: Complete and validated
- ✅ Microscope-Mounted Chemostat: Built and operational
- ✅ Smart Incubator: Built and operational
- 🔄 Manuscript: Under review

**Roadmap**:
- [ ] Extended simulation parameter sweeps
- [ ] Additional experimental validation datasets
- [ ] Protocol library expansion
- [ ] Community hardware builds and feedback

---

**Repository Structure Last Updated**: September 30, 2025  
**Maintainers**: [Maor Knafo]  
**For questions or collaboration inquiries**: [Contact info]
