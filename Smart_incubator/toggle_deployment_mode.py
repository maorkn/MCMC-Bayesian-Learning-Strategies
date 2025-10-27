#!/usr/bin/env python3
"""
Toggle Deployment Mode on ESP32
Enables/disables the deployment_mode flag that prevents auto-run of main.py
"""

import subprocess
import sys

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

def check_deployment_mode(port: str):
    """Check if deployment mode is currently enabled"""
    try:
        cmd = ["mpremote", "connect", port, "exec", 
               "import os; print('deployment_mode' in os.listdir('/'))"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        
        if result.returncode == 0:
            return "True" in result.stdout
        return None
    except subprocess.TimeoutExpired:
        # Timeout means device is probably running main.py
        return None
    except Exception as e:
        print(f"Error checking status: {e}")
        return None

def interrupt_and_enable_deployment_mode(port: str):
    """Interrupt running program and enable deployment mode"""
    print("\n🛑 Device appears to be running a program")
    print("   Attempting to enable deployment mode and reset...\n")
    
    # Try to enable deployment mode even if device is busy
    try:
        cmd = ["mpremote", "connect", port, "exec", 
               "f = open('/deployment_mode', 'w'); f.write('SAFE'); f.close()"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        
        if result.returncode == 0:
            print("✅ Deployment mode flag created")
        else:
            print("⚠️  Could not create flag (device may be busy)")
    except subprocess.TimeoutExpired:
        print("⚠️  Device is busy - flag creation timed out")
    except Exception as e:
        print(f"⚠️  Error: {e}")
    
    # Soft reset
    print("\n🔄 Attempting soft reset...")
    try:
        cmd = ["mpremote", "connect", port, "soft-reset"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        
        if result.returncode == 0:
            print("✅ Device reset successful")
            import time
            time.sleep(2)
            return True
    except subprocess.TimeoutExpired:
        print("⚠️  Soft reset timed out")
    except Exception as e:
        print(f"⚠️  Soft reset failed: {e}")
    
    # Manual reset instructions
    print("\n" + "="*60)
    print("⚠️  Please manually reset your ESP32:")
    print("="*60)
    print("  1. Press the EN (reset) button on your ESP32")
    print("  2. Wait 2-3 seconds for the device to stabilize")
    print("\nDeployment mode should now be enabled.")
    print("="*60)
    
    input("\nPress Enter after you've reset the device: ")
    
    import time
    time.sleep(1)
    return True

def enable_deployment_mode(port: str):
    """Enable deployment mode"""
    cmd = ["mpremote", "connect", port, "exec", 
           "f = open('/deployment_mode', 'w'); f.write('SAFE'); f.close(); print('ENABLED')"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    
    if result.returncode == 0 and "ENABLED" in result.stdout:
        print("✅ Deployment mode ENABLED")
        print("   main.py will NOT auto-run on boot")
        print("   Safe to update files now")
        return True
    else:
        print(f"❌ Failed to enable deployment mode: {result.stderr}")
        return False

def disable_deployment_mode(port: str):
    """Disable deployment mode"""
    cmd = ["mpremote", "connect", port, "exec", 
           "import os; os.remove('/deployment_mode') if 'deployment_mode' in os.listdir('/') else None; print('DISABLED')"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
    
    if result.returncode == 0:
        print("✅ Deployment mode DISABLED")
        print("   main.py WILL auto-run on next boot")
        return True
    else:
        print(f"❌ Failed to disable deployment mode: {result.stderr}")
        return False

def main():
    print("🔧 ESP32 Deployment Mode Toggle")
    print("=" * 40)
    
    # Auto-detect port
    port = get_port()
    if not port:
        print("❌ Error: ESP32 not found")
        sys.exit(1)
    
    print(f"✅ Found device: {port}\n")
    
    # Check current status
    print("Checking current status...")
    is_enabled = check_deployment_mode(port)
    
    if is_enabled is None:
        print("⚠️  Device is not responding (likely running main.py)")
        print("\nThis usually means deployment mode is DISABLED and main.py is running.\n")
        print("Options:")
        print("  1. Interrupt program and enable deployment mode")
        print("  2. Exit (and try sync_firmware.py instead)")
        choice = input("\nChoice [1/2]: ").strip()
        
        if choice == "1":
            interrupt_and_enable_deployment_mode(port)
            print("\n✅ Done! Deployment mode should now be enabled.")
            print("   You can verify by running this script again or use sync_firmware.py")
        else:
            print("Exiting. Use 'python3 Smart_incubator/sync_firmware.py' for deployments.")
    else:
        status = "ENABLED" if is_enabled else "DISABLED"
        auto_run = "will NOT" if is_enabled else "WILL"
        print(f"Current status: {status}")
        print(f"main.py {auto_run} auto-run on boot\n")
        
        if is_enabled:
            print("Options:")
            print("  1. Disable deployment mode (allow auto-run)")
            print("  2. Keep deployment mode enabled")
            print("  3. Exit")
            choice = input("\nChoice [1/2/3]: ").strip()
            if choice == "1":
                disable_deployment_mode(port)
                print("\n💡 Reset your device to start main.py automatically")
            elif choice == "2":
                print("✓ Deployment mode remains enabled")
        else:
            print("Options:")
            print("  1. Enable deployment mode (prevent auto-run)")
            print("  2. Keep deployment mode disabled")
            print("  3. Exit")
            choice = input("\nChoice [1/2/3]: ").strip()
            if choice == "1":
                enable_deployment_mode(port)
                print("\n💡 Reset your device to apply deployment mode")
            elif choice == "2":
                print("✓ Deployment mode remains disabled")

if __name__ == "__main__":
    main()
