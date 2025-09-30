# MCMC ESP-C Channel Controller

ESP32-based three-channel chemostat pump and LED controller for the MCMC (Microscope Chemostat) platform.

## 🏗️ Hardware Requirements

### ESP32 Board
- **ESP32 DevKit** (or compatible)
- **Minimum Flash**: 4MB
- **Memory**: 520KB RAM

### Peripherals
- **4x Peristaltic Pumps** (PWM-controlled)
- **1x LED Array** (PWM-controlled)
- **1x Status LED** (visual feedback)
- **1x MicroSD Card** (data logging)
- **WiFi Network** (2.4GHz)

### GPIO Pin Assignments (Default)
```
Pump 1:     GPIO 25
Pump 2:     GPIO 26
Pump 3:     GPIO 27
Pump 4:     GPIO 32
LED:        GPIO 33
Status LED: GPIO 2
SD Card:    SPI (see config.py)
```

## 🚀 Quick Start

### 1. Configure Channel
Edit `config.py` for your specific channel:
```python
CHANNEL_ID = 1  # Change to 2 or 3 for other channels
```

### 2. Network Setup
```python
WIFI_SSID = "YourNetworkName"
WIFI_PASSWORD = "YourPassword"
MQTT_BROKER = "192.168.1.100"
```

### 3. Deploy to ESP32
```bash
# Copy all files to ESP32
ampy put config.py
ampy put boot.py
ampy put main.py
ampy put esp_c_controller.py
ampy put Hardware_modules/
```

### 4. Monitor Operation
```bash
# Watch serial output
screen /dev/ttyUSB0 115200
```

## 📊 System Architecture

### Control Loop (1Hz)
```
WiFi Check → MQTT Process → Pump Updates → LED Updates → Status Report → Logging
```

### Command Queuing
- **FIFO Queue**: Up to 5 commands per pump
- **Duration Limit**: 1 hour max per command
- **Real-time Volume**: Continuous tracking with calibration

### Safety Systems
- **Hardware Watchdog**: 8-second timeout
- **MQTT Timeout**: 60-second failsafe with LED indication
- **Emergency Stop**: Immediate shutdown on `cmd/kill`
- **Parameter Validation**: Duty (0-100%), duration (0-3600s)

## 🔧 Enhanced Features

### PWM Compatibility
```python
# Handles both 10-bit and 16-bit MicroPython builds
if hasattr(self.pwm, "duty_u16"):
    self.pwm.duty_u16(pwm_val << 6)  # 16-bit
else:
    self.pwm.duty(pwm_val)           # 10-bit
```

### Calibration Management
```python
# Direct float storage for performance
ml_per_hour = (self.calib_a * duty_percent) + self.calib_b

# Zero coefficient warning
if self.calib_a == 0.0:
    print("WARNING: Pump may be stalled")
```

### Volume Tracking Precision
```python
# Proper tick handling prevents wraparound
elapsed_ms = utime.ticks_diff(utime.ticks_ms(), self.start_time)
volume = self.calculate_volume(duty, elapsed_ms / 1000.0)
```

## 📡 MQTT Protocol

### Command Topics
```
cmd/chan{N}/pump{1-4}   - Individual pump control
cmd/chan{N}/led         - LED control
cmd/chan{N}/calibrate   - Update calibration coefficients
cmd/chan{N}/flush       - Clear command queues
cmd/chan{N}/reset_volumes - Reset volume counters
cmd/kill                - Emergency stop (all channels)
```

### Status Topic
```
stat/chan{N}            - Channel status and telemetry
```

### Command Examples

#### Pump Control
```json
# cmd/chan1/pump2
{
  "duty": 75.5,
  "dur": 300
}
```

#### LED Control
```json
# cmd/chan1/led
{
  "duty": 50.0,
  "dur": 60
}
```

#### Calibration Update
```json
# cmd/chan1/calibrate
{
  "pump1": {"a": 2.5, "b": 0.1},
  "pump2": {"a": 2.7, "b": -0.05}
}
```

#### Queue Management
```json
# cmd/chan1/flush (specific pumps)
{
  "pumps": [1, 3]
}

# cmd/chan1/flush (all pumps)
{}
```

#### Volume Reset
```json
# cmd/chan1/reset_volumes (specific pumps)
{
  "pumps": [2, 4]
}

# cmd/chan1/reset_volumes (all pumps)
{}
```

### Status Response
```json
{
  "pump_duty": [0, 75.5, 0, 0],
  "led_duty": 50.0,
  "queued": 3,
  "total_volume": [0.0, 45.2, 0.0, 0.0],
  "active_pump": 2,
  "uptime": 3600,
  "mqtt_timeout": false,
  "emergency_stop": false
}
```

## 💾 Data Logging

### CSV Format
```
Timestamp,Pump,Duty,Duration,LED_Duty,Volume,CommandID,Event
2024-01-15 14:30:15,2,75.5,300,0,45.234,cmd_1_12345,PUMP_CMD
2024-01-15 14:35:20,0,0,0,50.0,0.0,cmd_1_12380,LED_CMD
```

### Log Rotation
- **Daily Rotation**: New file each day
- **Filename Format**: `chan{N}_log_YYYYMMDD.csv`
- **Auto-header**: CSV header added to new files
- **Hot Insert**: SD card detection after boot

## ⚠️ Safety Features

### Emergency Stop Sequence
1. **Immediate PWM shutdown** for all pumps/LED
2. **Queue clearing** (all pending commands)
3. **PWM deinit** for clean restart
4. **Fast LED blink** (emergency indication)
5. **MQTT notification** via status report

### MQTT Timeout Handling
```python
# 60-second timeout detection
if utime.ticks_diff(now, last_mqtt) > 60000:
    emergency_shutdown()
    led_mode = "timeout"  # Fast blink indication
```

### Parameter Validation
```python
# Early rejection of invalid commands
if duty_percent == 0 or duration_sec == 0:
    return False  # Don't waste queue slots

# Strict bounds checking  
duty = max(0, min(100, duty_percent))
duration = max(0, min(3600, duration_sec))
```

## 🛠️ Advanced Configuration

### Debug Mode
```python
# Enable verbose logging
pump_bank = PumpBank(PUMP_PINS, calibrations, debug=True)
led_controller = QueuedLEDController(LED_PIN, debug=True)
```

### PWM Frequency Adjustment
```python
# Quieter operation at higher frequency
pump.set_frequency(2000)  # 2kHz instead of 1kHz
```

### Calibration Validation
```python
# Check for stalled pumps
if pump.calib_a == 0.0:
    print("WARNING: Zero flow coefficient detected")
```

## 📈 Performance Optimizations

### Memory Efficiency
- **Direct float storage**: Avoid dict lookups in control loops
- **Garbage collection**: Managed collection timing
- **String interning**: Reuse common strings

### Timing Precision
- **Tick arithmetic**: Proper wraparound handling
- **Async control**: Non-blocking operation
- **Hardware watchdog**: System reliability

### Network Resilience
- **Exponential backoff**: WiFi reconnection (1s → 60s)
- **MQTT keepalive**: 30-second heartbeat
- **QoS=1**: Critical message delivery

## 🐛 Troubleshooting

### Common Issues

#### WiFi Connection Failed
```
[WiFi] Connection failed! Next retry in 2s
```
**Solution**: Check SSID/password, signal strength

#### MQTT Timeout
```
[MQTT] Timeout detected - emergency shutdown
```
**Solution**: Check broker connectivity, firewall rules

#### SD Card Error
```
[SD] Initialization failed: no SD card
```
**Solution**: Insert formatted SD card, check wiring

#### Queue Full
```
[Pump1] Command rejected (queue full)
```
**Solution**: Reduce command rate or flush queue

### LED Status Indicators

| Pattern | Meaning |
|---------|---------|
| Solid ON | Normal operation |
| Slow blink (1Hz) | WiFi/MQTT connecting |
| Fast blink (5Hz) | MQTT timeout |
| Very fast blink (10Hz) | Emergency stop |

### Serial Debugging
```python
# Enable debug output for all components
CONTROL_DEBUG = True
```

## 🔧 Hardware Assembly

### Pump Connections
```
ESP32 GPIO → Driver Board → Pump
   25    →    PWM1      →  Pump 1
   26    →    PWM2      →  Pump 2  
   27    →    PWM3      →  Pump 3
   32    →    PWM4      →  Pump 4
```

### Power Requirements
- **ESP32**: 5V/1A via USB or VIN
- **Pumps**: 12V/2A (external supply)
- **LED**: 12V/500mA (shared with pumps)

### Recommended Driver
- **Motor Driver**: TB6612FNG or L298N
- **PWM Input**: 3.3V compatible
- **Frequency**: 1-3 kHz optimal

## 📚 API Reference

### PumpController Class
```python
pump = PumpController(pin=25, pump_id=1, calibration={"a": 2.5, "b": 0.0})

# Control methods
pump.start(duty_percent, duration_sec)
pump.stop()
pump.set_duty(duty_percent)
pump.set_frequency(frequency)

# Calibration
pump.set_calibration(a, b)
pump.get_calibration()

# Status
status = pump.get_status()
volume_rate = pump.get_current_volume_rate()

# Safety
pump.emergency_stop()
pump.reset_volume()
```

### PumpBank Class
```python
bank = PumpBank(pump_pins=[25,26,27,32], calibrations=None, debug=False)

# Command queuing
bank.queue_command(pump_id, duty, duration, command_id, max_queue=5)
bank.flush_queue(pump_id)
bank.flush_all_queues()

# Management
bank.update_all()
bank.get_all_status()
bank.emergency_stop_all()
bank.update_calibration(calibrations)
bank.reset_volumes(pump_ids=None)
```

### QueuedLEDController Class
```python
led = QueuedLEDController(pin=33, debug=False)

# Control
led.queue_command(duty, duration, command_id)
led.set_duty(duty)
led.stop()

# Status
status = led.get_status()
led.emergency_stop()
```

## 🔄 Integration with Host

### Python Host Example
```python
import paho.mqtt.client as mqtt
import json

def send_pump_command(channel, pump, duty, duration):
    topic = f"cmd/chan{channel}/pump{pump}"
    payload = {"duty": duty, "dur": duration}
    client.publish(topic, json.dumps(payload))

def handle_status(client, userdata, msg):
    if msg.topic.startswith("stat/chan"):
        status = json.loads(msg.payload)
        print(f"Active pump: {status['active_pump']}")
        print(f"Total volume: {status['total_volume']}")

client = mqtt.Client()
client.on_message = handle_status
client.connect("192.168.1.100", 1883, 60)
client.subscribe("stat/chan+")
```

## 📋 System Specifications

| Parameter | Value | Notes |
|-----------|-------|-------|
| Control Frequency | 1.0 Hz | Fixed per specification |
| Max Command Duration | 3600 s | 1 hour safety limit |
| Queue Depth | 5 commands | Per pump |
| PWM Frequency | 1 kHz | Configurable 1-3 kHz |
| PWM Resolution | 10-bit (1023) | ESP32 default |
| Volume Precision | ±5% | With proper calibration |
| MQTT Timeout | 60 s | Configurable |
| Watchdog Timeout | 8 s | Hardware failsafe |
| Log Rotation | Daily | Automatic |

---

## 📄 License

Part of the MCMC (Microscope Chemostat) project. See main project license. 