#!/usr/bin/env python3
"""
Smart Incubator SD Card Formatter (Local)
Formats SD card on your computer and creates proper directory structure

⚠️  WARNING: This will erase ALL data on the SD card!

Usage:
    # List available disks
    python3 Smart_incubator/format_sd_card_local.py --list
    
    # Format specific disk (macOS)
    python3 Smart_incubator/format_sd_card_local.py /dev/disk4
    
    # Format specific disk (Linux)
    python3 Smart_incubator/format_sd_card_local.py /dev/sdb

What it does:
    - 🗑️  Erases entire SD card
    - 💾 Formats as FAT32 (DOS_FAT_32)
    - 📁 Creates experiment directory structure:
        - /data/markovian_experiments/
        - /configs_backup/
    - 📊 Shows storage statistics

Safety:
    - Shows disk info before formatting
    - Requires typing "YES" to confirm
    - Verifies disk is removable media
    - Won't format system disks
"""

import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

def run_command(cmd, shell=False):
    """Run command and return output"""
    try:
        result = subprocess.run(
            cmd if not shell else cmd,
            shell=shell,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)

def list_disks_macos():
    """List available disks on macOS"""
    print("\n💾 Available Disks (macOS):\n")
    
    code, stdout, stderr = run_command(["diskutil", "list"])
    
    if code != 0:
        print(f"❌ Error listing disks: {stderr}")
        return
    
    print(stdout)
    print("\n📋 To get detailed info about a disk:")
    print("   diskutil info /dev/disk4")
    print("\n⚠️  WARNING: Make sure you select the correct disk!")
    print("   System disks are usually /dev/disk0, /dev/disk1")
    print("   External/SD cards are usually /dev/disk2 and higher")

def list_disks_linux():
    """List available disks on Linux"""
    print("\n💾 Available Disks (Linux):\n")
    
    # Try lsblk first
    code, stdout, stderr = run_command(["lsblk", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,LABEL"])
    
    if code == 0:
        print(stdout)
    else:
        # Fallback to fdisk
        code, stdout, stderr = run_command(["sudo", "fdisk", "-l"])
        if code == 0:
            print(stdout)
        else:
            print(f"❌ Error listing disks: {stderr}")
            return
    
    print("\n📋 SD cards are usually:")
    print("   /dev/sdb, /dev/sdc, /dev/sdd (not /dev/sda - that's your system!)")
    print("\n⚠️  WARNING: Make sure you select the correct disk!")

def get_disk_info_macos(disk):
    """Get disk information on macOS"""
    code, stdout, stderr = run_command(["diskutil", "info", disk])
    
    if code != 0:
        return None
    
    info = {}
    for line in stdout.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            info[key.strip()] = value.strip()
    
    return info

def get_disk_info_linux(disk):
    """Get disk information on Linux"""
    # Get size
    code, stdout, stderr = run_command(["lsblk", "-b", "-n", "-o", "SIZE", disk])
    size_bytes = int(stdout.strip()) if code == 0 else 0
    size_mb = size_bytes / (1024 * 1024)
    
    # Get model/name
    code, stdout, stderr = run_command(["lsblk", "-n", "-o", "MODEL", disk])
    model = stdout.strip() if code == 0 else "Unknown"
    
    return {
        'size_mb': size_mb,
        'model': model
    }

def unmount_disk_macos(disk):
    """Unmount disk on macOS"""
    print(f"\n📤 Unmounting {disk}...")
    code, stdout, stderr = run_command(["diskutil", "unmountDisk", disk])
    
    if code != 0:
        print(f"⚠️  Warning: Could not unmount: {stderr}")
        return False
    
    print("✅ Disk unmounted")
    return True

def unmount_disk_linux(disk):
    """Unmount all partitions on Linux"""
    print(f"\n📤 Unmounting {disk}...")
    
    # Get mounted partitions
    code, stdout, stderr = run_command(["lsblk", "-n", "-o", "NAME,MOUNTPOINT", disk])
    
    for line in stdout.split('\n'):
        if line.strip():
            parts = line.split()
            if len(parts) > 1 and parts[1]:
                partition = f"/dev/{parts[0]}"
                print(f"  Unmounting {partition}...")
                run_command(["sudo", "umount", partition])
    
    print("✅ Partitions unmounted")
    return True

def format_disk_macos(disk, label="INCUBATOR"):
    """Format disk on macOS"""
    print(f"\n💾 Formatting {disk} as FAT32...")
    print(f"   Label: {label}")
    print(f"   Format: MS-DOS FAT32")
    print(f"   Scheme: MBR\n")
    
    cmd = [
        "diskutil", "eraseDisk", "MS-DOS", label, "MBR", disk
    ]
    
    code, stdout, stderr = run_command(cmd)
    
    if code != 0:
        print(f"❌ Format failed: {stderr}")
        return False
    
    print(stdout)
    print("\n✅ Format complete!")
    return True

def format_disk_linux(disk, label="INCUBATOR"):
    """Format disk on Linux"""
    print(f"\n💾 Formatting {disk} as FAT32...")
    print(f"   Label: {label}")
    print(f"   This requires sudo privileges\n")
    
    # Create partition table
    print("📋 Creating partition table...")
    code, stdout, stderr = run_command([
        "sudo", "parted", "-s", disk,
        "mklabel", "msdos"
    ])
    
    if code != 0:
        print(f"❌ Failed to create partition table: {stderr}")
        return False
    
    # Create partition
    print("📋 Creating partition...")
    code, stdout, stderr = run_command([
        "sudo", "parted", "-s", disk,
        "mkpart", "primary", "fat32", "1MiB", "100%"
    ])
    
    if code != 0:
        print(f"❌ Failed to create partition: {stderr}")
        return False
    
    # Format partition
    partition = f"{disk}1" if not disk.endswith(('1','2','3','4','5','6','7','8','9')) else disk
    print(f"💾 Formatting {partition}...")
    code, stdout, stderr = run_command([
        "sudo", "mkfs.vfat", "-F", "32", "-n", label, partition
    ])
    
    if code != 0:
        print(f"❌ Format failed: {stderr}")
        return False
    
    print("\n✅ Format complete!")
    return True

def find_mount_point(disk):
    """Find where disk is mounted"""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        # Wait for mount
        import time
        time.sleep(2)
        
        code, stdout, stderr = run_command(["diskutil", "info", disk])
        for line in stdout.split('\n'):
            if 'Mount Point:' in line:
                mount = line.split(':', 1)[1].strip()
                if mount and mount != "(not mounted)":
                    return mount
        
        # Try to find volume
        volumes = Path("/Volumes").glob("INCUBATOR*")
        for vol in volumes:
            return str(vol)
        
        return None
    
    elif system == "Linux":
        import time
        time.sleep(2)
        
        # Try to find mounted partition
        partition = f"{disk}1"
        code, stdout, stderr = run_command(["lsblk", "-n", "-o", "MOUNTPOINT", partition])
        
        mount = stdout.strip()
        if mount:
            return mount
        
        # Try common mount points
        for path in [f"/media/{os.getenv('USER')}/INCUBATOR", "/mnt/INCUBATOR"]:
            if os.path.exists(path):
                return path
        
        return None

def create_directory_structure(mount_point):
    """Create experiment directory structure"""
    print(f"\n📁 Creating directory structure at {mount_point}...")
    
    directories = [
        "data",
        "data/markovian_experiments",
        "configs_backup"
    ]
    
    created = []
    for dirname in directories:
        dir_path = Path(mount_point) / dirname
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"  ✅ Created /{dirname}")
            created.append(dirname)
        except Exception as e:
            print(f"  ⚠️  Could not create /{dirname}: {e}")
    
    return created

def show_storage_stats(mount_point):
    """Show storage statistics"""
    print(f"\n📊 Storage Statistics:")
    
    stat = shutil.disk_usage(mount_point)
    
    total_mb = stat.total / (1024 * 1024)
    used_mb = stat.used / (1024 * 1024)
    free_mb = stat.free / (1024 * 1024)
    
    print(f"   Total: {total_mb:.1f} MB")
    print(f"   Used:  {used_mb:.1f} MB")
    print(f"   Free:  {free_mb:.1f} MB")

def format_sd_card(disk):
    """Main formatting workflow"""
    system = platform.system()
    
    print("\n" + "="*60)
    print("💾 SD CARD FORMATTER (LOCAL)")
    print("="*60)
    
    # Get disk info
    if system == "Darwin":
        info = get_disk_info_macos(disk)
        if not info:
            print(f"❌ Could not get info for {disk}")
            return False
        
        print(f"\n📋 Disk Information:")
        print(f"   Device: {disk}")
        print(f"   Name: {info.get('Device / Media Name', 'Unknown')}")
        print(f"   Size: {info.get('Disk Size', 'Unknown')}")
        print(f"   Removable: {info.get('Removable Media', 'Unknown')}")
        
        # Safety check
        if info.get('Removable Media') != 'Removable':
            print(f"\n⚠️  WARNING: This doesn't appear to be removable media!")
            response = input("Continue anyway? Type 'YES' to proceed: ").strip()
            if response != 'YES':
                print("❌ Format cancelled")
                return False
    
    elif system == "Linux":
        info = get_disk_info_linux(disk)
        print(f"\n📋 Disk Information:")
        print(f"   Device: {disk}")
        print(f"   Model: {info['model']}")
        print(f"   Size: {info['size_mb']:.1f} MB")
    
    else:
        print(f"❌ Unsupported platform: {system}")
        return False
    
    # Confirmation
    print("\n" + "="*60)
    print("⚠️  WARNING: ALL DATA ON THIS DISK WILL BE ERASED!")
    print("="*60)
    response = input(f"\n⚠️  Format {disk}? Type 'YES' to proceed: ").strip()
    
    if response != 'YES':
        print("❌ Format cancelled")
        return False
    
    # Unmount
    if system == "Darwin":
        if not unmount_disk_macos(disk):
            print("⚠️  Continuing anyway...")
    else:
        if not unmount_disk_linux(disk):
            print("⚠️  Continuing anyway...")
    
    # Format
    if system == "Darwin":
        if not format_disk_macos(disk, "INCUBATOR"):
            return False
    else:
        if not format_disk_linux(disk, "INCUBATOR"):
            return False
    
    # Find mount point
    print("\n🔍 Finding mount point...")
    mount_point = find_mount_point(disk)
    
    if not mount_point:
        print("⚠️  Could not find mount point")
        print("\nManual steps:")
        print("1. Eject and re-insert SD card")
        print("2. Find mount point (usually /Volumes/INCUBATOR or /media/USER/INCUBATOR)")
        print("3. Create directories:")
        print("   mkdir -p /path/to/sdcard/data/markovian_experiments")
        print("   mkdir -p /path/to/sdcard/configs_backup")
        return True
    
    print(f"✅ Found mount point: {mount_point}")
    
    # Create directories
    created = create_directory_structure(mount_point)
    
    # Show stats
    show_storage_stats(mount_point)
    
    print("\n" + "="*60)
    print("✅ SD CARD FORMAT COMPLETE!")
    print("="*60)
    print(f"\n📁 Mount Point: {mount_point}")
    print(f"📋 Created {len(created)} directory(ies)")
    print("\n📋 Next steps:")
    print("   1. Eject SD card safely")
    print("   2. Insert into ESP32 SD card module")
    print("   3. Deploy firmware: python3 Smart_incubator/sync_firmware.py")
    print("   4. Copy configs to SD card via mpremote or sync script")
    print("\n🎉 Ready for experiments!")
    
    return True

def main():
    print("💾 Smart Incubator SD Card Formatter (Local)")
    print("=" * 50)
    
    system = platform.system()
    
    # Check for list flag
    if len(sys.argv) > 1 and sys.argv[1] in ["--list", "-l"]:
        if system == "Darwin":
            list_disks_macos()
        elif system == "Linux":
            list_disks_linux()
        else:
            print(f"❌ Unsupported platform: {system}")
        return
    
    # Check for disk argument
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  List disks:    python3 Smart_incubator/format_sd_card_local.py --list")
        print("  Format disk:   python3 Smart_incubator/format_sd_card_local.py /dev/diskX")
        print("\n📋 Run with --list first to see available disks")
        sys.exit(1)
    
    disk = sys.argv[1]
    
    # Validate disk path
    if system == "Darwin":
        if not disk.startswith("/dev/disk"):
            print(f"❌ Invalid disk path: {disk}")
            print("   macOS disk paths should be like: /dev/disk4")
            sys.exit(1)
    elif system == "Linux":
        if not disk.startswith("/dev/sd") and not disk.startswith("/dev/mmcblk"):
            print(f"❌ Invalid disk path: {disk}")
            print("   Linux disk paths should be like: /dev/sdb or /dev/mmcblk0")
            sys.exit(1)
    
    if not os.path.exists(disk):
        print(f"❌ Disk not found: {disk}")
        print("\nRun with --list to see available disks")
        sys.exit(1)
    
    # Format
    success = format_sd_card(disk)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
