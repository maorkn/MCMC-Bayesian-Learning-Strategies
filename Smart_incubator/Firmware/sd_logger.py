# sd_logger.py - Enhanced SD Card Logging Module
from machine import Pin, SPI
import os
import json
import time
import sdcard
import hashlib
import machine
import ubinascii

# ---- CONSTANTS ----
DATA_ROOT = '/sd/data'  # Change to '/flash/data' for SPIFFS
MANIFEST_UPDATE_INTERVAL = 5  # Update manifest every N writes

# ---- PIN DEFINITIONS ----
CS_SD = 15    # SD Card Chip Select (HSPI)
SCK_PIN = 14  # HSPI Clock
MOSI_PIN = 13 # HSPI MOSI
MISO_PIN = 12 # HSPI MISO

# ---- GLOBAL VARIABLES ----
spi = None
cs_sd = None
sd = None
current_experiment = None
firmware_version = "1.0.0"  # Update this with your version
write_count = 0  # Track writes for manifest updates

class ExperimentLogger:
    def __init__(self, meta_data=None):
        """Initialize experiment logger with metadata."""
        # Convert meta_data to a simple dict with only basic types
        self.meta_data = {}
        if meta_data:
            for key, value in meta_data.items():
                try:
                    # Try to convert to basic types
                    if isinstance(value, (int, float, str, bool)):
                        self.meta_data[key] = value
                    elif isinstance(value, (list, tuple)):
                        self.meta_data[key] = [str(x) for x in value]
                    elif isinstance(value, dict):
                        self.meta_data[key] = {str(k): str(v) for k, v in value.items()}
                    else:
                        self.meta_data[key] = str(value)
                except Exception as e:
                    print(f"[WARNING] Could not convert {key} to basic type: {e}")
                    self.meta_data[key] = str(value)
        
        self.experiment_id = self._generate_experiment_id()
        self.base_path = f'{DATA_ROOT}/{self.experiment_id}'
        self.manifest = {
            'experiment_id': str(self.experiment_id),
            'start_time': str(self._get_timestamp()),
            'files': [],
            'status': 'init',
            'error': None
        }
        self.write_count = 0
        self.snapshot_count = 0  # Track total snapshots logged
        
    def _generate_experiment_id(self):
        """Generate experiment ID with date and correlation."""
        try:
            correlation = float(self.meta_data.get('correlation', 1))
            timestamp = time.time()
            # Format: DDMMYYYY_corr
            return f"{int(timestamp/86400)}_{int(correlation)}"
        except Exception as e:
            print(f"[WARNING] Error generating experiment ID: {e}")
            return f"{int(time.time()/86400)}_1"
    
    def _get_timestamp(self):
        """Return Unix timestamp (integer seconds since epoch). Using a simple integer guarantees filenames without invalid FAT characters."""
        return int(time.time())
    
    def _ensure_directory(self):
        """Ensure experiment directory exists."""
        try:
            # Create data directory if it doesn't exist
            try:
                os.mkdir(DATA_ROOT)
            except OSError as e:
                if e.args[0] != 17:  # Ignore "directory exists" error
                    raise
            
            # Create experiment directory
            try:
                os.mkdir(self.base_path)
            except OSError as e:
                if e.args[0] != 17:  # Ignore "directory exists" error
                    raise
            return True
        except Exception as e:
            print(f"[ERROR] Failed to create directory: {e}")
            return False
    
    def _calculate_checksum(self, filepath):
        """Calculate SHA-256 checksum of file contents in a MicroPython-compatible way."""
        try:
            h = hashlib.sha256()
            with open(filepath, 'rb') as f:
                while True:
                    chunk = f.read(512)
                    if not chunk:
                        break
                    h.update(chunk)
            # MicroPython's sha256 object may lack hexdigest(); use ubinascii.hexlify
            return ubinascii.hexlify(h.digest()).decode()
        except Exception as e:
            print(f"[ERROR] Failed to calculate checksum: {e}")
            return None
    
    def _update_manifest(self, force=False):
        """Update manifest.json file."""
        global write_count
        write_count += 1
        
        if force or write_count % MANIFEST_UPDATE_INTERVAL == 0:
            try:
                # Limit manifest file list to last 100 entries to prevent memory buildup
                if len(self.manifest['files']) > 100:
                    self.manifest['files'] = self.manifest['files'][-100:]
                    
                with open(f'{self.base_path}/manifest.json', 'w') as f:
                    json.dump(self.manifest, f)
                write_count = 0  # Reset counter after successful write
            except Exception as e:
                print(f"[ERROR] Failed to update manifest: {e}")
    
    def init_experiment(self):
        """Initialize experiment directory and meta.json."""
        if not self._ensure_directory():
            return False
            
        # Create meta.json with only basic types
        try:
            meta = {
                'experiment_id': str(self.experiment_id),
                'firmware': str(firmware_version),
                'start_time': str(self._get_timestamp()),
                'parameters': self.meta_data
            }
            
            with open(f'{self.base_path}/meta.json', 'w') as f:
                json.dump(meta, f)
            return True
        except Exception as e:
            print(f"[ERROR] Failed to create meta.json: {e}")
            return False
    
    def log_snapshot(self, cycle_num, data):
        """Log a single data snapshot."""
        timestamp = self._get_timestamp()
        filename = f'cycle_{cycle_num}_{timestamp}.json'
        
        # Convert data to basic types
        safe_data = {}
        for key, value in data.items():
            if isinstance(value, (int, float, str, bool)):
                safe_data[key] = value
            else:
                safe_data[key] = str(value)
        
        # Add common fields
        safe_data.update({
            'experiment_id': self.experiment_id,
            'firmware': firmware_version,
            'timestamp': timestamp,
            'cycle_num': cycle_num
        })
        
        try:
            filepath = f'{self.base_path}/{filename}'
            
            # Try writing with retries
            max_retries = 3
            for retry in range(max_retries):
                try:
                    with open(filepath, 'w') as f:
                        json.dump(safe_data, f)
                    break  # Success, exit retry loop
                except OSError as e:
                    if retry < max_retries - 1:
                        time.sleep(0.1)  # Brief delay before retry
                        continue
                    else:
                        raise  # Re-raise on final attempt
            
            # Calculate checksum from file contents
            checksum = self._calculate_checksum(filepath)
            if checksum:
                # Update manifest
                file_info = {
                    'filename': filename,
                    'checksum': checksum,
                    'size': self._get_file_size(filepath),
                    'timestamp': timestamp
                }
                self.manifest['files'].append(file_info)
                self._update_manifest()
            
            # Commented out to prevent output flooding
            # print(f"[EXP:{self.experiment_id}] Logged cycle {cycle_num} snapshot")
            self.snapshot_count += 1
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to log snapshot: {e}")
            return False
    
    def log_cycle_summary(self, cycle_num, summary_data):
        """Log end-of-cycle summary."""
        filename = f'cycle_{cycle_num}_summary.json'
        timestamp = self._get_timestamp()  # Get timestamp once
        
        # Convert summary_data to basic types
        safe_summary = {}
        for key, value in summary_data.items():
            if isinstance(value, (int, float, str, bool)):
                safe_summary[key] = value
            else:
                safe_summary[key] = str(value)
        
        # Add common fields
        safe_summary.update({
            'experiment_id': self.experiment_id,
            'firmware': firmware_version,
            'timestamp': timestamp,
            'cycle_num': cycle_num
        })
        
        try:
            filepath = f'{self.base_path}/{filename}'
            
            # Try writing with retries
            max_retries = 3
            for retry in range(max_retries):
                try:
                    with open(filepath, 'w') as f:
                        json.dump(safe_summary, f)
                    break  # Success, exit retry loop
                except OSError as e:
                    if retry < max_retries - 1:
                        time.sleep(0.1)  # Brief delay before retry
                        continue
                    else:
                        raise  # Re-raise on final attempt
            
            # Calculate checksum from file contents
            checksum = self._calculate_checksum(filepath)
            if checksum:
                # Update manifest
                file_info = {
                    'filename': filename,
                    'checksum': checksum,
                    'size': self._get_file_size(filepath),
                    'timestamp': timestamp
                }
                self.manifest['files'].append(file_info)
                self._update_manifest()
            
            # Keep this print - it only happens once per cycle
            print(f"[EXP:{self.experiment_id}] Logged cycle {cycle_num} summary ({self.snapshot_count} snapshots)")
            self.snapshot_count = 0  # Reset for next cycle
            return True
            
        except Exception as e:
            print(f"[ERROR] Failed to log cycle summary: {e}")
            return False
    
    def finalize_experiment(self, status='completed', error=None):
        """Finalize experiment and create manifest.json."""
        self.manifest.update({
            'end_time': self._get_timestamp(),
            'status': status,
            'error': str(error) if error else None
        })
        
        try:
            with open(f'{self.base_path}/manifest.json', 'w') as f:
                json.dump(self.manifest, f)
            print(f"[EXP:{self.experiment_id}] Experiment {status}")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to create manifest.json: {e}")
            return False

    def _get_file_size(self, filepath):
        """Return file size in bytes using os.stat (compatible with MicroPython)."""
        try:
            return os.stat(filepath)[6]  # size field
        except Exception as e:
            print(f"[WARNING] Failed to get file size: {e}")
            return 0

def init_sd():
    """Initialize and mount the SD card."""
    global spi, cs_sd, sd
    
    try:
        print("[SPI] Initializing SPI for SD card...")
        print(f"[Debug] SD pins - CS: {CS_SD}, SCK: {SCK_PIN}, MOSI: {MOSI_PIN}, MISO: {MISO_PIN}")
        
        spi = SPI(1,  # Use HSPI
                  sck=Pin(SCK_PIN),
                  mosi=Pin(MOSI_PIN),
                  miso=Pin(MISO_PIN),
                  baudrate=1000000)
        cs_sd = Pin(CS_SD, Pin.OUT)
        cs_sd.value(1)  # Deselect SD card
        print("[SPI] SPI bus and CS pin initialized")
        
        # Add delay for SD card to stabilize
        time.sleep_ms(100)
        
        print("[SD] Initializing SD card...")
        sd = sdcard.SDCard(spi, cs_sd)
        print("[SD] SD card object created successfully")
        
        print("[SD] Mounting filesystem...")
        os.mount(sd, '/sd')
        print("[SD] Filesystem mounted successfully")
        
        # Create data directory if it doesn't exist
        try:
            print("[SD] Creating data directory...")
            os.mkdir(DATA_ROOT)
            print("[SD] Data directory created")
        except OSError as e:
            if e.args[0] != 17:  # Ignore "directory exists" error
                print(f"[ERROR] Failed to create data directory: {e}")
                raise
            else:
                print("[SD] Data directory already exists")
        
        print("[SD] Mounted Successfully.")
        return True
        
    except Exception as e:
        print(f"[ERROR] SD card initialization failed: {e}")
        print(f"[Debug] Error type: {type(e)}")
        return False

def deinit():
    """Clean up SD card and SPI resources."""
    global spi, cs_sd, sd
    
    try:
        if sd is not None:
            os.umount('/sd')
            sd = None
        if spi is not None:
            spi.deinit()
            spi = None
        if cs_sd is not None:
            cs_sd.value(1)  # Deselect SD card
            cs_sd = None
    except Exception as e:
        print(f"[ERROR] Cleanup failed: {e}")

# ---- TEST CODE ----
if __name__ == "__main__":
    if init_sd():
        # Test the new logging system
        logger = ExperimentLogger({
            'basal_temp': 23.0,
            'heat_shock_temp': 32.0,
            'us_type': "BOTH"
        })
        
        if logger.init_experiment():
            # Log a test snapshot
            logger.log_snapshot(1, {
                'temp': 25.5,
                'set_temp': 23.0,
                'us_active': 1,
                'power': 50.0
            })
            
            # Log a test summary
            logger.log_cycle_summary(1, {
                'avg_temp': 25.2,
                'max_temp': 26.0,
                'min_temp': 24.5,
                'us_count': 5
            })
            
            # Finalize experiment
            logger.finalize_experiment()
        
        deinit()
