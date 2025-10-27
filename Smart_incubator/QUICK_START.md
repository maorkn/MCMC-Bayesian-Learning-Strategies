# Smart Incubator Deployment - Visual Workflow

## 🆕 First Time Setup (Blank ESP32)

```
┌─────────────────────────────────────────────────────────────┐
│  1. Flash MicroPython (One Time)                            │
├─────────────────────────────────────────────────────────────┤
│  $ esptool.py --port /dev/tty.usbserial-0001 erase_flash    │
│  $ esptool.py --port PORT write_flash -z 0x1000 esp32.bin   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  2. Run Smart Sync                                          │
├─────────────────────────────────────────────────────────────┤
│  $ python3 Smart_incubator/sync_firmware.py                 │
│                                                              │
│  🆕 FIRST TIME SETUP DETECTED                               │
│  📦 Installing MicroPython packages... (from requirements)   │
│  📁 Creating SD directories... (/sd/data/...)               │
│  📤 Uploading ALL 15 files...                               │
│     ✓ markovian_hes_executor.py                             │
│     ✓ hes_config_loader.py                                  │
│     ✓ ... (all firmware files)                              │
│  ✅ Initial deployment complete!                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  3. Test                                                     │
├─────────────────────────────────────────────────────────────┤
│  $ mpremote connect PORT repl                                │
│  >>> import markovian_hes_executor                           │
│  >>> # Success! 🎉                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Daily Development (Existing ESP32)

```
┌─────────────────────────────────────────────────────────────┐
│  1. Edit Code in VS Code                                    │
├─────────────────────────────────────────────────────────────┤
│  # Made changes to:                                          │
│  - hes_transition_engine.py (updated probability calc)       │
│  - Configs/my_experiment.json (tweaked parameters)           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  2. Press Cmd+Shift+B (Smart Sync)                          │
├─────────────────────────────────────────────────────────────┤
│  🔍 Scanning for changes...                                  │
│  📦 Found 2 changed files:                                   │
│     📤 hes_transition_engine.py → /hes_transition_engine.py │
│     📤 my_experiment.json → /sd/my_experiment.json          │
│  ✅ Deployment complete! (2/2 successful)                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  3. Test in REPL                                             │
├─────────────────────────────────────────────────────────────┤
│  Press Cmd+Shift+P → "Tasks: Run Task" → "Open REPL"        │
│  >>> import markovian_hes_executor                           │
│  >>> markovian_hes_executor.run_experiment('/sd/test.json') │
└─────────────────────────────────────────────────────────────┘
```

---

## 💾 Format SD Card (Clean Slate)

**⚠️ Warning: Deletes all experiment data!**

```
┌─────────────────────────────────────────────────────────────┐
│  When to use:                                                │
├─────────────────────────────────────────────────────────────┤
│  • Starting new experiment series                            │
│  • SD card full of old data                                  │
│  • Corrupted experiment files                                │
│  • Want fresh start                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Method 1: VS Code Task (Easiest)                           │
├─────────────────────────────────────────────────────────────┤
│  Press Cmd+Shift+P → "Tasks: Run Task" → "Format SD Card"   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Method 2: Command Line                                      │
├─────────────────────────────────────────────────────────────┤
│  $ python3 Smart_incubator/format_sd_card.py                │
│                                                              │
│  💾 SD CARD FORMATTER FOR MARKOVIAN EXPERIMENTS             │
│  ⚠️  WARNING: This will:                                    │
│    1. Remove ALL existing experiment data                    │
│    2. Clear all config files from SD card                    │
│    3. Create fresh directory structure                       │
│    4. Keep system files intact (boot.py, main.py, etc.)      │
│                                                              │
│  ⚠️  Are you ABSOLUTELY SURE? Type 'YES' to proceed: YES    │
│                                                              │
│  🔧 Starting SD card format...                               │
│  📋 Checking SD card... ✅ SD card detected                  │
│  📋 Scanning existing data...                                │
│      Found 3 experiments to delete:                          │
│        - 20251014_143022_Experiment                          │
│        - 20251015_091503_Test                                │
│        - 20251016_120045_Final                               │
│                                                              │
│  ⚠️  Continue with deletion? Type 'YES' again: YES          │
│                                                              │
│  🗑️  Removing old experiment data... ✅ Old data removed    │
│  🗑️  Removing old config files... ✅ Removed 2 config files │
│  📁 Creating fresh directory structure...                    │
│      ✅ Created /sd/data                                     │
│      ✅ Created /sd/data/markovian_experiments               │
│      ✅ Created /sd/configs_backup                           │
│                                                              │
│  🔍 Verifying SD card structure...                           │
│  /                                                           │
│    📁 data/                                                  │
│      📁 markovian_experiments/                               │
│    📁 configs_backup/                                        │
│                                                              │
│  💾 SD Card Space:                                           │
│    Total: 1024.0 MB                                          │
│    Used: 2.1 MB                                              │
│    Free: 1021.9 MB                                           │
│                                                              │
│  ✅ SD CARD FORMAT COMPLETE!                                │
│                                                              │
│  📋 Next steps:                                              │
│    1. Deploy config files: python3 sync_firmware.py          │
│    2. Or manually copy configs                               │
│    3. Run experiment via VS Code task                        │
│                                                              │
│  🎉 Ready for experiments!                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Run Experiment
└─────────────────────────────────────────────────────────────┘
```

---

## 🔬 Daily Development (Existing ESP32)

```
┌─────────────────────────────────────────────────────────────┐
│  1. Edit Code in VS Code                                    │
├─────────────────────────────────────────────────────────────┤
│  # Made changes to:                                          │
│  - hes_transition_engine.py (updated probability calc)       │
│  - Configs/my_experiment.json (tweaked parameters)           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  2. Press Cmd+Shift+B (or run sync)                         │
├─────────────────────────────────────────────────────────────┤
│  🔍 Scanning for changes...                                  │
│  📦 Found 2 changed file(s):                                 │
│    📤 hes_transition_engine.py → /                           │
│    📤 my_experiment.json → /sd/                              │
│  ✅ Deployment complete! (2/2 successful)                   │
│                                                              │
│  ⏱️  Total time: 3 seconds (vs. 45 sec full upload!)        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  3. Test Changes                                             │
├─────────────────────────────────────────────────────────────┤
│  $ mpremote connect PORT repl                                │
│  >>> import sys                                              │
│  >>> del sys.modules['hes_transition_engine']  # Reload      │
│  >>> import markovian_hes_executor                           │
│  >>> markovian_hes_executor.run_experiment('/sd/test.json')  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Force Reinstall (Something Broke)

```
┌─────────────────────────────────────────────────────────────┐
│  $ python3 Smart_incubator/sync_firmware.py --force         │
├─────────────────────────────────────────────────────────────┤
│  🔄 Force reinstall mode - treating as new ESP32             │
│                                                              │
│  [Same as first time setup, reinstalls everything]          │
│                                                              │
│  ✅ Complete reinstall finished!                            │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Comparison: Old vs. New Method

### OLD METHOD (Thonny Copy-Paste)
```
┌───────────────────────────────────────────┐
│ Time: ~5-10 minutes per update            │
│ Steps: 15-20 manual copy-pastes           │
│ Error-prone: High (easy to miss files)    │
│ Tracking: Manual (what did I update?)     │
│ First setup: Same tedious process         │
└───────────────────────────────────────────┘
```

### NEW METHOD (Smart Sync)
```
┌───────────────────────────────────────────┐
│ Time: 3-5 seconds for changed files       │
│       30-60 seconds for first setup       │
│ Steps: 1 command (or 1 keystroke!)        │
│ Error-prone: None (automated hashing)     │
│ Tracking: Automatic cache system          │
│ First setup: Fully automated              │
└───────────────────────────────────────────┘
```

**Speed improvement: 50-100x faster!** ⚡

---

## 🎯 When to Use Each Method

| Scenario | Recommended Method | Command |
|----------|-------------------|---------|
| **Brand new ESP32** | Smart sync (auto-detects) | `python3 sync_firmware.py` |
| **Daily coding** | VS Code task | `Cmd+Shift+B` |
| **Quick single file** | mpremote direct | `mpremote connect PORT cp file.py :/` |
| **Test without upload** | Mount filesystem | `mpremote connect PORT mount .` |
| **Something broke** | Force reinstall | `python3 sync_firmware.py --force` |
| **Deploy experiment** | VS Code task | "Run Experiment" task |
| **Debug on device** | REPL | `mpremote connect PORT repl` |

---

## 💡 Pro Tips

### 1. **Use VS Code Tasks for Everything**
```
Cmd+Shift+P → "Tasks: Run Task" → Choose:
  - Sync Firmware (Auto)      ← Daily use
  - Open REPL                  ← Debugging
  - Run Experiment             ← Start experiment
  - List Files on Device       ← Check what's on ESP32
  - Reset Device               ← Restart
```

### 2. **Mount Local Files for Rapid Testing**
```bash
# No upload needed! ESP32 reads from your computer
mpremote connect PORT mount Smart_incubator/Firmware

# In REPL:
>>> import markovian_hes_executor  # Reads from your local drive!
```

### 3. **Add Packages to Requirements**
```bash
# Edit: Smart_incubator/micropython_requirements.txt
# Add line: micropython-ssd1306

# Next sync will auto-install it!
python3 Smart_incubator/sync_firmware.py
```

### 4. **Check What Changed**
```bash
# Before syncing, see what will upload:
git status                    # Changed files
git diff file.py             # See changes
python3 sync_firmware.py     # Auto-detects changes
```

### 5. **Quick REPL Access**
```bash
# Add to your ~/.zshrc or ~/.bashrc:
alias esp32="mpremote connect /dev/tty.usbserial-0001 repl"

# Now just type:
esp32
```

---

## 🆘 Troubleshooting Quick Guide

| Problem | Solution |
|---------|----------|
| **Port not found** | `ls /dev/tty.*` to find port, may need drivers |
| **Upload fails** | Try `mpremote connect PORT reset` first |
| **Out of memory** | Delete old files or use `.mpy` compiled files |
| **Files not updating** | Use `--force` flag or delete cache file |
| **SD card not found** | Check SD card is inserted, try re-mount |
| **Package install fails** | Check internet connection, try manual install |

---

## ✅ Quick Start Checklist

For your first ESP32:

- [ ] Install tools: `pip install mpremote esptool`
- [ ] Download MicroPython firmware for ESP32
- [ ] Flash firmware: `esptool.py --port PORT erase_flash && write_flash...`
- [ ] Run: `python3 Smart_incubator/sync_firmware.py`
- [ ] Wait for "✅ Initial deployment complete!"
- [ ] Test: `mpremote connect PORT repl`
- [ ] Success! 🎉

For daily development:
- [ ] Edit files in VS Code
- [ ] Press `Cmd+Shift+B`
- [ ] Test in REPL
- [ ] Repeat!

**You're all set! Happy coding! 🚀**
