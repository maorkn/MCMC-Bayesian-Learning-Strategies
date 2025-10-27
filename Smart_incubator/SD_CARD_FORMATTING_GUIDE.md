# SD Card Formatting Guide

Quick guide for formatting SD cards for Smart Incubator experiments.

---

## 🎯 Which Method Should I Use?

| Scenario | Method | Command |
|----------|--------|---------|
| **New SD card** | Local formatter | `python3 format_sd_card_local.py --list` |
| **SD card needs reformat** | Local formatter | `python3 format_sd_card_local.py /dev/diskX` |
| **SD card already in ESP32** | ESP32 formatter | `python3 format_sd_card.py` |
| **Quick cleanup** | ESP32 formatter | `python3 format_sd_card.py` |
| **File system corruption** | Local formatter | `python3 format_sd_card_local.py /dev/diskX` |

---

## Method 1: Format SD Card in Computer (Recommended for New Cards)

**Best for:** Brand new SD cards, corrupted file systems, complete reformats

### Step 1: Insert SD Card
Insert SD card into your computer's SD card reader.

### Step 2: List Available Disks
```bash
cd Smart_incubator
python3 format_sd_card_local.py --list
```

**macOS Output Example:**
```
/dev/disk0 (internal, physical) - YOUR SYSTEM DISK - DON'T FORMAT!
/dev/disk3 (synthesized) - YOUR SYSTEM VOLUME - DON'T FORMAT!
/dev/disk4 (external, physical) - SD CARD - THIS IS IT!
   #:                       TYPE NAME                    SIZE       IDENTIFIER
   0:     FDisk_partition_scheme                        *32.0 GB    disk4
   1:                 DOS_FAT_32 UNTITLED                32.0 GB    disk4s1
```

⚠️ **IMPORTANT:** SD cards are usually:
- macOS: `/dev/disk4` or higher (NOT disk0, disk1, disk2, disk3)
- Linux: `/dev/sdb`, `/dev/sdc` (NOT /dev/sda)

### Step 3: Format the SD Card
```bash
# macOS example
python3 format_sd_card_local.py /dev/disk4

# Linux example  
python3 format_sd_card_local.py /dev/sdb
```

**The script will:**
1. Show disk information
2. Ask for confirmation (type `YES`)
3. Unmount the disk
4. Format as FAT32 (DOS_FAT_32) with MBR
5. Create directory structure:
   - `/data/markovian_experiments/`
   - `/configs_backup/`
6. Show storage statistics

### Step 4: Eject Safely
```bash
# macOS
diskutil eject /dev/disk4

# Linux
sudo eject /dev/sdb
```

### Step 5: Insert into ESP32
- Remove SD card from computer
- Insert into ESP32 SD card module
- Ready to deploy firmware!

---

## Method 2: Format SD Card via ESP32

**Best for:** SD card already in ESP32, quick cleanup, remote formatting

### Requirements
- SD card inserted in ESP32
- ESP32 connected via USB
- ESP32 has firmware deployed

### Steps
```bash
cd Smart_incubator

# Auto-detect ESP32 port
python3 format_sd_card.py

# Or specify port
python3 format_sd_card.py /dev/tty.usbserial-0001
```

**The script will:**
1. Check SD card is accessible
2. List existing experiment data
3. Ask for confirmation (type `YES` **twice**)
4. Delete all data and configs
5. Create fresh directory structure
6. Show storage statistics

**Note:** This method does NOT reformat the filesystem - it only clears files and recreates directories. For complete reformatting, use Method 1.

---

## 📋 After Formatting

### Deploy Firmware
```bash
# Sync firmware to ESP32
python3 sync_firmware.py

# Or use VS Code
# Press Cmd+Shift+B
```

### Copy Config Files
```bash
# Via mpremote (if SD card in ESP32)
mpremote connect PORT cp Configs/experiment.json :/sd/experiment.json

# Or via sync script (will detect new configs)
python3 sync_firmware.py
```

### Test SD Card
```bash
# Connect to REPL
mpremote connect PORT repl

# In REPL, test SD access:
>>> import os
>>> os.listdir('/sd')
['data', 'configs_backup']
>>> os.listdir('/sd/data')
['markovian_experiments']
```

---

## 🆘 Troubleshooting

### "Disk not found" (Local Format)
```bash
# Make sure SD card is inserted
# Run list command to see all disks
python3 format_sd_card_local.py --list

# Check physical connection
# Try reinserting SD card
```

### "Permission denied" (Linux)
```bash
# Use sudo for formatting operations
sudo python3 format_sd_card_local.py /dev/sdb

# Or add user to disk group
sudo usermod -a -G disk $USER
# Log out and back in
```

### "SD card not accessible" (ESP32 Format)
```bash
# Check SD card is inserted properly
# Verify SD card module is working

# Test in REPL:
>>> import os
>>> os.listdir('/')
# Should show 'sd' if SD card is mounted

# If not mounted, check wiring and sdcard.py module
```

### "Format failed" (Local)
```bash
# Disk may be in use
# Close any programs accessing the SD card
# Unmount manually:

# macOS
diskutil unmountDisk /dev/disk4

# Linux
sudo umount /dev/sdb1
sudo umount /dev/sdb2
```

### SD Card Not Recognized by ESP32
```bash
# SD card must be FAT32 (not exFAT or NTFS)
# Use local formatter to ensure correct format

# Check SD card is not too large (max 32GB for FAT32)
# For larger cards, use exFAT support or partition
```

---

## 💡 Pro Tips

1. **Always use `--list` first** - Double-check disk before formatting
2. **Label your SD cards** - Write "ESP32-1", "ESP32-2" on cards
3. **Keep spare formatted SD cards** - Quick swaps for experiments
4. **Backup experiment data** - Copy `/sd/data/` before formatting
5. **Use quality SD cards** - Cheap cards fail more often
6. **Format on computer when possible** - More reliable than ESP32 formatting
7. **Check filesystem regularly** - Run filesystem check on computer monthly

---

## 📊 Recommended SD Card Specs

- **Capacity:** 4GB - 32GB (FAT32 limit)
- **Class:** Class 10 or UHS-I
- **Brand:** SanDisk, Samsung, Kingston (reliable brands)
- **Format:** FAT32 (DOS_FAT_32)
- **Partition:** MBR (not GPT)

---

## 🔗 Related Documentation

- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Complete deployment workflow
- [DEPLOYMENT_TOOLS_SUMMARY.md](DEPLOYMENT_TOOLS_SUMMARY.md) - All tools reference
- [QUICK_START.md](QUICK_START.md) - Visual workflow guides

---

**Ready to format? 💾**

**Method 1 (Local):**
```bash
python3 Smart_incubator/format_sd_card_local.py --list
python3 Smart_incubator/format_sd_card_local.py /dev/diskX
```

**Method 2 (ESP32):**
```bash
python3 Smart_incubator/format_sd_card.py
```
