#!/usr/bin/env python3
"""
Smart Incubator Firmware Sync Tool (Simplified Full Redeploy)
- Always wipes device files (except boot.py while we swap it safely)
- Uploads ALL firmware files every run
- Installs required MicroPython packages
- Creates SD card directory structure
- Restores original boot.py and resets to start normal operation

Rationale:
Incremental sync can be flaky when main.py auto-runs and blocks REPL. This script switches to a robust,
simple flow: temporarily install a "safe boot.py" that never auto-runs main, reset, wipe files, upload all,
restore the real boot.py, then reset again.
"""

import os
import argparse
import hashlib
import importlib.util
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, Set, List, Optional

# Configuration
FIRMWARE_DIR = "Smart_incubator/Firmware"
CONFIG_DIR = "Smart_incubator/Configs"
CACHE_FILE = "Smart_incubator/.deployment_cache.json"
SETUP_MARKER = "Smart_incubator/.esp32_initialized"
REQUIREMENTS_FILE = "Smart_incubator/micropython_requirements.txt"

# Files to always skip (local filtering)
SKIP_FILES = {
    "__pycache__",
    ".pyc",
    ".DS_Store",
    ".git",
    "README.md"
}

# CLI / runtime configuration (populated in main)
AUTO_YES = os.getenv("SYNC_AUTO_YES") == "1"
CORRELATION_OVERRIDE: Optional[int] = None
_CORRELATION_NOTICE_EMITTED = False

def _apply_correlation_override(source_text: str, correlation_value: int) -> Optional[str]:
    """Return source with the first correlation assignment replaced."""
    pattern = re.compile(r"^(\s*correlation\s*=\s*)([0-9]+)", re.MULTILINE)
    new_text, replacements = pattern.subn(r"\g<1>{}".format(correlation_value), source_text, count=1)
    if replacements == 0:
        return None
    return new_text


# =========================
# Utilities / Requirements
# =========================

def load_requirements() -> List[str]:
    """Load required packages from requirements file"""
    if not os.path.exists(REQUIREMENTS_FILE):
        return []
    
    packages = []
    with open(REQUIREMENTS_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if line and not line.startswith('#'):
                packages.append(line)
    return packages

REQUIRED_PACKAGES = load_requirements()

def get_port() -> Optional[str]:
    """Auto-detect ESP32 port, honouring environment override."""
    env_port = os.getenv("INCUBATOR_PORT") or os.getenv("ESP32_PORT")
    if env_port:
        return env_port

    if os.name == "nt":
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    "[System.IO.Ports.SerialPort]::GetPortNames() | Sort-Object"
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            ports = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
            if ports:
                return ports[0]
        except Exception:
            pass
        return None

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

def run_cmd(cmd: List[str], timeout: int = 8, quiet: bool = False) -> subprocess.CompletedProcess:
    """Run a subprocess command, return CompletedProcess (never raise)."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if not quiet and result.stdout.strip():
            print(result.stdout.strip())
        if not quiet and result.stderr.strip():
            print(result.stderr.strip())
        return result
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, returncode=124, stdout="", stderr="TIMEOUT")
    except Exception as exc:
        return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr=str(exc))


def _test_mpremote_command(base_cmd: List[str]) -> bool:
    """Return True if mpremote command appears functional."""
    try:
        result = subprocess.run([*base_cmd, "--help"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return True
    except Exception:
        pass
    return False


def _resolve_mpremote_base() -> List[str]:
    """Discover a working mpremote command invocation."""
    env_cmd = os.getenv("MPREMOTE")
    if env_cmd:
        candidate = shlex.split(env_cmd)
        if _test_mpremote_command(candidate):
            return candidate
        raise RuntimeError(f"MPREMOTE override is invalid: {' '.join(candidate)}")

    candidates: List[List[str]] = []

    direct_exe = shutil.which("mpremote")
    if direct_exe:
        candidates.append([direct_exe])

    if importlib.util.find_spec("mpremote") is not None:
        candidates.append([sys.executable, "-m", "mpremote"])

    if os.name == "nt":
        py_launcher = shutil.which("py")
        if py_launcher:
            candidates.append([py_launcher, "-m", "mpremote"])
            for minor in ("3.12", "3.11", "3.10"):
                candidates.append([py_launcher, f"-{minor}", "-m", "mpremote"])

    for launcher in ("python3", "python"):
        exe = shutil.which(launcher)
        if exe and exe != sys.executable:
            candidates.append([exe, "-m", "mpremote"])

    seen = set()
    unique_candidates: List[List[str]] = []
    for base_cmd in candidates:
        key = tuple(base_cmd)
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(base_cmd)

    for base_cmd in unique_candidates:
        if _test_mpremote_command(base_cmd):
            return base_cmd

    raise RuntimeError(
        "Could not locate a working mpremote command. Install mpremote or set the MPREMOTE environment variable."
    )


def mpremote_cmd(*args: str) -> List[str]:
    """Return a cross-platform mpremote command list."""
    cached = getattr(mpremote_cmd, "_cached_cmd", None)
    if cached is None:
        cached = _resolve_mpremote_base()
        mpremote_cmd._cached_cmd = cached
        print(f"ℹ️ Using mpremote command: {' '.join(cached)}")
    return [*cached, *args]


def reset_device(port: str, wait_sec: float = 2.0):
    """Send a reset to the device and wait a bit."""
    run_cmd(mpremote_cmd("connect", port, "reset"), timeout=5, quiet=True)
    time.sleep(wait_sec)

def device_has_boot(port: str) -> Optional[bool]:
    """Return True if boot.py exists on device, False if not, None if unknown (timeout/error)."""
    res = run_cmd(mpremote_cmd("connect", port, "ls"), timeout=5, quiet=True)
    if res.returncode == 0:
        out = (res.stdout or "")
        return "boot.py" in out
    # TIMEOUT or error
    return None

# =========================
# Safe boot handling
# =========================

SAFE_BOOT_CONTENT = """# Safe boot for deployment - DO NOT AUTO-RUN MAIN
import gc, machine, time
print("=== SAFE DEPLOYMENT MODE ===")

# Set known-safe outputs (adapt pins to your hardware as needed)
try:
    for pin in (33, 27, 25, 16):
        try:
            p = machine.Pin(pin, machine.Pin.OUT)
            p.value(0)
        except Exception as e:
            print("Pin init failed:", pin, e)
except Exception as e:
    print("GPIO init block failed:", e)

gc.collect()
print("Boot complete. Skipping main.py for deployment.")
# Stay idle; do not import main
"""

def upload_safe_boot(port: str) -> bool:
    """Upload a temporary safe boot.py that never auto-runs main."""
    global AUTO_YES
    print("📝 Creating and uploading safe boot.py...")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tf:
        tf.write(SAFE_BOOT_CONTENT)
        temp_path = tf.name
    try:
        for attempt in range(1, 4):
            print(f"  📤 Upload attempt {attempt}...")
            res = run_cmd(mpremote_cmd("connect", port, "cp", temp_path, ":/boot.py"), timeout=10, quiet=True)
            if res.returncode == 0:
                print("  ✅ Safe boot.py uploaded")
                return True
            else:
                print(f"  ⚠️  Upload failed (attempt {attempt}): {res.stderr.strip() or res.stdout.strip()}")
                print("  ⏳ Waiting 1s and retrying...")
                time.sleep(1.0)
        # Prompt manual reset then one more try
        print("\n" + "="*60)
        print("⚠️  Could not upload safe boot automatically.")
        print("   Please press the EN (reset) button on the ESP32, wait 2-3 seconds, then press Enter.")
        print("="*60)
        if AUTO_YES:
            print("AUTO_YES enabled: skipping interactive wait and retrying upload")
        else:
            input("\nPress Enter after reset: ")
        res = run_cmd(mpremote_cmd("connect", port, "cp", temp_path, ":/boot.py"), timeout=10, quiet=True)
        if res.returncode == 0:
            print("  ✅ Safe boot.py uploaded after manual reset")
            return True
        print("❌ Still failed to upload safe boot.py")
        return False
    finally:
        try:
            Path(temp_path).unlink(missing_ok=True)  # type: ignore[attr-defined]
        except Exception:
            pass

# =========================
# Device filesystem ops
# =========================

def wipe_device_files(port: str):
    """Remove all Python files from root (except boot.py) and selected files from /sd."""
    print("\n🧹 Wiping device files (root and /sd)...")
    # Remove .py/.mpy on root (except boot.py)
    cmd_root = mpremote_cmd(
        "connect", port, "exec",
        "import os; "
        "[os.remove('/'+f) for f in os.listdir('/') "
        " if (f.endswith('.py') or f.endswith('.mpy')) and f!='boot.py' and not f.startswith('.')]; "
        "print('OK')"
    )
    res_root = run_cmd(cmd_root, timeout=8, quiet=True)
    if res_root.returncode != 0:
        print("  ⚠️  Root wipe may have partially failed")

    # Clean /sd configs/data (json/txt/log)
    cmd_sd = mpremote_cmd(
        "connect", port, "exec",
        "import os; "
        "exists=('sd' in os.listdir('/')); "
        "print('NO_SD') if not exists else [os.remove('/sd/'+f) for f in os.listdir('/sd') "
        " if (f.endswith('.json') or f.endswith('.txt') or f.endswith('.log')) and not f.startswith('.')]; "
        "print('OK')"
    )
    res_sd = run_cmd(cmd_sd, timeout=8, quiet=True)
    if res_sd.returncode != 0:
        print("  ⚠️  /sd wipe may have partially failed")

def upload_file(port: str, local_path: Path, remote_path: str) -> bool:
    """Upload single file to ESP32"""
    global CORRELATION_OVERRIDE, _CORRELATION_NOTICE_EMITTED

    print(f"  📤 {local_path} → {remote_path}")

    source_path = str(local_path)
    temp_path = None

    if CORRELATION_OVERRIDE is not None and local_path.name == "main.py":
        try:
            patched_content = _apply_correlation_override(local_path.read_text(), CORRELATION_OVERRIDE)
            if patched_content is None:
                if not _CORRELATION_NOTICE_EMITTED:
                    print("    ⚠️  Correlation override requested but no 'correlation =' assignment found in main.py")
                    _CORRELATION_NOTICE_EMITTED = True
            else:
                temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False)
                temp_file.write(patched_content)
                temp_file.flush()
                temp_file.close()
                temp_path = temp_file.name
                source_path = temp_path
                if not _CORRELATION_NOTICE_EMITTED:
                    print(f"    🔁 Patched correlation to {CORRELATION_OVERRIDE} for upload")
                    _CORRELATION_NOTICE_EMITTED = True
        except Exception as exc:
            print(f"    ⚠️  Failed to apply correlation override: {exc}")

    result = run_cmd(mpremote_cmd("connect", port, "cp", source_path, f":{remote_path}"), timeout=15, quiet=True)

    if temp_path:
        try:
            Path(temp_path).unlink()
        except Exception:
            pass

    if result.returncode != 0:
        print(f"    ⚠️  Warning: {result.stderr.strip() or result.stdout.strip()}")
        return False
    return True

# =========================
# Package install and SD setup
# =========================

def install_micropython_packages(port: str):
    """Install required MicroPython packages"""
    if not REQUIRED_PACKAGES:
        print("  ℹ️  No additional packages required")
        return
    
    print(f"\n📦 Installing {len(REQUIRED_PACKAGES)} MicroPython package(s)...")
    for package in REQUIRED_PACKAGES:
        print(f"  📥 Installing {package}...")
        result = run_cmd(mpremote_cmd("connect", port, "mip", "install", package), timeout=60, quiet=True)
        if result.returncode != 0:
            print(f"    ⚠️  Failed to install {package}: {result.stderr.strip() or result.stdout.strip()}")
        else:
            print(f"    ✅ Installed {package}")

def create_sd_directories(port: str):
    """Create necessary directories on SD card"""
    print("\n📁 Creating SD card directories...")
    directories = ["/sd", "/sd/data", "/sd/data/markovian_experiments"]
    for directory in directories:
        print(f"  📁 Ensuring {directory} exists...")
        cmd = mpremote_cmd(
            "connect", port, "exec",
            f"import os; "
            f"exists=('sd' in os.listdir('/')) if '{directory}'.startswith('/sd') else True; "
            f"os.makedirs('{directory}') if exists and '{directory}' not in str(os.listdir('/')) else None; "
            "print('OK')"
        )
        res = run_cmd(cmd, timeout=8, quiet=True)
        if res.returncode != 0 and "EEXIST" not in (res.stderr or ""):
            print(f"    ℹ️  Directory may already exist or SD card not present")

# =========================
# File collection helpers
# =========================

def get_all_firmware_files() -> List[Path]:
    """Get all firmware files for deployment"""
    files: List[Path] = []
    # Firmware files (py/json/txt)
    if os.path.exists(FIRMWARE_DIR):
        for root, dirs, filenames in os.walk(FIRMWARE_DIR):
            dirs[:] = [d for d in dirs if d not in SKIP_FILES]
            for filename in filenames:
                if any(skip in filename for skip in SKIP_FILES):
                    continue
                filepath = Path(root) / filename
                if filepath.suffix.lower() in ['.py', '.json', '.txt']:
                    files.append(filepath)
    # Config files (json)
    if os.path.exists(CONFIG_DIR):
        for config_file in Path(CONFIG_DIR).glob("*.json"):
            files.append(config_file)
    return files

def check_firmware_exists() -> bool:
    """Check if firmware files exist before attempting deployment"""
    firmware_files = get_all_firmware_files()
    if not firmware_files:
        print("\n⚠️  WARNING: No firmware files found!")
        print("\nExpected files in:")
        print(f"  - {FIRMWARE_DIR}/ (for .py files)")
        print(f"  - {CONFIG_DIR}/ (for .json files)")
        print("\nCreate your firmware files first, then run this script again.")
        return False
    return True


# =========================
# CLI handling
# =========================


def parse_args():
    parser = argparse.ArgumentParser(description="Smart Incubator firmware redeploy tool")
    parser.add_argument("--yes", action="store_true", help="Skip confirmation and interactive prompts")
    parser.add_argument("--correlation", type=int, choices=[0, 1], help="Override correlation value in main.py (0 or 1)")
    parser.add_argument("--port", help="Explicit serial port to use (overrides auto-detect)")
    parser.add_argument("--force", "-f", "--reset", dest="force", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()

# =========================
# Full redeploy flow
# =========================

def full_redeploy(port: str):
    """Perform a full redeploy every time (safe boot, wipe, upload all, restore, reset)."""
    global AUTO_YES, CORRELATION_OVERRIDE
    print("\n" + "="*60)
    print("🧼 FULL REDEPLOY")
    print("="*60)
    print("This will:")
    print("  1. Upload a safe boot.py that does NOT auto-run main")
    print("  2. Reset the device to load safe boot")
    print("  3. Wipe Python files from root (except boot.py) and clean /sd configs")
    print("  4. Install required MicroPython packages (if any)")
    print("  5. Ensure SD directories exist")
    print("  6. Upload ALL firmware and config files")
    print("  7. Restore the original boot.py")
    print("  8. Reset to start normal operation")
    print("="*60)

    if CORRELATION_OVERRIDE is not None:
        print(f"\n🔁 Correlation override active: main.py will be patched to {CORRELATION_OVERRIDE}")

    # Confirm
    if AUTO_YES:
        print("Auto-confirmed full redeploy (--yes or SYNC_AUTO_YES=1)")
    else:
        resp = input("\nProceed with FULL redeploy? [Y/n]: ").strip().lower()
        if resp and resp != "y":
            print("❌ Redeploy cancelled")
            sys.exit(0)

    # Step 1: Ensure no autorun by handling boot.py
    has_boot = device_has_boot(port)
    if has_boot is True:
        print("\n🔐 Detected boot.py on device; attempting to install safe boot...")
        if not upload_safe_boot(port):
            print("\n⚠️ Could not install safe boot automatically.")
            print("   If the device is busy, delete boot.py on the device, then press Enter to continue.")
            if AUTO_YES:
                print("AUTO_YES enabled: skipping interactive wait; continuing")
            else:
                input("Press Enter after deleting boot.py and resetting the device: ")
    elif has_boot is False:
        print("\nℹ️ boot.py not present on device; skipping safe boot step")
    else:
        print("\n⚠️ Could not determine device files (device may be busy).")
        print("   Delete boot.py on the device, then press Enter to continue.")
        if AUTO_YES:
            print("AUTO_YES enabled: skipping interactive wait; continuing")
        else:
            input("Press Enter after deleting boot.py and resetting the device: ")

    # Step 2: Reset to load safe boot
    print("\n🔄 Resetting device to enter safe mode...")
    reset_device(port, wait_sec=2.5)
    print("  ✅ Device reset")

    # Step 3: Wipe device files
    wipe_device_files(port)

    # Step 4: Install packages
    install_micropython_packages(port)

    # Step 5: Ensure SD structure
    create_sd_directories(port)

    # Step 6: Upload all files
    if not check_firmware_exists():
        print("\n❌ Redeploy aborted - no firmware files found")
        sys.exit(1)

    print("\n📦 Uploading ALL firmware files...")
    all_files = get_all_firmware_files()
    print(f"  Found {len(all_files)} file(s) to upload\n")

    success_count = 0
    for filepath in sorted(all_files):
        # Determine remote path
        if str(filepath).startswith(FIRMWARE_DIR):
            remote_path = f"/{filepath.name}" if filepath.suffix.lower() == ".py" else f"/sd/{filepath.name}"
            # Convention: .py to root, other resources (json/txt) to /sd
            if filepath.suffix.lower() == ".py":
                remote_path = f"/{filepath.name}"
            else:
                remote_path = f"/sd/{filepath.name}"
        elif str(filepath).startswith(CONFIG_DIR):
            remote_path = f"/sd/{filepath.name}"
        else:
            # Fallback to root
            remote_path = f"/{filepath.name}"
        if upload_file(port, filepath, remote_path):
            success_count += 1
            time.sleep(0.2)

    print(f"\n    ✅ Uploaded {success_count}/{len(all_files)} files")

    # Step 7: Restore original boot.py
    boot_src = Path(FIRMWARE_DIR) / "boot.py"
    if boot_src.exists():
        print("\n📤 Restoring original boot.py...")
        if not upload_file(port, boot_src, "/boot.py"):
            print("❌ Failed to restore original boot.py")
            sys.exit(1)
    else:
        print("\n⚠️  No original boot.py found locally; keeping safe boot on device")

    # Save marker (purely local)
    try:
        with open(SETUP_MARKER, 'w') as f:
            f.write(f"ESP32 initialized on {port}\n")
    except Exception:
        pass

    # Step 8: Final reset
    print("\n🔄 Final reset to start normal operation...")
    reset_device(port, wait_sec=2.0)
    print("  ✅ Reset complete")

    print("\n" + "="*60)
    print("✅ Full redeploy complete!")
    print("="*60)
    print("\nTo monitor output:")
    print(f"  mpremote connect {port} repl")

# =========================
# Main
# =========================

def main():
    global AUTO_YES, CORRELATION_OVERRIDE

    args = parse_args()
    AUTO_YES = AUTO_YES or args.yes
    if args.correlation is not None:
        CORRELATION_OVERRIDE = args.correlation

    print("🔧 Smart Incubator Firmware Sync (Full Redeploy Mode)")
    print("=" * 40)

    port = args.port or get_port()
    if not port:
        print("❌ Error: ESP32 not found")
        print("\nHint: specify --port COMx (Windows) or --port /dev/ttyUSB0 (Unix) if auto-detect fails")
        sys.exit(1)

    print(f"✅ Using device: {port}\n")

    # Always perform full redeploy (simple and robust)
    try:
        full_redeploy(port)
    except RuntimeError as exc:
        print(f"\n❌ Deployment aborted: {exc}")
        print("Hint: install mpremote (pip install mpremote) or set MPREMOTE to the full command.")
        sys.exit(1)


if __name__ == "__main__":
    main()
