# max31865.py - MAX31865 Temperature Sensor Module with Noise Filtering
from machine import Pin, SPI
import math
import time

# ---- PIN DEFINITIONS ----
CS_PIN = 5    # MAX31865 Chip Select
SCK_PIN = 18  # SPI Clock
MOSI_PIN = 23 # SPI MOSI
MISO_PIN = 19 # SPI MISO
CS_SD_PIN = 15  # SD Card CS pin to ensure it's deselected

# ---- TEMPERATURE SENSOR CONSTANTS ----
REF_RESISTANCE = 430.0
RTD_NOMINAL = 100.0
RTD_A = 3.9083e-3
RTD_B = -5.775e-7

# MAX31865 Register Addresses
CONFIG_REG = 0x00
RTD_MSB_REG = 0x01
RTD_LSB_REG = 0x02
FAULT_STATUS_REG = 0x07

# ---- NOISE FILTERING CONSTANTS ----
MAX_TEMP_CHANGE = 5.0  # Maximum allowed temp change per reading (°C)
MEDIAN_FILTER_SIZE = 5  # Number of readings for median filter
MAX_READ_RETRIES = 3   # Maximum retries for each reading

# ---- GLOBAL VARIABLES ----
spi = None
cs = None
cs_sd = None
last_valid_temp = None
temp_history = []  # Store recent temperatures for median filtering

def init_spi():
    """Initialize the SPI bus for MAX31865."""
    global spi, cs, cs_sd
    if spi is None:
        print("[MAX31865] Initializing VSPI...")
        # Ensure SD card CS is high (deselected)
        cs_sd = Pin(CS_SD_PIN, Pin.OUT, value=1)
        
        # Use slower, more reliable SPI settings to reduce noise sensitivity
        spi = SPI(2, baudrate=250000, polarity=0, phase=1,  # Reduced from 500kHz
                  sck=Pin(SCK_PIN), mosi=Pin(MOSI_PIN), miso=Pin(MISO_PIN))
        cs = Pin(CS_PIN, Pin.OUT, value=1)
        time.sleep_ms(200)  # Longer stabilization time

def write_register(reg, data):
    """Write to MAX31865 register with improved timing."""
    # Ensure SD card is deselected
    if cs_sd:
        cs_sd.value(1)
    time.sleep_ms(2)  # Increased delay to avoid noise
    
    cs.value(0)
    time.sleep_ms(20)  # Increased delay for more reliable communication
    spi.write(bytes([reg | 0x80, data]))
    time.sleep_ms(20)  # Increased delay
    cs.value(1)

def read_register(reg):
    """Read from MAX31865 register with improved timing."""
    # Ensure SD card is deselected
    if cs_sd:
        cs_sd.value(1)
    time.sleep_ms(2)  # Increased delay to avoid noise
    
    cs.value(0)
    time.sleep_ms(20)  # Increased delay for more reliable communication
    spi.write(bytes([reg & 0x7F]))  # Read mode
    result = spi.read(1)
    time.sleep_ms(20)  # Increased delay
    cs.value(1)
    value = int.from_bytes(result, 'big')
    
    # Debug output for troubleshooting
    if reg == RTD_MSB_REG or reg == RTD_LSB_REG:
        if value == 0xFF or value == 0x00:
            print(f"[MAX31865] Warning: Register {hex(reg)} returned {hex(value)}")
    
    return value

def check_fault():
    """Check MAX31865 fault register and return fault status."""
    # Ensure SD card is deselected
    if cs_sd:
        cs_sd.value(1)
    time.sleep_ms(2)
    
    cs.value(0)
    time.sleep_ms(20)
    spi.write(bytes([FAULT_STATUS_REG & 0x7F]))  # Read fault register
    fault = spi.read(1)
    time.sleep_ms(20)
    cs.value(1)
    
    fault = int.from_bytes(fault, 'big')
    if fault & 0x01:  # RTD High Threshold
        return "RTD High Threshold"
    elif fault & 0x02:  # RTD Low Threshold
        return "RTD Low Threshold"
    elif fault & 0x04:  # REFIN- > 0.85 × VBIAS
        return "REFIN- High"
    elif fault & 0x08:  # REFIN- < 0.85 × VBIAS (FORCE- Open)
        return "REFIN- Low"
    elif fault & 0x10:  # RTDIN- < 0.85 × VBIAS (FORCE- Open)
        return "RTDIN- Low"
    elif fault & 0x20:  # Overvoltage/Undervoltage Fault
        return "Voltage Fault"
    else:
        return None

def median_filter(values):
    """Calculate median of a list of values."""
    if not values:
        return None
    sorted_values = sorted(values)
    n = len(sorted_values)
    if n % 2 == 0:
        return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
    else:
        return sorted_values[n//2]

def read_temperature_raw():
    """Read raw temperature from MAX31865 with single attempt."""
    if spi is None:
        raise RuntimeError("[MAX31865] SPI not initialized! Call init_max31865() first.")
    
    try:
        # Add small delay before reading to avoid interference from PWM switching
        time.sleep_ms(5)
        
        # Read raw RTD data
        msb = read_register(RTD_MSB_REG)
        lsb = read_register(RTD_LSB_REG)
        
        # Check for fault bit
        if lsb & 0x01:
            fault = check_fault()
            print(f"[MAX31865] Fault bit set, fault status: {fault}")
            return None
        
        raw = ((msb << 8) | lsb) >> 1
        
        # Validate raw value
        if raw == 0 or raw == 0x7FFF:
            print(f"[MAX31865] Invalid raw reading: {raw}")
            return None
        
        # Calculate resistance
        resistance = (raw * REF_RESISTANCE) / 32768.0
        
        # Validate resistance (PT100 should be ~100Ω at 0°C, ~138.5Ω at 100°C)
        if resistance < 50 or resistance > 200:
            print(f"[MAX31865] Invalid resistance: {resistance}Ω")
            return None
        
        # Convert resistance to temperature
        if resistance >= RTD_NOMINAL:
            temp = -RTD_A + math.sqrt(RTD_A**2 + 4 * RTD_B * (1 - resistance / RTD_NOMINAL))
            temp = -temp / (2 * RTD_B)
        else:
            temp = (resistance / RTD_NOMINAL - 1) / RTD_A
        
        # Final temperature validation
        if temp < -50 or temp > 150:
            print(f"[MAX31865] Temperature out of range: {temp}°C")
            return None
        
        return round(temp, 2)
        
    except Exception as e:
        print(f"[MAX31865] Error reading temperature: {e}")
        return None

def read_temperature():
    """Read temperature with noise filtering and validation."""
    global last_valid_temp, temp_history
    
    # Collect multiple readings for filtering
    readings = []
    for attempt in range(MEDIAN_FILTER_SIZE):
        temp = read_temperature_raw()
        if temp is not None:
            readings.append(temp)
        
        # Add small delay between readings to avoid burst noise
        if attempt < MEDIAN_FILTER_SIZE - 1:
            time.sleep_ms(10)
    
    # Need at least 3 valid readings for median filter
    if len(readings) < 3:
        print(f"[MAX31865] Insufficient valid readings: {len(readings)}/{MEDIAN_FILTER_SIZE}")
        return last_valid_temp  # Return last known good value
    
    # Calculate median to filter out noise spikes
    median_temp = median_filter(readings)
    
    # Validate against previous reading to catch remaining noise
    if last_valid_temp is not None:
        temp_change = abs(median_temp - last_valid_temp)
        if temp_change > MAX_TEMP_CHANGE:
            print(f"[MAX31865] Large temp change detected: {temp_change:.1f}°C, filtering out")
            print(f"[MAX31865] Readings: {readings}")
            return last_valid_temp  # Return last known good value
    
    # Update history for trend analysis
    temp_history.append(median_temp)
    if len(temp_history) > 10:  # Keep last 10 readings
        temp_history.pop(0)
    
    # Update last valid temperature
    last_valid_temp = median_temp
    return median_temp

def init_max31865():
    """Initialize MAX31865."""
    global last_valid_temp, temp_history
    
    init_spi()
    
    # Reset filtering variables
    last_valid_temp = None
    temp_history = []
    
    # Configure MAX31865 with 0xC3 (3-wire RTD, 60Hz filter, bias on)
    print("[MAX31865] Writing configuration 0xC3...")
    write_register(CONFIG_REG, 0xC3)
    time.sleep_ms(200)  # Longer stabilization time
    
    # Read back configuration to verify
    config = read_register(CONFIG_REG)
    print(f"[MAX31865] Configuration readback: 0x{config:02X}")
    
    # Accept both 0xC3 and 0xC1 as valid (1-shot bit may be cleared automatically)
    if config not in [0xC3, 0xC1]:
        print("[MAX31865] ERROR: Configuration mismatch!")
        print(f"[MAX31865] Expected 0xC3 or 0xC1, got 0x{config:02X}")
        return False
    else:
        print("[MAX31865] Configuration accepted (1-shot bit may auto-clear)")
    
    # Read initial temperature to verify sensor
    try:
        temp = read_temperature()
        if temp is None:
            print("[MAX31865] ERROR: Initial temperature read returned None")
            fault = check_fault()
            if fault:
                print(f"[MAX31865] Fault detected: {fault}")
            return False
            
        print(f"[MAX31865] Initial temperature reading: {temp}°C")
        return True
    except Exception as e:
        print(f"[MAX31865] Error during initialization: {e}")
        return False

def deinit():
    """Deinitialize SPI."""
    global spi, cs
    if spi is not None:
        spi.deinit()
        spi = None
        cs = None

# ---- TEST CODE ----
if __name__ == "__main__":
    init_max31865()
    while True:
        temp = read_temperature()
        print(f"Temperature: {temp}°C")
        time.sleep(1)
