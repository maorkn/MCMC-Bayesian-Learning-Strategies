# config.py - MCMC ESP-C Channel Controller Configuration
# Single-channel pump and LED control module

# ================== WIFI CONFIGURATION ==================
WIFI_SSID = "your_wifi_network"
WIFI_PASSWORD = "your_wifi_password"

# ================== MQTT CONFIGURATION ==================
# IP address of the Mac running mosquitto broker
MQTT_BROKER = "192.168.1.100"  
MQTT_PORT = 1883
MQTT_KEEPALIVE = 30  # Seconds

# Channel ID - MUST be set per ESP-C node (1, 2, or 3)
CHANNEL_ID = 1  # Change this for each ESP-C controller

# MQTT Topics (will be formatted with CHANNEL_ID)
TOPIC_CMD_PUMP_BASE = "cmd/chan{}/pump{}"      # cmd/chan1/pump1-4
TOPIC_CMD_LED = "cmd/chan{}/led"               # cmd/chan1/led
TOPIC_CMD_CALIBRATE = "cmd/chan{}/calibrate"   # cmd/chan1/calibrate
TOPIC_CMD_RESET_VOLUMES = "cmd/chan{}/reset_volumes"  # cmd/chan1/reset_volumes
TOPIC_CMD_KILL = "cmd/kill"                    # Global emergency stop
TOPIC_STAT_CHANNEL = "stat/chan{}"             # stat/chan1

# ================== HARDWARE CONFIGURATION ==================
# GPIO Pin assignments
PUMP_PINS = [25, 26, 27, 32]  # GPIO for pumps 1-4 PWM
LED_PIN = 33                  # LED pair PWM output
STATUS_LED_PIN = 2            # Built-in LED for status

# SD Card SPI pins
SD_CS_PIN = 5         # SD card chip select
SD_SCK_PIN = 18       # SPI clock
SD_MOSI_PIN = 23      # SPI MOSI  
SD_MISO_PIN = 19      # SPI MISO

# PWM Configuration
PWM_FREQUENCY = 1000  # 1kHz PWM frequency
PWM_RESOLUTION = 10   # 10-bit resolution (0-1023)

# ================== CONTROL PARAMETERS ==================
# Safety limits
MAX_COMMAND_DURATION = 3600   # 1 hour maximum pump run time (seconds)
MQTT_TIMEOUT_SEC = 60         # Failsafe timeout if MQTT silent
QUEUE_DEPTH = 5               # Maximum queued commands per pump

# Timing
CONTROL_FREQUENCY = 1.0       # 1Hz status reporting
STATUS_LED_FREQ_NORMAL = 2    # 2Hz status LED blink (normal)
STATUS_LED_FREQ_TIMEOUT = 10  # 10Hz status LED blink (timeout)

# ================== CALIBRATION DEFAULTS ==================
# Default calibration coefficients (ml/h = a * PWM% + b)
# These will be overridden by host calibration data
DEFAULT_CALIBRATION = {
    1: {"a": 2.5, "b": 0.1},  # Pump 1: ml/h = 2.5*PWM% + 0.1
    2: {"a": 2.4, "b": 0.0},  # Pump 2: ml/h = 2.4*PWM% + 0.0
    3: {"a": 2.6, "b": 0.2},  # Pump 3: ml/h = 2.6*PWM% + 0.2
    4: {"a": 2.3, "b": 0.1}   # Pump 4: ml/h = 2.3*PWM% + 0.1
}

# Calibration accuracy target
CALIBRATION_ERROR_TARGET = 5.0  # ±5% error target

# ================== LOGGING CONFIGURATION ==================
# SD card logging format
LOG_CSV_HEADER = "timestamp,pump,duty_pct,duration_s,led_duty_pct,volume_ml,command_id,event_type"

# Log rotation (new file each day)
LOG_ROTATE_DAILY = True

# Volume tracking
TRACK_VOLUMES = True          # Enable volume calculation and tracking
VOLUME_RESET_ON_BOOT = False  # Keep volume counters across reboots 