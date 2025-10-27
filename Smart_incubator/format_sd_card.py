#!/usr/bin/env python3
"""
Smart Incubator SD Card Formatter
Prepares SD card with proper directory structure for experiments

⚠️  WARNING: This deletes ALL existing experiment data!

Usage:
    # Auto-detect ESP32 port
    python3 Smart_incubator/format_sd_card.py
    
    # Specify port manually
    python3 Smart_incubator/format_sd_card.py /dev/tty.usbserial-0001
    
    # From VS Code
    Press Cmd+Shift+P → "Tasks: Run Task" → "Format SD Card"

What it does:
    - 🗑️  Removes all experiment data from /sd/data/
    - 🗑️  Removes all config files from /sd/
    - 📁 Creates fresh directory structure
    - ✅ Keeps system files intact (boot.py, main.py, etc.)
    - 📊 Shows storage statistics

Safety:
    - Requires typing "YES" twice to confirm
    - Shows what will be deleted before proceeding
    - Verifies SD card is accessible
"""

import subprocess
import sys
from pathlib import Path

def get_port():
    """Auto-detect ESP32 port"""
    patterns = [
        "/dev/tty.usbserial*",
        "/dev/tty.SLAB_USBtoUART",
        "/dev/ttyUSB*"
    ]
    
    for pattern in patterns:
        result = subprocess.run(
            f"ls {pattern} 2>/dev/null || true",
            shell=True,
            capture_output=True,
            text=True
        )
        if result.stdout.strip():
            return result.stdout.strip().split('\n')[0]
    
    return None

def execute_command(port: str, command: str, description: str = None):
    """Execute a Python command on the ESP32"""
    if description:
        print(f"  {description}")
    
    cmd = ["mpremote", "connect", port, "exec", command]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"    ⚠️  Warning: {result.stderr.strip()}")
        return False
    
    if result.stdout.strip():
        print(f"    {result.stdout.strip()}")
    
    return True

def format_sd_card(port: str):
    """Format SD card and create experiment directory structure"""
    print("\n" + "="*60)
    print("💾 SD CARD FORMATTER FOR MARKOVIAN EXPERIMENTS")
    print("="*60)
    print("\n⚠️  WARNING: This will:")
    print("  1. Remove ALL existing experiment data")
    print("  2. Clear all config files from SD card")
    print("  3. Create fresh directory structure")
    print("  4. Keep system files intact (boot.py, main.py, etc.)")
    print("\n" + "="*60)
    
    response = input("\n⚠️  Are you ABSOLUTELY SURE? Type 'YES' to proceed: ").strip()
    if response != 'YES':
        print("❌ Format cancelled - no changes made")
        sys.exit(0)
    
    print("\n🔧 Starting SD card format...\n")
    
    # Step 1: Check if SD card is mounted
    print("📋 Step 1/5: Checking SD card...")
    check_sd = """
import os
try:
    if '/sd' in os.listdir('/'):
        print('✅ SD card detected')
    else:
        print('❌ SD card not found at /sd')
        print('💡 Make sure SD card is properly inserted')
except:
    print('❌ SD card not accessible')
"""
    if not execute_command(port, check_sd):
        print("\n❌ Cannot access SD card. Please check:")
        print("  - SD card is properly inserted")
        print("  - SD card module is working")
        print("  - sdcard.py is deployed on ESP32")
        sys.exit(1)
    
    # Step 2: Backup check - list what will be deleted
    print("\n📋 Step 2/5: Scanning existing data...")
    list_data = """
import os
try:
    if '/sd/data' in ['/sd/' + f for f in os.listdir('/sd')]:
        data_dirs = os.listdir('/sd/data')
        if data_dirs:
            print(f'Found {len(data_dirs)} experiment(s) to delete:')
            for d in data_dirs[:5]:  # Show first 5
                print(f'  - {d}')
            if len(data_dirs) > 5:
                print(f'  ... and {len(data_dirs) - 5} more')
        else:
            print('No experiments found')
    else:
        print('No data directory exists yet')
except Exception as e:
    print(f'Could not scan data: {e}')
"""
    execute_command(port, list_data)
    
    # Final confirmation
    response = input("\n⚠️  Continue with deletion? Type 'YES' again: ").strip()
    if response != 'YES':
        print("❌ Format cancelled - no changes made")
        sys.exit(0)
    
    # Step 3: Remove old data directory
    print("\n🗑️  Step 3/5: Removing old experiment data...")
    remove_data = """
import os

def rmdir_recursive(path):
    \"\"\"Recursively remove directory and contents\"\"\"
    try:
        for item in os.listdir(path):
            item_path = path + '/' + item
            try:
                # Try to remove as file first
                os.remove(item_path)
            except:
                # If it's a directory, recurse
                rmdir_recursive(item_path)
                os.rmdir(item_path)
    except:
        pass

# Remove data directory
try:
    if '/sd/data' in ['/sd/' + f for f in os.listdir('/sd')]:
        print('Removing /sd/data...')
        rmdir_recursive('/sd/data')
        os.rmdir('/sd/data')
        print('✅ Old data removed')
    else:
        print('ℹ️  No data directory to remove')
except Exception as e:
    print(f'Warning: {e}')
"""
    execute_command(port, remove_data)
    
    # Step 4: Remove config files
    print("\n🗑️  Step 4/5: Removing old config files...")
    remove_configs = """
import os

try:
    removed = 0
    for item in os.listdir('/sd'):
        if item.endswith('.json'):
            try:
                os.remove('/sd/' + item)
                removed += 1
            except Exception as e:
                print(f'Could not remove {item}: {e}')
    if removed > 0:
        print(f'✅ Removed {removed} config file(s)')
    else:
        print('ℹ️  No config files to remove')
except Exception as e:
    print(f'Warning: {e}')
"""
    execute_command(port, remove_configs)
    
    # Step 5: Create fresh directory structure
    print("\n📁 Step 5/5: Creating fresh directory structure...")
    create_dirs = """
import os

directories = [
    '/sd/data',
    '/sd/data/markovian_experiments',
    '/sd/configs_backup'
]

created = 0
for directory in directories:
    try:
        os.makedirs(directory)
        print(f'✅ Created {directory}')
        created += 1
    except OSError as e:
        if 'EEXIST' in str(e):
            print(f'ℹ️  {directory} already exists')
        else:
            print(f'⚠️  Could not create {directory}: {e}')

print(f'\\n✅ Created {created} directory(ies)')
"""
    execute_command(port, create_dirs)
    
    # Final verification
    print("\n🔍 Verifying SD card structure...")
    verify = """
import os

print('\\nSD Card Structure:')
print('/')
for item in os.listdir('/sd'):
    item_path = '/sd/' + item
    try:
        # Check if directory
        os.listdir(item_path)
        print(f'  📁 {item}/')
        # Show subdirectories
        for subitem in os.listdir(item_path):
            print(f'    📁 {subitem}/')
    except:
        # It's a file
        print(f'  📄 {item}')

# Show stats
try:
    stat = os.statvfs('/sd')
    block_size = stat[0]
    total_blocks = stat[2]
    free_blocks = stat[3]
    total_mb = (total_blocks * block_size) / (1024 * 1024)
    free_mb = (free_blocks * block_size) / (1024 * 1024)
    used_mb = total_mb - free_mb
    print(f'\\n💾 SD Card Space:')
    print(f'  Total: {total_mb:.1f} MB')
    print(f'  Used: {used_mb:.1f} MB')
    print(f'  Free: {free_mb:.1f} MB')
except Exception as e:
    print(f'Could not read storage stats: {e}')
"""
    execute_command(port, verify)
    
    print("\n" + "="*60)
    print("✅ SD CARD FORMAT COMPLETE!")
    print("="*60)
    print("\n📋 Next steps:")
    print("  1. Deploy config files: python3 Smart_incubator/sync_firmware.py")
    print("  2. Or manually copy configs:")
    print(f"     mpremote connect {port} cp Configs/experiment.json :/sd/")
    print("  3. Run experiment via VS Code task or:")
    print(f"     mpremote connect {port} exec \"import markovian_hes_executor; markovian_hes_executor.run_experiment('/sd/experiment.json')\"")
    print("\n🎉 Ready for experiments!")

def main():
    print("💾 Smart Incubator SD Card Formatter")
    print("=" * 40)
    
    # Auto-detect port
    port = get_port()
    if not port:
        print("❌ Error: ESP32 not found")
        print("\nTroubleshooting:")
        print("  - Check USB connection")
        print("  - Check device drivers installed")
        print("  - Try: ls /dev/tty.* (macOS/Linux)")
        print("\nManual usage:")
        print("  python3 Smart_incubator/format_sd_card.py /dev/tty.usbserial-0001")
        sys.exit(1)
    
    print(f"✅ Found device: {port}\n")
    
    # Format the SD card
    format_sd_card(port)

if __name__ == "__main__":
    # Allow manual port specification
    if len(sys.argv) > 1:
        port = sys.argv[1]
        print(f"💾 Smart Incubator SD Card Formatter")
        print("=" * 40)
        print(f"Using specified port: {port}\n")
        format_sd_card(port)
    else:
        main()
