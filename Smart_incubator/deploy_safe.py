#!/usr/bin/env python3
"""
Safe Deployment Script for Smart Incubator
This script:
1. Uploads a modified boot.py that doesn't auto-run main.py
2. Resets the device
3. Uploads all firmware files
4. Restores the original boot.py
5. Resets again to start normal operation
"""

import subprocess
import sys
import time
import tempfile
import shutil
from pathlib import Path

PORT = "/dev/tty.usbserial-0001"
FIRMWARE_DIR = "Smart_incubator/Firmware"

def run_command(cmd, description, timeout=10, ignore_errors=False):
    """Run a command and handle errors"""
    print(f"  {description}...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0 and not ignore_errors:
            print(f"    ⚠️  Warning: {result.stderr.strip()[:100]}")
            return False
        print(f"    ✅ Done")
        return True
    except subprocess.TimeoutExpired:
        if not ignore_errors:
            print(f"    ⚠️  Timeout")
        return False
    except Exception as e:
        if not ignore_errors:
            print(f"    ⚠️  Error: {e}")
        return False

def create_safe_boot():
    """Create a boot.py that doesn't auto-run main"""
    boot_path = Path(FIRMWARE_DIR) / "boot.py"
    
    with open(boot_path, 'r') as f:
        content = f.read()
    
    # Create a safe version that doesn't run main
    safe_content = content.replace(
        "try:\n    # Run the working main program\n    import main\n    main.main()",
        "# Main auto-run disabled for deployment\nprint('Ready for deployment. Main program will not auto-run.')"
    )
    
    # Create temp file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
    temp_file.write(safe_content)
    temp_file.close()
    
    return temp_file.name

def main():
    print("=" * 60)
    print("🔧 Safe Deployment for Smart Incubator")
    print("=" * 60)
    print()
    
    # Step 1: Create safe boot.py
    print("📝 Step 1: Creating safe boot.py...")
    safe_boot_path = create_safe_boot()
    print("    ✅ Safe boot.py created")
    
    # Step 2: Upload safe boot.py
    print("\n📤 Step 2: Uploading safe boot.py...")
    run_command(
        ["mpremote", "connect", PORT, "cp", safe_boot_path, ":/boot.py"],
        "Uploading safe boot",
        timeout=15,
        ignore_errors=False
    )
    
    # Clean up temp file
    Path(safe_boot_path).unlink()
    
    # Step 3: Reset device
    print("\n🔄 Step 3: Resetting device...")
    subprocess.run(
        ["mpremote", "connect", PORT, "reset"],
        capture_output=True,
        timeout=5
    )
    print("    ✅ Reset command sent")
    print("    ⏳ Waiting 5 seconds for device to boot...")
    time.sleep(5)
    
    # Step 4: Upload all firmware files
    print("\n📦 Step 4: Uploading ALL firmware files...")
    firmware_files = list(Path(FIRMWARE_DIR).glob("*.py"))
    print(f"    Found {len(firmware_files)} files to upload\n")
    
    success_count = 0
    for filepath in sorted(firmware_files):
        remote_path = f"/{filepath.name}"
        print(f"  📤 {filepath.name} → {remote_path}")
        
        if run_command(
            ["mpremote", "connect", PORT, "cp", str(filepath), f":{remote_path}"],
            f"Uploading {filepath.name}",
            timeout=15
        ):
            success_count += 1
            time.sleep(0.5)  # Small delay between files
    
    print(f"\n    ✅ Uploaded {success_count}/{len(firmware_files)} files")
    
    # Step 5: Final reset to start normal operation
    print("\n🔄 Step 5: Final reset to start normal operation...")
    subprocess.run(
        ["mpremote", "connect", PORT, "reset"],
        capture_output=True,
        timeout=5
    )
    print("    ✅ Reset complete")
    
    print("\n" + "=" * 60)
    print("✅ Deployment Complete!")
    print("=" * 60)
    print("\nThe device should now be running your main program.")
    print("To monitor output: mpremote connect", PORT, "repl")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Deployment failed: {e}")
        sys.exit(1)
