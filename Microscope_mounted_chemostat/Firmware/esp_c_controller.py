# esp_c_controller.py - MCMC ESP-C Channel Controller
# Single-channel pump and LED control with MQTT integration

import json
import utime
import gc
from machine import Pin, Timer, RTC, reset, WDT
import network
import ubinascii
from umqtt.simple import MQTTClient
import sdcard
import os
import uasyncio as asyncio

# Import configuration and hardware modules
import config
from Hardware_modules.pump_controller import PumpBank
from Hardware_modules.led_controller import QueuedLEDController

# ================== CONFIGURATION FROM CONFIG.PY ==================

# Channel identification
CHANNEL_ID = config.CHANNEL_ID

# Hardware pins
PUMP_PINS = config.PUMP_PINS
LED_PIN = config.LED_PIN
STATUS_LED_PIN = config.STATUS_LED_PIN
SD_CS_PIN = config.SD_CS_PIN

# WiFi Configuration  
WIFI_SSID = config.WIFI_SSID
WIFI_PASSWORD = config.WIFI_PASSWORD

# MQTT Configuration
MQTT_BROKER = config.MQTT_BROKER
MQTT_PORT = config.MQTT_PORT
MQTT_KEEPALIVE = config.MQTT_KEEPALIVE

# Get MAC address properly
wlan_if = network.WLAN(network.STA_IF)
MQTT_CLIENT_ID = f"esp_c{CHANNEL_ID}_" + ubinascii.hexlify(wlan_if.config('mac')).decode()

# MQTT Topics (formatted with channel ID)
TOPIC_CMD_PUMP_BASE = config.TOPIC_CMD_PUMP_BASE.format(CHANNEL_ID, "{}")  # cmd/chan1/pump{}
TOPIC_CMD_LED = config.TOPIC_CMD_LED.format(CHANNEL_ID)                    # cmd/chan1/led
TOPIC_CMD_CALIBRATE = config.TOPIC_CMD_CALIBRATE.format(CHANNEL_ID)        # cmd/chan1/calibrate
TOPIC_CMD_RESET_VOLUMES = config.TOPIC_CMD_RESET_VOLUMES.format(CHANNEL_ID) # cmd/chan1/reset_volumes
TOPIC_CMD_FLUSH = f"cmd/chan{CHANNEL_ID}/flush"                            # cmd/chan1/flush
TOPIC_CMD_KILL = config.TOPIC_CMD_KILL                                     # cmd/kill
TOPIC_STAT_CHANNEL = config.TOPIC_STAT_CHANNEL.format(CHANNEL_ID)          # stat/chan1

# Control parameters
CONTROL_FREQ_HZ = config.CONTROL_FREQUENCY
assert CONTROL_FREQ_HZ == 1.0, "Control frequency must be 1.0 Hz per spec"

MAX_COMMAND_DURATION = config.MAX_COMMAND_DURATION
MQTT_TIMEOUT_SEC = config.MQTT_TIMEOUT_SEC
QUEUE_DEPTH = config.QUEUE_DEPTH

# Safety and timing
WIFI_RETRY_DELAY = 1.0  # Start with 1s, exponential backoff
MAX_RETRY_DELAY = 60.0  # Maximum retry delay

# ================== GLOBAL STATE ==================

class SystemState:
    def __init__(self):
        self.channel_id = CHANNEL_ID
        self.pump_status = {}
        self.led_status = {}
        self.mqtt_connected = False
        self.wifi_connected = False
        self.mqtt_timeout = False
        self.last_mqtt_message = utime.ticks_ms()
        self.emergency_stop = False
        self.uptime_sec = 0
        self.last_log_day = None
        self.log_file = None
        self.led_mode = "normal"  # "normal", "timeout", "emergency"
        self.wifi_retry_delay = WIFI_RETRY_DELAY
        self.last_sd_retry = 0
        
state = SystemState()
pump_bank = None
led_controller = None
mqtt_client = None
status_led = None
sd = None
watchdog = None

# ================== UTILITY FUNCTIONS ==================

def get_uptime():
    """Get system uptime in seconds."""
    return utime.ticks_ms() // 1000

def generate_command_id():
    """Generate unique command ID."""
    return f"cmd_{CHANNEL_ID}_{utime.ticks_ms()}"

# ================== WIFI MANAGEMENT ==================

def connect_wifi():
    """Connect to WiFi network with exponential backoff."""
    global state
    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if wlan.isconnected():
        state.wifi_connected = True
        state.wifi_retry_delay = WIFI_RETRY_DELAY  # Reset backoff
        print(f"[WiFi] Already connected: {wlan.ifconfig()[0]}")
        return True
    
    print(f"[WiFi] Connecting to {WIFI_SSID}...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    
    # Wait up to retry delay for connection
    timeout = int(state.wifi_retry_delay)
    while timeout > 0 and not wlan.isconnected():
        utime.sleep(1)
        timeout -= 1
    
    if wlan.isconnected():
        state.wifi_connected = True
        state.wifi_retry_delay = WIFI_RETRY_DELAY  # Reset backoff
        ip = wlan.ifconfig()[0]
        print(f"[WiFi] Connected successfully: {ip}")
        return True
    else:
        state.wifi_connected = False
        # Exponential backoff
        state.wifi_retry_delay = min(state.wifi_retry_delay * 2, MAX_RETRY_DELAY)
        print(f"[WiFi] Connection failed! Next retry in {state.wifi_retry_delay}s")
        return False

# ================== MQTT MANAGEMENT ==================

def mqtt_callback(topic, msg):
    """Handle incoming MQTT messages."""
    global state, pump_bank, led_controller
    
    try:
        topic_str = topic.decode('utf-8')
        msg_str = msg.decode('utf-8')
        
        print(f"[MQTT] Received: {topic_str} -> {msg_str}")
        
        # Update last message time for timeout detection
        state.last_mqtt_message = utime.ticks_ms()
        
        # Clear timeout state if we were in timeout
        if state.mqtt_timeout:
            state.mqtt_timeout = False
            state.led_mode = "normal"
            print("[MQTT] Timeout cleared - resuming normal operation")
        
        if topic_str == TOPIC_CMD_KILL:
            print("[SAFETY] Emergency kill command received!")
            emergency_shutdown()
            
        elif topic_str.startswith(f"cmd/chan{CHANNEL_ID}/pump"):
            # Extract pump number from topic: cmd/chan1/pump2 -> pump 2
            try:
                pump_num = int(topic_str.split('pump')[1])
                if 1 <= pump_num <= 4:
                    handle_pump_command(pump_num, msg_str)
                else:
                    print(f"[MQTT] Invalid pump number: {pump_num}")
            except (ValueError, IndexError):
                print(f"[MQTT] Invalid pump topic format: {topic_str}")
                
        elif topic_str == TOPIC_CMD_LED:
            handle_led_command(msg_str)
            
        elif topic_str == TOPIC_CMD_CALIBRATE:
            handle_calibration_command(msg_str)
            
        elif topic_str == TOPIC_CMD_RESET_VOLUMES:
            handle_reset_volumes_command(msg_str)
            
        elif topic_str == TOPIC_CMD_FLUSH:
            handle_flush_command(msg_str)
            
    except Exception as e:
        print(f"[MQTT] Error processing message: {e}")

def handle_pump_command(pump_num, msg_str):
    """Handle pump control command."""
    global pump_bank
    
    try:
        data = json.loads(msg_str)
        duty = float(data.get('duty', 0))
        duration = float(data.get('dur', 0))
        
        # Validate parameters
        if not (0 <= duty <= 100):
            print(f"[Pump{pump_num}] Invalid duty: {duty}%")
            return
            
        if not (0 <= duration <= MAX_COMMAND_DURATION):
            print(f"[Pump{pump_num}] Invalid duration: {duration}s")
            return
        
        # Queue command
        if pump_bank:
            command_id = generate_command_id()
            success = pump_bank.queue_command(pump_num, duty, duration, command_id, QUEUE_DEPTH)
            
            if success:
                print(f"[Pump{pump_num}] Command queued: {duty}% for {duration}s")
                log_pump_command(pump_num, duty, duration, 0, command_id)
            else:
                print(f"[Pump{pump_num}] Command rejected (queue full)")
        
    except Exception as e:
        print(f"[Pump{pump_num}] Error processing command: {e}")

def handle_led_command(msg_str):
    """Handle LED control command."""
    global led_controller
    
    try:
        data = json.loads(msg_str)
        duty = float(data.get('duty', 0))
        duration = float(data.get('dur', 0))
        
        # Validate parameters
        if not (0 <= duty <= 100):
            print(f"[LED] Invalid duty: {duty}%")
            return
            
        if not (0 <= duration <= MAX_COMMAND_DURATION):
            print(f"[LED] Invalid duration: {duration}s")
            return
        
        # Queue LED command
        if led_controller:
            command_id = generate_command_id()
            success = led_controller.queue_command(duty, duration, command_id)
            
            if success:
                print(f"[LED] Command queued: {duty}% for {duration}s")
                log_led_command(duty, duration, command_id)
            else:
                print("[LED] Command rejected (queue full)")
        
    except Exception as e:
        print(f"[LED] Error processing command: {e}")

def handle_calibration_command(msg_str):
    """Handle pump calibration update."""
    global pump_bank
    
    try:
        calibrations = json.loads(msg_str)
        
        if pump_bank:
            # Convert string keys to integers
            calib_dict = {}
            for pump_str, calib in calibrations.items():
                try:
                    pump_id = int(pump_str.replace('pump', ''))
                    if 1 <= pump_id <= 4 and 'a' in calib and 'b' in calib:
                        calib_dict[pump_id] = calib
                except (ValueError, KeyError):
                    print(f"[Calibration] Invalid calibration for {pump_str}")
            
            if calib_dict:
                pump_bank.update_calibration(calib_dict)
                print(f"[Calibration] Updated {len(calib_dict)} pump(s)")
                log_event("CALIBRATION_UPDATE", f"Updated {len(calib_dict)} pumps")
        
    except Exception as e:
        print(f"[Calibration] Error processing command: {e}")

def handle_reset_volumes_command(msg_str):
    """Handle volume counter reset."""
    global pump_bank
    
    try:
        data = json.loads(msg_str)
        pump_ids = data.get('pumps', None)  # None = all pumps
        
        if pump_bank:
            pump_bank.reset_volumes(pump_ids)
            print(f"[Volumes] Reset counters for pumps: {pump_ids or 'all'}")
            log_event("VOLUME_RESET", f"Pumps: {pump_ids or 'all'}")
        
    except Exception as e:
        print(f"[Volumes] Error processing command: {e}")

def handle_flush_command(msg_str):
    """Handle flush command to clear pump queues."""
    global pump_bank
    
    try:
        data = json.loads(msg_str)
        pump_ids = data.get('pumps', None)  # None = all pumps
        
        if pump_bank:
            if pump_ids is None:
                # Flush all pumps
                total_cleared = pump_bank.flush_all_queues()
                print(f"[Flush] Flushed all pumps - {total_cleared} commands cleared")
                log_event("FLUSH", f"All pumps - {total_cleared} commands")
            else:
                # Flush specific pumps
                total_cleared = 0
                for pump_id in pump_ids:
                    cleared = pump_bank.flush_queue(pump_id)
                    total_cleared += cleared
                print(f"[Flush] Flushed pumps {pump_ids} - {total_cleared} commands cleared")
                log_event("FLUSH", f"Pumps {pump_ids} - {total_cleared} commands")
        
    except Exception as e:
        print(f"[Flush] Error processing command: {e}")

def connect_mqtt():
    """Connect to MQTT broker with full subscription."""
    global mqtt_client, state
    
    try:
        mqtt_client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, keepalive=MQTT_KEEPALIVE)
        mqtt_client.set_callback(mqtt_callback)
        mqtt_client.connect()
        
        # Subscribe to all command topics
        mqtt_client.subscribe(TOPIC_CMD_KILL)
        mqtt_client.subscribe(TOPIC_CMD_LED)
        mqtt_client.subscribe(TOPIC_CMD_CALIBRATE)
        mqtt_client.subscribe(TOPIC_CMD_RESET_VOLUMES)
        mqtt_client.subscribe(TOPIC_CMD_FLUSH)
        
        # Subscribe to individual pump topics
        for pump_num in range(1, 5):
            topic = TOPIC_CMD_PUMP_BASE.format(pump_num)
            mqtt_client.subscribe(topic)
        
        state.mqtt_connected = True
        state.last_mqtt_message = utime.ticks_ms()
        print(f"[MQTT] Connected as {MQTT_CLIENT_ID} (keepalive={MQTT_KEEPALIVE}s)")
        return True
        
    except Exception as e:
        state.mqtt_connected = False
        print(f"[MQTT] Connection failed: {e}")
        return False

def publish_status():
    """Publish channel status via MQTT."""
    global mqtt_client, state, pump_bank, led_controller
    
    if not state.mqtt_connected or mqtt_client is None:
        return
        
    try:
        # Get pump status
        pump_duties = [0, 0, 0, 0]
        total_volumes = [0.0, 0.0, 0.0, 0.0]
        active_pump = 0
        total_queued = 0
        
        if pump_bank:
            pump_status = pump_bank.get_all_status()
            for pump_id in range(1, 5):
                if pump_id in pump_status:
                    pump_duties[pump_id-1] = pump_status[pump_id]["duty_percent"]
                    total_volumes[pump_id-1] = pump_status[pump_id]["total_volume_ml"]
                    total_queued += pump_status[pump_id]["queue_length"]
                    
                    if pump_status[pump_id]["is_running"]:
                        active_pump = pump_id
        
        # Get LED status
        led_duty = 0
        led_queued = 0
        if led_controller:
            led_status = led_controller.get_status()
            led_duty = led_status["duty_percent"]
            led_queued = led_status["queue_length"]
        
        status_data = {
            "pump_duty": pump_duties,
            "led_duty": led_duty,
            "queued": total_queued + led_queued,
            "total_volume": total_volumes,
            "active_pump": active_pump,
            "uptime": get_uptime(),
            "mqtt_timeout": state.mqtt_timeout,
            "emergency_stop": state.emergency_stop
        }
        
        message = json.dumps(status_data)
        mqtt_client.publish(TOPIC_STAT_CHANNEL, message, qos=1)
        
    except Exception as e:
        print(f"[MQTT] Error publishing status: {e}")

# ================== SD CARD LOGGING ==================

def init_sd_card():
    """Initialize SD card for logging."""
    global sd
    
    try:
        from machine import SPI
        spi = SPI(1, baudrate=40000000, 
                  sck=Pin(config.SD_SCK_PIN), 
                  mosi=Pin(config.SD_MOSI_PIN), 
                  miso=Pin(config.SD_MISO_PIN))
        sd = sdcard.SDCard(spi, Pin(SD_CS_PIN))
        os.mount(sd, '/sd')
        print("[SD] Card initialized successfully")
        return True
        
    except Exception as e:
        print(f"[SD] Initialization failed: {e}")
        sd = None
        return False

def get_log_filename():
    """Generate log filename based on current date."""
    rtc = RTC()
    year, month, day, _, _, _, _, _ = rtc.datetime()
    return f"/sd/chan{CHANNEL_ID}_log_{year:04d}{month:02d}{day:02d}.csv"

def init_log_file():
    """Initialize or rotate log file."""
    global state
    
    if sd is None:
        return
    
    try:
        rtc = RTC()
        year, month, day, _, _, _, _, _ = rtc.datetime()
        current_day = f"{year:04d}{month:02d}{day:02d}"
        
        if state.last_log_day != current_day:
            if state.log_file:
                state.log_file.close()
            
            filename = get_log_filename()
            
            # Create header if file doesn't exist
            file_exists = False
            try:
                with open(filename, 'r'):
                    file_exists = True
            except:
                pass
            
            state.log_file = open(filename, 'a')
            
            if not file_exists:
                state.log_file.write(config.LOG_CSV_HEADER + "\n")
                state.log_file.flush()
            
            state.last_log_day = current_day
            print(f"[SD] Log file: {filename}")
            
    except Exception as e:
        print(f"[SD] Error initializing log file: {e}")

def retry_sd_card_init():
    """Retry SD card initialization if card was inserted after boot."""
    global state
    
    current_time = utime.ticks_ms()
    if utime.ticks_diff(current_time, state.last_sd_retry) > 60000:
        if sd is None:
            print("[SD] Retrying SD card initialization...")
            if init_sd_card():
                init_log_file()
        state.last_sd_retry = current_time

def log_event(event_type, details="", pump=0, duty=0, duration=0, led_duty=0, volume=0.0, command_id=""):
    """Log event to SD card."""
    if sd is None or state.log_file is None:
        return
    
    try:
        rtc = RTC()
        year, month, day, _, hour, minute, second, _ = rtc.datetime()
        timestamp = f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
        
        log_line = f"{timestamp},{pump},{duty},{duration},{led_duty},{volume:.3f},{command_id},{event_type}\n"
        state.log_file.write(log_line)
        state.log_file.flush()
        
    except Exception as e:
        print(f"[SD] Error logging event: {e}")

def log_pump_command(pump_num, duty, duration, volume, command_id):
    """Log pump command execution."""
    log_event("PUMP_CMD", pump=pump_num, duty=duty, duration=duration, volume=volume, command_id=command_id)

def log_led_command(duty, duration, command_id):
    """Log LED command execution."""
    log_event("LED_CMD", duty=0, duration=0, led_duty=duty, command_id=command_id)

# ================== SAFETY SYSTEMS ==================

def emergency_shutdown():
    """Emergency shutdown - stop all pumps and LED immediately."""
    global state, pump_bank, led_controller
    
    print("[SAFETY] EMERGENCY SHUTDOWN ACTIVATED!")
    
    state.emergency_stop = True
    
    # Stop all pumps and LED
    if pump_bank:
        pump_bank.emergency_stop_all()
    
    if led_controller:
        led_controller.emergency_stop()
    
    state.led_mode = "emergency"
    log_event("EMERGENCY_STOP", "Kill command received")

def check_mqtt_timeout():
    """Check for MQTT communication timeout."""
    global state
    
    if not state.mqtt_connected:
        return
    
    elapsed_ms = utime.ticks_diff(utime.ticks_ms(), state.last_mqtt_message)
    
    if elapsed_ms > (MQTT_TIMEOUT_SEC * 1000) and not state.mqtt_timeout:
        print(f"[SAFETY] MQTT timeout after {elapsed_ms/1000:.1f}s - entering failsafe mode")
        
        state.mqtt_timeout = True
        state.led_mode = "timeout"
        
        # Stop all pumps and LED
        if pump_bank:
            pump_bank.emergency_stop_all()
        
        if led_controller:
            led_controller.emergency_stop()
        
        log_event("MQTT_TIMEOUT", f"Silent for {elapsed_ms/1000:.1f}s")

# ================== LED STATUS CONTROL ==================

def update_status_led():
    """Handle status LED indication."""
    global state, status_led
    
    if status_led is None:
        return
    
    current_time = utime.ticks_ms()
    
    if state.led_mode == "normal":
        # Slow blink (2Hz)
        status_led.value((current_time // 250) % 2)
    elif state.led_mode == "timeout":
        # Fast blink (10Hz)
        status_led.value((current_time // 50) % 2)
    elif state.led_mode == "emergency":
        # Very fast blink (20Hz)
        status_led.value((current_time // 25) % 2)

# ================== MAIN CONTROL LOOP ==================

def control_step():
    """Main control step - called every second."""
    global state, pump_bank, led_controller, mqtt_client, watchdog
    
    try:
        # Feed watchdog
        if watchdog:
            watchdog.feed()
        
        # Skip updates if in emergency stop
        if state.emergency_stop:
            return
        
        # Check MQTT timeout
        check_mqtt_timeout()
        
        # Update pumps (handle queues and timeouts)
        if pump_bank and not state.mqtt_timeout:
            pump_bank.update_all()
        
        # Update LED
        if led_controller and not state.mqtt_timeout:
            led_controller.update()
        
        # Update uptime
        state.uptime_sec = get_uptime()
        
        # Publish status via MQTT
        publish_status()
        
        # Check MQTT connection (non-blocking)
        if mqtt_client and state.mqtt_connected:
            try:
                mqtt_client.check_msg()  # Process incoming messages
            except Exception as e:
                print(f"[MQTT] Error checking messages: {e}")
                state.mqtt_connected = False
        
        # Log periodic status if pumps are active
        if pump_bank:
            status = pump_bank.get_all_status()
            active_pumps = [p for p, s in status.items() if s["is_running"]]
            if active_pumps:
                print(f"[Status] Active pumps: {active_pumps}")
        
    except Exception as e:
        print(f"[Control] Error in control step: {e}")

async def control_timer_callback():
    """Async control loop timer."""
    while True:
        try:
            control_step()
            await asyncio.sleep_ms(1000)  # 1Hz control
        except Exception as e:
            print(f"[Timer] Control callback error: {e}")
            await asyncio.sleep_ms(1000)

# ================== INITIALIZATION ==================

def initialize_system():
    """Initialize all system components."""
    global pump_bank, led_controller, status_led, sd, watchdog, state
    
    print(f"=== MCMC ESP-C{CHANNEL_ID} Channel Controller ===")
    print(f"Client ID: {MQTT_CLIENT_ID}")
    print(f"Control topics: cmd/chan{CHANNEL_ID}/...")
    print(f"Status topic: {TOPIC_STAT_CHANNEL}")
    
    # Initialize hardware watchdog
    try:
        watchdog = WDT(timeout=8000)  # 8 second timeout
        print("[Init] Hardware watchdog enabled")
    except Exception as e:
        print(f"[Init] Watchdog failed: {e}")
        watchdog = None
    
    # Initialize status LED
    status_led = Pin(STATUS_LED_PIN, Pin.OUT)
    status_led.off()
    
    # Initialize pump bank
    print("[Init] Initializing pump bank...")
    pump_bank = PumpBank(
        pump_pins=PUMP_PINS,
        calibrations=config.DEFAULT_CALIBRATION,
        frequency=config.PWM_FREQUENCY
    )
    
    # Initialize LED controller
    print("[Init] Initializing LED controller...")
    led_controller = QueuedLEDController(
        pin=LED_PIN,
        frequency=config.PWM_FREQUENCY,
        max_queue=QUEUE_DEPTH
    )
    
    # Initialize SD card
    print("[Init] Initializing SD card...")
    if init_sd_card():
        init_log_file()
        log_event("SYSTEM_START", f"ESP-C{CHANNEL_ID} initialized")
    else:
        print("[Warning] SD card not available - logging disabled, will retry periodically")
    
    # Connect to WiFi
    print("[Init] Connecting to WiFi...")
    if not connect_wifi():
        print("[Warning] WiFi connection failed - MQTT disabled")
        return True  # Continue without MQTT
    
    # Connect to MQTT
    print("[Init] Connecting to MQTT...")
    if not connect_mqtt():
        print("[Warning] MQTT connection failed")
    
    print("[Init] System initialization complete!")
    print(f"[Control] Ready for commands on channel {CHANNEL_ID}")
    return True

# ================== MAIN PROGRAM ==================

async def main_async():
    """Main async program loop."""
    global state
    
    if not initialize_system():
        print("[ERROR] System initialization failed!")
        return
    
    print(f"[Main] ESP-C{CHANNEL_ID} controller running...")
    
    # Start control loop task
    control_task = asyncio.create_task(control_timer_callback())
    
    # Main monitoring loop
    last_wifi_check = utime.ticks_ms()
    last_gc_time = utime.ticks_ms()
    
    try:
        while True:
            current_time = utime.ticks_ms()
            
            # Handle status LED
            update_status_led()
            
            # Emergency shutdown handling
            if state.emergency_stop:
                await asyncio.sleep_ms(2000)
                continue
            
            # Periodic SD card retry
            retry_sd_card_init()
            
            # Periodic WiFi/MQTT checks
            if utime.ticks_diff(current_time, last_wifi_check) > int(state.wifi_retry_delay * 1000):
                if not state.wifi_connected:
                    print("[Main] Attempting WiFi reconnection...")
                    connect_wifi()
                elif not state.mqtt_connected:
                    print("[Main] Attempting MQTT reconnection...")
                    connect_mqtt()
                last_wifi_check = current_time
            
            # Garbage collection every 5 seconds
            if utime.ticks_diff(current_time, last_gc_time) > 5000:
                gc.collect()
                last_gc_time = current_time
            
            await asyncio.sleep_ms(100)  # 10Hz main loop
            
    except Exception as e:
        print(f"[Main] Fatal error: {e}")
        emergency_shutdown()
        await asyncio.sleep_ms(5000)
        reset()

def main():
    """Main program entry point."""
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[Main] Shutting down...")
        emergency_shutdown()
    except Exception as e:
        print(f"[Main] Fatal error: {e}")
        emergency_shutdown()
        utime.sleep(5)
        reset()

if __name__ == "__main__":
    main() 