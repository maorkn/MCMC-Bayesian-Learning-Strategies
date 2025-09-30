# Microscope Mounted Chemostat

An experimental platform for studying habituation, valence reassignment, and threshold adaptation in single-celled organisms such as *Capsaspora owczarzaki*.

## Overview

The Microscope Mounted Chemostat (MCMC platform) is an automated experimental system designed to convert standard laboratory microscopes into sophisticated continuous culture reactors with real-time cell counting and adaptive control capabilities. Built on ESP32 microcontrollers with MicroPython firmware, the system enables long-term microbiology experiments with precise environmental control.

**Key Features:**
- **Four-pump coordination system** for continuous culture
- **Variable PWM flow control** (0-100% duty cycle)
- **Real-time cell counting** via Cellpose integration (optional)
- **Multiple operation modes:** Chemostat, Turbidostat, Morbidostat
- **Microscope integration** for longitudinal imaging
- **Under-lens chemical pulses** with reproducible transients
- **Closed-loop control** based on live segmentation

## Directory Structure

```
Microscope_mounted_chemostat/
├── Docs/                          # Documentation and specifications
│   ├── MCMC_Software_Spec.md     # Complete software architecture
│   ├── MCMC_Methods_Materials.tex # Methods from manuscript
│   ├── MCMClayout.drawio.png     # System diagram
│   └── parts_list.md             # Bill of materials (to be created)
├── Firmware/                      # ESP32 MicroPython code
│   ├── chemostat_controller.py   # Main controller with flow control
│   ├── local_pump_calibration.py # Pump calibration utility
│   ├── esp_c_controller.py       # Channel controller
│   ├── config.py                 # Configuration settings
│   ├── main.py                   # Entry point
│   ├── boot.py                   # Boot configuration
│   └── Hardware_modules/         # Hardware drivers
│       ├── pump_controller.py    # Pump control module
│       └── led_controller.py     # LED control module
└── Hardware/                      # Physical design files
    ├── PCB/                      # Printed circuit board designs
    │   └── *.gbr                 # Gerber files for manufacturing
    └── 3D_Models/                # 3D-printed components
        └── *.stl                 # STL files for printing
```

## Hardware Components

### ESP32-Based Control System
- **ESP32-WROOM-32** (240 MHz dual-core)
- **4x Peristaltic pumps** (PWM-controlled, 0-15 ml/h range)
- **LED illumination** with PWM intensity control
- **Power supply:** 12V for pumps, USB for ESP32

### Pump Configuration
1. **Media Pump (Pump 1):** Fresh medium delivery
2. **Signal Pump (Pump 2):** Independent signal/drug injection
3. **Chamber Pump (Pump 3):** Culture delivery (coordinated with media)
4. **Overflow Pump (Pump 4):** Waste removal (3× duration multiplier)

### Flow Coordination Algorithm
- **Synchronized operation:** Media and chamber pumps run simultaneously for T seconds
- **Extended overflow:** Overflow pump continues for 3T seconds
- **Independent signaling:** Signal pump operates on-demand
- **Non-blocking control:** Timer-based operation allows command acceptance during cycles

### GPIO Pin Assignments
```
Pump 1 (Media):     GPIO 25
Pump 2 (Signal):    GPIO 26
Pump 3 (Chamber):   GPIO 27
Pump 4 (Overflow):  GPIO 32
LED Array:          GPIO 33
Status LED:         GPIO 2  (Built-in)
```

## Key Capabilities

### 1. Flow Rate Control
- **PWM Resolution:** 13-bit (8,191 discrete levels)
- **Flow Range:** 0.1-15 ml/min per pump with ±5% accuracy
- **Calibration Model:** Linear relationship: Flow Rate (ml/min) = a × PWM% + b
- **Minimum Flow:** 0.05 ml/h achieved through duty cycling
- **Real-time Adjustment:** Flow rates modifiable during operation

### 2. Experimental Modes

#### Chemostat Mode
- Constant dilution rate with continuous medium supply
- Fixed flow rate independent of cell density
- For steady-state physiology studies

#### Turbidostat Mode
- Constant cell density maintenance through feedback control
- Cell density setpoint (default: 1×10⁶ cells/ml)
- Proportional dilution based on density deviation
- For growth rate measurements and evolutionary experiments

#### Morbidostat Mode (Planned)
- Adaptive drug concentration based on growth response
- Automated drug delivery via signal pump
- For antibiotic resistance evolution studies

### 3. Signal Injection Capabilities

The platform supports precise chemical perturbations:
- **Timed pulses:** User-defined duration and flow rate
- **Signal-pause sequences:** Inject → Mix → Pause protocol
- **Automatic triggering:** Based on cell density thresholds
- **Volume precision:** ±1% accuracy with 0.1 ml minimum delivery

Example signal-pause sequence:
```python
signal_pause(time_s=10, amount_gpm=5, mixing_time_s=30, pause_s=60)
# Injects signal for 10s at 5 g/min
# Mixes for 30s
# Pauses pumps 1&3 for 60s
```

### 4. Research Applications

**Habituation Studies:**
- Attenuation and re-sensitization to repeated non-predictive cues
- Response-decay rate measurements
- Under-lens cue pulses aligned to imaging

**Valence Reassignment:**
- Context-dependent cue value under controlled dilution
- Shifting perceived stimulus value (neutral → aversive/appetitive)

**Threshold Adaptation:**
- Shifts in response onset with changing resource background
- Dynamic chemical and thermal control in situ

**Population Dynamics:**
- Facultative aggregation in *Capsaspora owczarzaki*
- Information sharing via collective behaviors
- Tracking phenotypic exploration and assimilation

## Quick Start

### 1. Hardware Assembly
1. Print 3D components from `Hardware/3D_Models/`
2. Order PCBs using Gerber files from `Hardware/PCB/`
3. Assemble components according to parts list (see `Docs/parts_list.md`)
4. Connect pumps to GPIO pins as specified above

### 2. Firmware Installation
1. Install [Thonny IDE](https://thonny.org/) or similar MicroPython tool
2. Flash MicroPython to ESP32
3. Upload all files from `Firmware/` to ESP32
4. Edit `config.py` with your WiFi credentials (optional for MQTT)

### 3. Pump Calibration
Run the calibration utility to characterize your pumps:
```python
# On ESP32 via Thonny REPL
import local_pump_calibration
local_pump_calibration.run_calibration()
```

This creates CSV calibration files (e.g., `pump1_12V_calib.csv`) with flow-rate vs PWM relationships.

### 4. Basic Operation

**Local Control (No WiFi Required):**
```python
# In Thonny REPL
%Run chemostat_controller.py

# Run chemostat cycle: 15s at specified flow rates (g/min)
>>> chemostat(15, media_flow=10, chamber_flow=10, overflow_flow=30)

# Inject signal: 10s at 5 g/min
>>> signal(10, signal_flow=5)

# Check status
>>> status()

# Stop cycle
>>> stop()
```

**Continuous Operation:**
```python
# Start continuous run with specified flow rates
>>> start(media_flow=10, chamber_flow=10, overflow_flow=30)

# Stop when done
>>> stop()
```

## Advanced Features

### Cellpose Integration (Optional)
For automated turbidostat operation with real-time cell counting:

**Requirements:**
- Python 3.8+ on host computer
- USB microscope camera
- Cellpose library
- MQTT broker (mosquitto)

**Setup:**
```bash
# Install dependencies
pip install opencv-python paho-mqtt cellpose

# Start MQTT broker
mosquitto -v

# Run turbidostat controller
python cellpose_turbidostat.py
```

**Automated Operation:**
1. Camera captures frame every 5 seconds
2. Cellpose analyzes cell count
3. System adjusts dilution to maintain target density
4. Auto-triggers signal injection above threshold

### Signal-Pause Protocol
For experiments requiring chemical perturbation with controlled mixing:

```python
signal_pause(
    time_s=10,          # Signal injection duration
    amount_gpm=5,       # Signal flow rate (g/min)
    mixing_time_s=30,   # Mixing phase duration
    pause_s=60          # Pause duration (pumps 1&3 off)
)
```

**Sequence:**
1. **Inject:** Signal pump delivers compound
2. **Mix:** Media and chamber pumps mix the signal
3. **Pause:** All flow stops for incubation
4. **Resume:** Normal operation continues

### Data Logging
The system automatically logs experimental data:

**ESP32 Local Logging:**
- Creates daily rotating log files
- Records pump states, flow rates, timestamps
- Survives network interruptions

**Log Format:**
```csv
timestamp,pump_id,flow_gpm,duration_s,event_type
2024-01-15 14:30:15,1,10.0,60,CHEMOSTAT_START
2024-01-15 14:30:15,3,10.0,60,CHEMOSTAT_START
2024-01-15 14:30:15,4,30.0,180,OVERFLOW_START
```

## Experimental Design Considerations

### Flow Rate Selection
- **Dilution Rate (D):** D = Flow Rate / Volume
- **Typical Range:** 0.1-1.0 h⁻¹
- **Residence Time:** τ = 1/D
- **Volume:** Standard chamber ~5-10 ml

Example: For a 5 ml chamber with D=0.2 h⁻¹:
- Flow rate = 0.2 × 5 = 1 ml/h
- Residence time = 5 hours

### Signal Injection Timing
- **Minimum Volume:** 0.1 ml (for adequate mixing)
- **Typical Duration:** 5-30 seconds
- **Flow Rate:** 5-10 g/min for aqueous solutions
- **Avoid Washout:** Signal injection should be <10% of cycle time

### Overflow Management
- **3× Multiplier:** Ensures complete evacuation
- **Prevents Backflow:** Extended operation eliminates residual pressure
- **Maintains Volume:** Chamber volume stays constant

## Troubleshooting

### Pump Not Running
1. Check power supply (12V for pumps)
2. Verify GPIO connections
3. Run calibration to confirm pump response
4. Check for MOSFET failure

### Inconsistent Flow Rates
1. Re-run calibration
2. Check tubing for kinks or air bubbles
3. Verify pump orientation (inlet/outlet correct)
4. Clean pump heads if clogged

### WiFi Connection Issues
1. Verify SSID and password in `config.py`
2. Check network range
3. Use serial connection as fallback
4. Restart ESP32

### Cell Count Errors (Cellpose)
1. Adjust camera focus and lighting
2. Calibrate conversion factor in code
3. Check for segmentation artifacts
4. Consider manual counting for validation

## Safety and Maintenance

### Safety Considerations
- **Temperature Limits:** Firmware enforces 42°C cutoff
- **Emergency Stop:** Hardware and software kill switches
- **Current Limiting:** MOSFET circuits prevent pump damage
- **Network Loss:** System continues with last valid schedule

### Maintenance Schedule
- **Daily:** Check pump operation, clean chamber if needed
- **Weekly:** Inspect tubing for wear, verify calibration
- **Monthly:** Full system calibration, backup configuration
- **As Needed:** Replace pump heads, clean electrodes

## Citation

If you use this platform in your research, please cite:

```
Knafo, M., Casacuberta, E., Solé, R., & Ruiz-Trillo, I. (2025). 
Beyond Diffusion: Bayesian Learning Strategies in Single-Cell Life. 
Physical Review E (in preparation).
```

## Documentation

See `Docs/` directory for:
- **MCMC_Software_Spec.md:** Complete software architecture and MQTT topics
- **MCMC_Methods_Materials.tex:** Materials and methods from manuscript
- **MCMClayout.drawio.png:** System wiring diagram
- **parts_list.md:** Bill of materials for hardware assembly

## Support and Contributing

This is an open-source research platform. Contributions welcome!

**Issues:** Report bugs or request features via GitHub issues  
**Documentation:** Improvements to setup guides always appreciated  
**Hardware:** Share your modifications and calibrations  

## License

Open source for research and educational use. See LICENSE file for details.

## Acknowledgments

Developed for studying basal cognition and adaptive behaviors in single-celled organisms. Built on affordable, accessible components to enable widespread adoption in research labs.

---

**Ready for your next experiment!** 🧪🔬
