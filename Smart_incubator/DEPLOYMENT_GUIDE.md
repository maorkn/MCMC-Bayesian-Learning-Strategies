# Smart Incubator Deployment Guide

## Quick Start: Choose Your Method

### Method 1: Intelligent Sync (⭐ Recommended)
**Auto-detects changes and only uploads modified files**

```bash
# First time (blank ESP32): Installs packages & uploads everything
python3 Smart_incubator/sync_firmware.py

# Subsequent runs: Only syncs changed files
python3 Smart_incubator/sync_firmware.py

# Force complete reinstall (if needed)
python3 Smart_incubator/sync_firmware.py --force
```

**How it works:**
- 🆕 **First Run (Blank ESP32):**
  1. Detects no firmware present
  2. Installs required MicroPython packages
  3. Creates SD card directory structure
  4. Uploads ALL firmware files
  5. Uploads ALL config files
  6. Marks ESP32 as initialized

- 🔄 **Subsequent Runs:**
  1. Checks file hashes against cache
  2. Only uploads changed files
  3. Updates cache

**Advantages:**
- ✅ Handles blank ESP32 automatically
- ✅ Only uploads changed files (fast!)
- ✅ Auto-detects ESP32 port
- ✅ Maintains deployment cache
- ✅ No manual tracking needed

---

### Method 2: VS Code Tasks (⭐⭐ Best for Development)
**One-click deployment from VS Code**

1. Press `Cmd+Shift+P` (Mac) or `Ctrl+Shift+P` (Windows/Linux)
2. Type "Tasks: Run Task"
3. Choose:
   - **Sync Firmware (Auto)** - Smart sync (recommended)
   - **Deploy Core HES Modules** - Only HES files
   - **Deploy Full Firmware** - Everything
   - **Deploy Config Files Only** - Just JSON configs
   - **Format SD Card** - ⚠️ Clear SD card and create fresh structure
   - **Open REPL** - Interactive Python shell
   - **Run Experiment** - Start experiment directly

**Keyboard Shortcut:**
- `Cmd+Shift+B` - Runs default task (Smart Sync)

---

### Method 3: Manual Script
**For when you want control**

```bash
# Core HES modules only
./Smart_incubator/deploy.sh /dev/tty.usbserial-0001 core

# Full firmware update
./Smart_incubator/deploy.sh /dev/tty.usbserial-0001 full

# Config files only
./Smart_incubator/deploy.sh /dev/tty.usbserial-0001 config-only
```

---

### Method 4: Direct mpremote Commands
**For quick single-file updates**

```bash
# Upload single file
mpremote connect /dev/tty.usbserial-0001 cp Firmware/main.py :/main.py

# Upload config
mpremote connect /dev/tty.usbserial-0001 cp Configs/experiment.json :/sd/experiment.json

# Run without uploading (test before deploy)
mpremote connect /dev/tty.usbserial-0001 run test_script.py

# Execute Python command
mpremote connect /dev/tty.usbserial-0001 exec "print('Hello from ESP32!')"
```

---

## Installation: One-Time Setup

### Install Required Tools

```bash
# Install Python tools
pip install mpremote adafruit-ampy rshell

# Verify installation
mpremote version
ampy --help
rshell version
```

### Find Your ESP32 Port

**macOS:**
```bash
ls /dev/tty.usbserial* /dev/tty.SLAB_USBtoUART
# Output: /dev/tty.usbserial-0001
```

**Linux:**
```bash
ls /dev/ttyUSB* /dev/ttyACM*
# Output: /dev/ttyUSB0
```

**Windows:**
```bash
# Use Device Manager or:
mode
# Output: COM3, COM4, etc.
```

---

## Common Workflows

### Workflow 0: Format SD Card for New Experiment

**⚠️ Warning: This deletes all existing experiment data!**

```bash
# Method 1: Using the script (auto-detects port)
python3 Smart_incubator/format_sd_card.py

# Method 2: Using VS Code task
# Press Cmd+Shift+P → "Tasks: Run Task" → "Format SD Card"

# Method 3: Manual port specification
python3 Smart_incubator/format_sd_card.py /dev/tty.usbserial-0001
```

**What it does:**
- 🗑️ Removes all experiment data from `/sd/data/`
- 🗑️ Removes all config files from `/sd/`
- 📁 Creates fresh directory structure:
  - `/sd/data/markovian_experiments/`
  - `/sd/configs_backup/`
- ✅ Keeps system files intact (boot.py, main.py, etc.)
- 📊 Shows storage statistics

**When to use:**
- Starting a new series of experiments
- SD card is full of old data
- Corrupted experiment files
- Want a clean slate

**Safety features:**
- Requires typing "YES" twice to confirm
- Shows what will be deleted before proceeding
- Auto-detects ESP32 port
- Verifies SD card is accessible

---

### Workflow 1: Brand New ESP32 Setup

```bash
# 1. Flash MicroPython firmware (one time)
esptool.py --port /dev/tty.usbserial-0001 erase_flash
esptool.py --port /dev/tty.usbserial-0001 write_flash -z 0x1000 esp32-micropython.bin

# 2. Run sync script (auto-detects blank ESP32)
python3 Smart_incubator/sync_firmware.py

# Output will show:
# 🆕 FIRST TIME SETUP DETECTED
# 📦 Installing MicroPython packages...
# 📁 Creating SD card directories...
# 📤 Uploading ALL firmware files...
# ✅ Initial deployment complete!

# 3. Test
mpremote connect /dev/tty.usbserial-0001 repl
>>> import markovian_hes_executor
>>> # Success!
```

### Workflow 2: Daily Development Cycle

```bash
# 1. Edit files in VS Code
# 2. Press Cmd+Shift+B (auto-sync changed files)
# 3. Press Cmd+Shift+P → "Tasks: Run Task" → "Open REPL"
# 4. Test in REPL:
>>> import markovian_hes_executor
>>> markovian_hes_executor.run_experiment('/sd/test.json')
```

### Workflow 3: Deploy New Experiment

```bash
# 1. Create config file: Configs/my_experiment.json
# 2. Deploy config only:
./Smart_incubator/deploy.sh /dev/tty.usbserial-0001 config-only

# 3. Run via VS Code task "Run Experiment"
# Or manually:
mpremote connect /dev/tty.usbserial-0001 exec "import markovian_hes_executor; markovian_hes_executor.run_experiment('/sd/my_experiment.json')"
```

### Workflow 3: Debug Issue on Device

```bash
# 1. Connect to REPL
mpremote connect /dev/tty.usbserial-0001 repl

# 2. In REPL:
>>> import os
>>> os.listdir('/')           # List root files
>>> os.listdir('/sd')          # List SD card files

# 3. Check logs
>>> with open('/sd/data/latest_experiment/hes_sequence.json') as f:
...     print(f.read())

# 4. Test individual module
>>> import hes_config_loader
>>> config = hes_config_loader.load_config('/sd/test.json')
>>> print(config)
```

### Workflow 4: Debug Issue on Device

```bash
# 1. Connect to REPL
mpremote connect /dev/tty.usbserial-0001 repl

# 2. In REPL:
>>> import os
>>> os.listdir('/')           # List root files
>>> os.listdir('/sd')          # List SD card files

# 3. Check logs
>>> with open('/sd/data/latest_experiment/hes_sequence.json') as f:
...     print(f.read())

# 4. Test individual module
>>> import hes_config_loader
>>> config = hes_config_loader.load_config('/sd/test.json')
>>> print(config)
```

### Workflow 5: Reset Everything (Corrupt Firmware)

```bash
# 1. Force complete reinstall
python3 Smart_incubator/sync_firmware.py --force

# This will:
# - Clear deployment cache
# - Reinstall all packages
# - Re-upload all files
# - Recreate directories

# 2. Or manually erase and start fresh:
# Erase all files
mpremote connect /dev/tty.usbserial-0001 exec "import os; [os.remove(f) for f in os.listdir('/') if f.endswith('.py')]"

# Deploy fresh firmware
./Smart_incubator/deploy.sh /dev/tty.usbserial-0001 full

# Reset device
mpremote connect /dev/tty.usbserial-0001 reset
```

---

## Advanced Features

### Mount Local Filesystem (⭐ AMAZING!)

```bash
# Your local files appear on the ESP32!
mpremote connect /dev/tty.usbserial-0001 mount Smart_incubator/Firmware

# Now in REPL:
>>> import markovian_hes_executor  # Runs from YOUR computer!
```

**Use case:** Rapid development without uploading

### Auto-Run on Boot

Edit `boot.py`:
```python
# boot.py
import markovian_hes_executor
markovian_hes_executor.run_experiment('/sd/auto_experiment.json')
```

Deploy:
```bash
mpremote connect /dev/tty.usbserial-0001 cp Firmware/boot.py :/boot.py
mpremote connect /dev/tty.usbserial-0001 reset
```

### Continuous Sync (Watch Mode)

```bash
# Install watchdog
pip install watchdog

# Run auto-sync on file changes
python3 -c "
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import subprocess

class SyncHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            print(f'🔄 Detected change: {event.src_path}')
            subprocess.run(['python3', 'Smart_incubator/sync_firmware.py'])

observer = Observer()
observer.schedule(SyncHandler(), 'Smart_incubator/Firmware', recursive=True)
observer.start()
print('👀 Watching for changes... (Ctrl+C to stop)')
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
"
```

---

## Troubleshooting

### Issue: Port Not Found
```bash
# Check USB connection
ls /dev/tty.* 

# Check drivers (macOS/Linux)
# May need CH340 or CP2102 drivers

# Windows: Install USB-to-Serial drivers from manufacturer
```

### Issue: Permission Denied (Linux)
```bash
# Add user to dialout group
sudo usermod -a -G dialout $USER
# Log out and back in

# Or use sudo
sudo mpremote connect /dev/ttyUSB0 ls
```

### Issue: Upload Fails
```bash
# 1. Reset device first
mpremote connect /dev/tty.usbserial-0001 reset

# 2. Wait 3 seconds, then upload
sleep 3 && mpremote connect /dev/tty.usbserial-0001 cp file.py :/

# 3. If still fails, erase flash and re-flash MicroPython
esptool.py --port /dev/tty.usbserial-0001 erase_flash
esptool.py --port /dev/tty.usbserial-0001 write_flash -z 0x1000 esp32-micropython.bin
```

### Issue: Out of Memory
```bash
# Check free space
mpremote connect /dev/tty.usbserial-0001 exec "import os; print(os.statvfs('/'))"

# Remove old files
mpremote connect /dev/tty.usbserial-0001 exec "import os; os.remove('/old_file.py')"

# Or use compiled .mpy files (smaller)
mpy-cross Firmware/markovian_hes_executor.py
mpremote connect /dev/tty.usbserial-0001 cp markovian_hes_executor.mpy :/
```

---

## File Structure on ESP32

```
/                           # Root filesystem (flash)
├── boot.py                 # Runs on every boot
├── main.py                 # Runs after boot.py
├── markovian_hes_executor.py
├── hes_config_loader.py
├── hes_transition_engine.py
├── hes_actuator_controller.py
├── hes_logger.py
├── temp_controller.py
├── led_control.py
└── ... (other firmware files)

/sd/                        # SD card
├── experiment.json         # Config files
├── test_config.json
└── data/                   # Experiment data
    └── 20251014_143022_Experiment/
        ├── config.json
        ├── hes_sequence.json
        ├── actuator_timeseries.json
        └── ...
```

---

## Quick Reference Card

| Task | Command |
|------|---------|
| **First time setup** | `python3 Smart_incubator/sync_firmware.py` |
| **Smart sync** | `python3 Smart_incubator/sync_firmware.py` |
| **Force reinstall** | `python3 Smart_incubator/sync_firmware.py --force` |
| **Format SD card** | `python3 Smart_incubator/format_sd_card.py` |
| **VS Code deploy** | `Cmd+Shift+B` |
| **VS Code format SD** | `Cmd+Shift+P` → Tasks → Format SD Card |
| **Upload file** | `mpremote connect PORT cp local.py :/remote.py` |
| **Open REPL** | `mpremote connect PORT repl` |
| **List files** | `mpremote connect PORT ls` |
| **Run script** | `mpremote connect PORT run script.py` |
| **Execute command** | `mpremote connect PORT exec "print('hi')"` |
| **Reset device** | `mpremote connect PORT reset` |
| **Mount filesystem** | `mpremote connect PORT mount .` |

---

## Next Steps

### For Brand New ESP32:
1. **Flash MicroPython:** `esptool.py --port PORT erase_flash && esptool.py --port PORT write_flash -z 0x1000 firmware.bin`
2. **Initial setup:** `python3 Smart_incubator/sync_firmware.py`
3. **Test:** `mpremote connect PORT repl`

### For Existing ESP32:
1. **Install tools:** `pip install mpremote`
2. **Find port:** `ls /dev/tty.*`
3. **Sync changes:** Press `Cmd+Shift+B` in VS Code

**Happy coding! 🚀**
