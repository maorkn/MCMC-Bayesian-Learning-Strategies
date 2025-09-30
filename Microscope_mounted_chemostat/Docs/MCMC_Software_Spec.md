# MCMC Microscope Chemostat – Software Specification

## 0 Goal
Create a full control‑and‑analysis stack that converts a standard microscope into an automated three‑channel chemostat platform.

* Drive **12 pumps**, **3 LED pairs**, and **TEC + PTC** via four Wi‑Fi‑connected ESP32 nodes.  
* Close the loop in four culture modes—**chemostat, turbidostat, morbidostat, aggregation‑stat**—using real‑time cell counts from Cellpose segmentation of microscope TIFFs.  
* Maintain sample temperature at a user‑defined set‑point within **±0.5 °C** with PID control and a hard safety cutoff at **42 °C**.  
* Offer a lightweight GUI for live plots, on‑the‑fly parameter edits, and an emergency kill switch.  
* Persist all raw and derived data in a structured run folder for reproducible experiments.

---

## 1 Hardware / Firmware Layout

| Node | Language | I/O | Responsibilities |
|------|----------|-----|------------------|
| **ESP‑T** (1×) | MicroPython | 2 PWM (TEC & PTC), 1 ADC (PT100) | PID @ 1 Hz, temperature logging to SD |
| **ESP‑C1/2/3** (3×) | MicroPython | 4 PWM pumps + 1 PWM LED each | Mode execution, SD fallback logging |

* All nodes connect over **802.11 n** to an MQTT broker running on the Mac host.  
* Each ESP keeps a 24 h rolling log on its onboard SD card (temperature for ESP‑T, channel stats for ESP‑C\*).

### ESP-T Implementation Details

**✅ COMPLETED** - The ESP-T temperature controller has been fully implemented with the following features:

* **Hardware Interface**: MAX31865 + PT100 sensor, PTC heater (GPIO 33), TEC cooler (GPIO 27)
* **PID Controller**: Asymmetric gains (heating: 1.0, cooling: 1.35) with anti-windup
* **Safety Systems**: 42°C hard cutoff, emergency kill switch, sensor fault detection
* **Communication**: MQTT over WiFi with automatic reconnection
* **Data Logging**: Daily rotating CSV logs on SD card with timestamp precision
* **Status Indication**: LED feedback for heating/cooling/idle/emergency states
* **Configuration**: Externalized settings in `config.py` for easy deployment

**File Structure**:
```
ESP_T_Module/
├── boot.py                 # ESP32 boot configuration
├── main.py                 # Entry point with error handling
├── config.py               # Configuration settings
├── esp_t_controller.py     # Main temperature controller
├── README.md               # Setup and operation guide
└── Temp_aux_scripts/
    ├── temp_controller.py  # PID controller with asymmetric dead-band
    ├── heater.py           # PTC heater PWM control
    ├── tec.py              # TEC cooler PWM control
    └── max31865.py         # PT100 sensor interface
```

---

## 2 Host Stack (Mac, Python‑only)

```text
mosquitto               # MQTT broker (no auth) - ✅ READY
controller/             # asyncio service - 🔄 PENDING
 ├─ calibration.py      # ml h⁻¹ ↔ PWM (±5 %)
 ├─ modes/
 │   ├─ chemostat.py    # constant D  (table TBD)
 │   ├─ turbidostat.py  # cell‑count set‑point (TBD)
 │   ├─ morbidostat.py  # user‑supplied drug rule
 │   └─ aggstat.py      # cluster‑size trigger
 ├─ imaging_watch.py    # watches IMG/ for *.tif
 │   └─ cellpose_wrap.py
gui.py                  # PyQt/PySide minimal GUI - 🔄 PENDING
```

*Cellpose* must fall back to CPU if no GPU is present; auto‑detect at runtime.

---

## 3 MQTT Contract

| Topic | JSON Payload | Description |
|-------|--------------|-------------|
| `cmd/chan{n}/pump{m}` | `{ "duty": 0‑100, "dur": s }` | Start pump *m* on channel *n* |
| `cmd/chan{n}/led` | `{ "duty": 0‑100, "dur": s }` | Drive LED pair on channel *n* |
| `cmd/temp` | `{ "setpoint": °C }` | Update PID target - **✅ IMPLEMENTED** |
| `cmd/kill` | `{}` | Immediate global PWM = 0 - **✅ IMPLEMENTED** |
| `stat/temp` | `{ "T": °C, "TEC_PWM": %, "PTC_PWM": %, "setpoint": °C, "mode": "string", "safety_shutdown": bool }` | 1 Hz temperature telemetry - **✅ IMPLEMENTED** |
| `stat/chan{n}` | `{ "pump_duty": [%, …], "led_duty": % }` | 1 Hz channel telemetry |

No authentication for now. One **`cmd/kill`** message halts all actuators.

### Temperature Control MQTT Examples

**Set temperature to 25°C**:
```bash
mosquitto_pub -h localhost -t "cmd/temp" -m '{"setpoint": 25.0}'
```

**Emergency stop**:
```bash
mosquitto_pub -h localhost -t "cmd/kill" -m '{}'
```

**Monitor temperature status**:
```bash
mosquitto_sub -h localhost -t "stat/temp"
# Example output:
# {"T": 24.85, "TEC_PWM": 0, "PTC_PWM": 12.3, "setpoint": 25.0, "mode": "Heating", "safety_shutdown": false}
```

---

## 4 Data Layout

```text
run_YYYYMMDD/
 ├── Temp/          temp_log_YYYYMMDD.csv - ✅ IMPLEMENTED
 ├── IMG/           ch{n}_YYYYMMDD_HHMMSS.tif
 │                  ch{n}_YYYYMMDD_HHMMSS_seg.npy
 └── CSV_AGG/       ch{n}_YYYYMMDD.csv   # timestamp, channel, cell_count,
                                         # mean_size, live_pct, dead_pct
```

* A new aggregation CSV opens every 24 h.  
* All raw TIFFs and logs are kept indefinitely.

### Temperature Log Format - ✅ IMPLEMENTED

ESP-T automatically creates daily rotating temperature logs:

**File**: `/sd/temp_log_YYYYMMDD.csv`  
**Columns**: `timestamp,temp_c,setpoint_c,heater_pwm,cooler_pwm,mode`  
**Example**:
```csv
timestamp,temp_c,setpoint_c,heater_pwm,cooler_pwm,mode
2024-06-12 14:30:15,23.45,23.0,15.2,0,Heating
2024-06-12 14:30:16,23.48,23.0,12.1,0,Heating
2024-06-12 14:30:17,23.52,23.0,0,0,Idle
```

---

## 5 Calibration & Maintenance

* **Pump auto‑calibration** – Host issues a stepped PWM profile, weighs output, fits a linear ml h⁻¹ ↔ PWM curve (≤ 5 % error). Constants sent to each ESP at run start.  
* **PID gains** – Set manually or by an optional auto‑tune wizard. **✅ ESP-T defaults: Kp=18.0, Ki=0.1, Kd=0.0**
* **Firmware & analysis versioning** – GitHub repo with semantic tags; CI pipeline TBD.  

### Temperature Calibration - ✅ IMPLEMENTED

The ESP-T system includes built-in calibration features:

* **Sensor Validation**: PT100 + MAX31865 provides ±0.01°C resolution with built-in fault detection
* **Asymmetric Control**: Separate heating (1.0) and cooling (1.35) gains for optimal performance
* **Dead-band Tuning**: 0.2°C heating threshold, 0.5°C cooling threshold
* **Safety Verification**: Hard 42°C cutoff with <1 second response time

**PID Tuning Parameters** (in `ESP_T_Module/config.py`):
```python
PID_KP = 18.0               # Proportional gain
PID_KI = 0.1                # Integral gain  
PID_KD = 0.0                # Derivative gain
HEATING_GAIN = 1.0          # Heating output scaling
COOLING_GAIN = 1.35         # Cooling output scaling
```

---

## 6 Implementation Status

### ✅ Completed Components

* **ESP-T Temperature Controller**: Full implementation with PID control, MQTT, safety systems, and SD logging
* **Temperature Sensor Interface**: MAX31865 + PT100 with fault detection and retry logic
* **Actuator Control**: PTC heater and TEC cooler with PWM control and asymmetric gains
* **Safety Systems**: 42°C hard cutoff, emergency kill switch, network loss handling
* **Data Logging**: 24-hour rotating CSV logs with configurable format
* **Configuration Management**: Externalized settings for easy deployment and tuning

### 🔄 Pending Implementation

* **ESP-C1/2/3 Controllers**: Pump and LED control nodes (similar architecture to ESP-T)
* **Host Python Controller**: asyncio service for coordinating all nodes
* **Mode Implementations**: Chemostat, turbidostat, morbidostat, aggregation-stat control algorithms
* **Cellpose Integration**: Real-time cell counting and segmentation
* **GUI Application**: PyQt/PySide interface for monitoring and control
* **Pump Calibration System**: Automated flow rate characterization

### 📋 Next Development Steps

1. **ESP-C Channel Controllers**: Adapt ESP-T architecture for pump/LED control
2. **Host MQTT Broker Setup**: Configure mosquitto on Mac with proper topics
3. **Python Controller Framework**: asyncio service with mode scheduling
4. **Basic GUI**: Temperature monitoring and setpoint control interface
5. **Pump Calibration**: Automated characterization and linearization
6. **Integration Testing**: Full system validation with all nodes

---

## 7 Open Items (to specify later)

* Chemostat dilution‑rate table.  
* Turbidostat set‑point and hysteresis band.  
* Morbidostat drug‑adjust algorithm.  
* Aggregation‑stat cluster‑size threshold.  
* ~~Final PID Kp/Ki/Kd values~~ - **✅ IMPLEMENTED** (Kp=18.0, Ki=0.1, Kd=0.0)
* Minimum GPU spec (if any).  
* Optional flow‑sensor integration.  
* Depth of CI/testing pipeline.
* ESP-C pump/LED controller pin assignments and protocols
* Host-side data aggregation and analysis pipeline
* GUI design and user workflow specifications
