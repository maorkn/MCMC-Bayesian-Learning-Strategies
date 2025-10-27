# Deployment Mode Guide

## Problem Solved

**Issue**: Your ESP32's `boot.py` automatically runs `main.py` on startup, making it difficult to update firmware files because the running program blocks file transfers.

**Solution**: A deployment mode system that temporarily prevents auto-start during updates.

## How It Works

### The Mechanism

Your `boot.py` already includes a built-in deployment mode check:

```python
# In boot.py
if 'deployment_mode' in os.listdir('/'):
    print("=== DEPLOYMENT MODE ===")
    print("Main program will NOT auto-run")
    # Stays in REPL, doesn't run main.py
else:
    # Normal operation: runs main.py
    import main
    main.main()
```

When a file called `/deployment_mode` exists on the ESP32, `main.py` won't auto-run, allowing safe file updates.

## Using the Deployment System

### Method 1: Automatic (Recommended)

The `sync_firmware.py` script now automatically manages deployment mode:

```bash
python3 Smart_incubator/sync_firmware.py
```

**What happens:**
1. Script detects ESP32 and enables deployment mode
2. Attempts soft reset (or prompts for manual reset)
3. Uploads changed files safely
4. Asks if you want to disable deployment mode
5. If disabled, device will auto-run on next boot

### Method 2: Manual Toggle

Use the dedicated toggle script:

```bash
python3 Smart_incubator/toggle_deployment_mode.py
```

This interactive tool lets you:
- Check current deployment mode status
- Enable deployment mode (prevent auto-run)
- Disable deployment mode (allow auto-run)

### Method 3: Direct Commands

Enable deployment mode:
```bash
mpremote connect /dev/tty.YOUR_PORT exec "f = open('/deployment_mode', 'w'); f.write('SAFE'); f.close()"
```

Disable deployment mode:
```bash
mpremote connect /dev/tty.YOUR_PORT exec "import os; os.remove('/deployment_mode')"
```

Check status:
```bash
mpremote connect /dev/tty.YOUR_PORT exec "import os; print('deployment_mode' in os.listdir('/'))"
```

## Workflow Examples

### Example 1: Quick Update

```bash
# Run sync - it handles everything
python3 Smart_incubator/sync_firmware.py

# When prompted, choose 'Y' to disable deployment mode
# Device will auto-run on next reset
```

### Example 2: Development Session

```bash
# Enable deployment mode for extended development
python3 Smart_incubator/toggle_deployment_mode.py
# Choose "1" to enable

# Now you can freely update files
python3 Smart_incubator/sync_firmware.py
# Choose 'n' to keep deployment mode enabled

# Make more changes, run sync again...

# When done, disable deployment mode
python3 Smart_incubator/toggle_deployment_mode.py
# Choose "1" to disable

# Reset device to start auto-run
mpremote connect /dev/tty.YOUR_PORT reset
```

### Example 3: Emergency Manual Control

If your device is stuck or you need manual control:

```bash
# 1. Enable deployment mode remotely
mpremote connect /dev/tty.YOUR_PORT exec "f = open('/deployment_mode', 'w'); f.write('SAFE'); f.close()"

# 2. Reset device
# Press the EN button on your ESP32

# 3. Device boots but won't run main.py
# You can now safely update files

# 4. When done, disable deployment mode
mpremote connect /dev/tty.YOUR_PORT exec "import os; os.remove('/deployment_mode')"

# 5. Reset again to start normal operation
```

## Understanding the States

### Deployment Mode ENABLED
- **Status**: `/deployment_mode` file exists on device
- **Behavior**: `boot.py` runs, but `main.py` does NOT auto-run
- **Use case**: Safe for file updates, development, debugging
- **REPL access**: Available immediately after boot

### Deployment Mode DISABLED
- **Status**: `/deployment_mode` file does NOT exist
- **Behavior**: `boot.py` runs, then automatically runs `main.py`
- **Use case**: Normal operation, production use
- **REPL access**: Only available if main.py exits or crashes

## Troubleshooting

### Problem: Can't Upload Files

**Solution**: Enable deployment mode first
```bash
python3 Smart_incubator/toggle_deployment_mode.py
# Choose option to enable
# Then reset your device (press EN button)
```

### Problem: Device Won't Auto-Run After Update

**Cause**: Deployment mode is still enabled

**Solution**: Disable deployment mode
```bash
python3 Smart_incubator/toggle_deployment_mode.py
# Choose option to disable
# Then reset your device
```

### Problem: Script Says "Device May Be Running"

**Solution**: Manually reset the device
1. Press the EN (reset) button on your ESP32
2. Wait 2-3 seconds
3. Press Enter in the terminal to continue

### Problem: Lost REPL Access

If deployment mode is disabled and main.py is running:

**Option 1**: Enable deployment mode remotely, then reset
```bash
mpremote connect /dev/tty.YOUR_PORT exec "f = open('/deployment_mode', 'w'); f.write('SAFE'); f.close()"
# Press EN button on device
```

**Option 2**: Use Ctrl+C in REPL to interrupt
```bash
mpremote connect /dev/tty.YOUR_PORT repl
# Press Ctrl+C to interrupt
```

## Best Practices

1. **During Development**: Keep deployment mode ENABLED
   - Prevents accidental auto-starts
   - Makes testing easier
   - Safer file updates

2. **For Production**: Keep deployment mode DISABLED
   - Device auto-starts on power cycle
   - Runs autonomously
   - Survives power outages

3. **Before Long-Running Experiments**: Disable deployment mode
   - Ensures device restarts properly if power is lost
   - No manual intervention needed

4. **When Troubleshooting**: Enable deployment mode
   - Prevents program from interfering
   - Full REPL access
   - Can test components individually

## Quick Reference

| Action | Command |
|--------|---------|
| Auto-deploy with management | `python3 Smart_incubator/sync_firmware.py` |
| Interactive toggle | `python3 Smart_incubator/toggle_deployment_mode.py` |
| Enable manually | `mpremote exec "open('/deployment_mode','w').write('SAFE')"` |
| Disable manually | `mpremote exec "import os; os.remove('/deployment_mode')"` |
| Check status | `mpremote exec "import os; print('deployment_mode' in os.listdir('/'))"` |
| Reset device | `mpremote reset` or press EN button |

## Integration with Existing Tools

The deployment mode system is now integrated into:
- ✅ `sync_firmware.py` - Automatic management
- ✅ `toggle_deployment_mode.py` - Manual control
- ✅ `boot.py` - Built-in detection
- 🔄 Compatible with all existing mpremote commands

You can still use all your existing deployment scripts; they'll work better now with deployment mode protection!
