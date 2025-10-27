# Smart Incubator Deployment Tools Summary

Quick reference for all deployment tools and shortcuts.

---

## 🚀 Quick Commands

| What You Want | Command | Shortcut |
|---------------|---------|----------|
| **Deploy firmware changes** | `python3 Smart_incubator/sync_firmware.py` | `Cmd+Shift+B` |
| **Format SD (via ESP32)** | `python3 Smart_incubator/format_sd_card.py` | `Cmd+Shift+P` → Format SD Card |
| **Format SD (local reader)** | `python3 Smart_incubator/format_sd_card_local.py /dev/diskX` | - |
| **List local disks** | `python3 Smart_incubator/format_sd_card_local.py --list` | - |
| **Force full reinstall** | `python3 Smart_incubator/sync_firmware.py --force` | - |
| **Open REPL** | `mpremote connect PORT repl` | `Cmd+Shift+P` → Open REPL |
| **List files** | `mpremote connect PORT ls` | `Cmd+Shift+P` → List Files |
| **Reset device** | `mpremote connect PORT reset` | `Cmd+Shift+P` → Reset Device |

---

## 📦 Available Tools

### 1. Intelligent Sync (`sync_firmware.py`)
**Auto-detects changes and only uploads modified files**

```bash
# First time (blank ESP32)
python3 Smart_incubator/sync_firmware.py
# → Installs packages, creates dirs, uploads everything

# Subsequent runs
python3 Smart_incubator/sync_firmware.py
# → Only uploads changed files (fast!)

# Force complete reinstall
python3 Smart_incubator/sync_firmware.py --force
```

**Features:**
- ✅ Auto-detects ESP32 port
- ✅ Tracks file changes via SHA-256 hashing
- ✅ Handles blank ESP32 automatically
- ✅ Installs MicroPython packages from requirements
- ✅ Creates SD card directory structure
- ✅ Smart caching for fast deployments

---

### 2. SD Card Formatter - Two Options

#### Option A: Format via ESP32 (`format_sd_card.py`)
**For SD cards already in the ESP32**

```bash
# Auto-detect ESP32 port
python3 Smart_incubator/format_sd_card.py

# Specify port
python3 Smart_incubator/format_sd_card.py /dev/tty.usbserial-0001
```

**What it does:**
1. 🗑️ Removes `/sd/data/*` (all experiments)
2. 🗑️ Removes `/sd/*.json` (all configs)
3. 📁 Creates `/sd/data/markovian_experiments/`
4. 📁 Creates `/sd/configs_backup/`
5. 📊 Shows storage statistics

**When to use:**
- SD card is already in ESP32
- Quick cleanup between experiments
- Remote formatting

#### Option B: Format Locally (`format_sd_card_local.py`)
**For SD cards in your computer's SD reader**

```bash
# List available disks
python3 Smart_incubator/format_sd_card_local.py --list

# Format specific disk (macOS)
python3 Smart_incubator/format_sd_card_local.py /dev/disk4

# Format specific disk (Linux)
python3 Smart_incubator/format_sd_card_local.py /dev/sdb
```

**⚠️ WARNING: Completely erases and reformats the SD card!**

**What it does:**
1. 💾 Formats as FAT32 (DOS_FAT_32) with MBR
2. 📁 Creates `/data/markovian_experiments/`
3. 📁 Creates `/configs_backup/`
4. 📊 Shows storage statistics

**When to use:**
- Brand new SD card
- SD card needs complete reformat
- File system corruption
- Want guaranteed clean slate

**Safety features:**
- Requires typing "YES" to confirm
- Shows disk info before formatting
- Verifies disk is removable media
- Won't format system disks

---

### 3. Manual Deploy Script (`deploy.sh`)
**Traditional deployment for specific scenarios**

```bash
# Core HES modules only
./Smart_incubator/deploy.sh /dev/tty.usbserial-0001 core

# Full firmware
./Smart_incubator/deploy.sh /dev/tty.usbserial-0001 full

# Config files only
./Smart_incubator/deploy.sh /dev/tty.usbserial-0001 config-only
```

---

## 🎯 VS Code Tasks

**Press `Cmd+Shift+P` → "Tasks: Run Task" → Choose:**

| Task | What It Does | When to Use |
|------|-------------|-------------|
| **Sync Firmware (Auto)** ⭐ | Smart sync (only changed files) | Daily development |
| **Format SD Card** | Clean SD card structure | Start new experiments |
| **Deploy Core HES Modules** | Upload HES system files | Testing HES changes |
| **Deploy Full Firmware** | Upload everything | Major updates |
| **Deploy Config Files Only** | Upload JSON configs | Tweak parameters |
| **Open REPL** | Interactive Python shell | Testing/debugging |
| **Run Experiment** | Start experiment | Launch experiments |
| **List Files on Device** | Show filesystem | Check what's deployed |
| **Reset Device** | Soft reset ESP32 | Apply changes |

**Default Task:** `Cmd+Shift+B` runs "Sync Firmware (Auto)"

---

## 📋 Typical Workflows

### New ESP32 Setup
```bash
1. Flash MicroPython (one time)
   esptool.py --port PORT erase_flash
   esptool.py --port PORT write_flash -z 0x1000 firmware.bin

2. Initial deployment
   python3 Smart_incubator/sync_firmware.py
   # Will auto-detect it's first time and do full setup

3. Format SD card
   python3 Smart_incubator/format_sd_card.py

4. Test
   mpremote connect PORT repl
   >>> import markovian_hes_executor
```

### Daily Development
```bash
1. Edit code in VS Code

2. Press Cmd+Shift+B
   # Auto-syncs only changed files

3. Test in REPL
   Press Cmd+Shift+P → "Tasks: Run Task" → "Open REPL"
```

### Start New Experiment Series
```bash
1. Format SD card
   python3 Smart_incubator/format_sd_card.py
   # Type YES twice to confirm

2. Deploy new configs
   python3 Smart_incubator/sync_firmware.py
   # Or use "Deploy Config Files Only" task

3. Run experiment
   Press Cmd+Shift+P → "Tasks: Run Task" → "Run Experiment"
```

### Troubleshooting/Reset
```bash
1. Force complete reinstall
   python3 Smart_incubator/sync_firmware.py --force

2. Format SD card
   python3 Smart_incubator/format_sd_card.py

3. Reset device
   Press Cmd+Shift+P → "Tasks: Run Task" → "Reset Device"
```

---

## 🔧 Direct mpremote Commands

For quick one-off operations:

```bash
# Upload single file
mpremote connect PORT cp local.py :/remote.py

# Upload to SD card
mpremote connect PORT cp config.json :/sd/config.json

# List root files
mpremote connect PORT ls

# List SD card
mpremote connect PORT ls /sd

# Execute command
mpremote connect PORT exec "print('Hello ESP32!')"

# Run script without uploading
mpremote connect PORT run test.py

# Reset
mpremote connect PORT reset

# Mount filesystem (amazing for development!)
mpremote connect PORT mount Smart_incubator/Firmware
# Now files run from YOUR computer!
```

---

## 🆘 Troubleshooting

### Port Not Found
```bash
# Check connection
ls /dev/tty.*          # macOS
ls /dev/ttyUSB*        # Linux
mode                   # Windows

# Manual port specification
python3 Smart_incubator/sync_firmware.py /dev/tty.usbserial-0001
```

### Permission Denied (Linux)
```bash
sudo usermod -a -G dialout $USER
# Log out and back in
```

### Upload Fails
```bash
# Reset first, wait, then upload
mpremote connect PORT reset
sleep 3
python3 Smart_incubator/sync_firmware.py
```

### Out of Memory
```bash
# Check free space
mpremote connect PORT exec "import os; print(os.statvfs('/'))"

# Remove old files
mpremote connect PORT exec "import os; os.remove('/old_file.py')"

# Use compiled .mpy files (smaller)
mpy-cross Firmware/large_file.py
mpremote connect PORT cp large_file.mpy :/
```

### SD Card Issues
```bash
# Verify SD card
mpremote connect PORT exec "import os; print('/sd' in os.listdir('/'))"

# Format SD card
python3 Smart_incubator/format_sd_card.py

# Check SD card on computer
# Format as DOS_FAT_32 with MBR
```

---

## 📚 Full Documentation

- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete deployment documentation
- **[QUICK_START.md](QUICK_START.md)** - Visual workflows with examples
- **[README.md](README.md)** - Main platform documentation
- **[DEPLOYMENT_README.md](DEPLOYMENT_README.md)** - Legacy deployment notes

---

## 💡 Pro Tips

1. **Use `Cmd+Shift+B` religiously** - It's the fastest way to deploy
2. **Format SD card before big experiments** - Ensures clean data collection
3. **Check REPL regularly** - Catch issues early
4. **Use `--force` sparingly** - Only when things are broken
5. **Mount filesystem for rapid development** - No upload needed!
6. **Keep configs in version control** - Easy to track experiment parameters
7. **Use VS Code tasks** - One click for everything

---

**Happy deploying! 🚀**
