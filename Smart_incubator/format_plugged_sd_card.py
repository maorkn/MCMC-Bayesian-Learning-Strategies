#!/usr/bin/env python3
"""
Routine Smart Incubator SD card formatter.

This wrapper auto-detects the currently plugged removable SD/USB storage device,
then delegates the actual formatting to format_sd_card_local.py. The delegated
formatter creates the required FAT32/MBR card with:

    /data/markovian_experiments/
    /configs_backup/

Default behavior is intentionally conservative:
    - refuses to format if no eligible removable disk is found
    - refuses to format if multiple eligible removable disks are found
    - refuses virtual disk images, internal disks, read-only disks, and large disks
    - still requires typing YES unless --yes is supplied
    - ejects the card after a successful format unless --no-eject is supplied
"""

from __future__ import annotations

import argparse
import json
import platform
import plistlib
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_MAX_SIZE_GB = 64


@dataclass
class Disk:
    path: str
    name: str
    size_bytes: int
    protocol: str = "Unknown"
    removable: bool = False
    writable: bool = False
    virtual: bool = False
    whole_disk: bool = True
    internal: bool = False
    reasons: list[str] = field(default_factory=list)

    @property
    def eligible(self) -> bool:
        return not self.reasons


def run_command(args: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, input=input_text, text=True, capture_output=True, check=False)


def human_size(size_bytes: int) -> str:
    value = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size_bytes} B"


def max_size_bytes(max_size_gb: float) -> int:
    return int(max_size_gb * 1024 * 1024 * 1024)


def macos_plist(args: list[str]) -> dict:
    result = subprocess.run(args, capture_output=True, check=False)
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(stderr or f"Command failed: {' '.join(args)}")
    return plistlib.loads(result.stdout)


def disk_from_macos_info(path: str, max_bytes: int) -> Disk:
    info = macos_plist(["diskutil", "info", "-plist", path])
    identifier = info.get("DeviceIdentifier", path.replace("/dev/", ""))
    size = int(info.get("TotalSize") or 0)
    protocol = str(info.get("BusProtocol") or "Unknown")
    virtual = info.get("VirtualOrPhysical") == "Virtual" or protocol == "Disk Image"
    removable = bool(info.get("RemovableMediaOrExternalDevice") or info.get("RemovableMedia") or info.get("Ejectable"))
    writable = bool(info.get("WritableMedia") or info.get("Writable"))
    whole_disk = bool(info.get("WholeDisk"))
    internal = bool(info.get("Internal"))

    disk = Disk(
        path=f"/dev/{identifier}",
        name=str(info.get("MediaName") or info.get("VolumeName") or "Unknown"),
        size_bytes=size,
        protocol=protocol,
        removable=removable,
        writable=writable,
        virtual=virtual,
        whole_disk=whole_disk,
        internal=internal,
    )
    add_safety_reasons(disk, max_bytes)
    return disk


def list_macos_disks(max_bytes: int) -> list[Disk]:
    listing = macos_plist(["diskutil", "list", "-plist"])
    disks: list[Disk] = []
    for identifier in listing.get("WholeDisks", []):
        try:
            disks.append(disk_from_macos_info(f"/dev/{identifier}", max_bytes))
        except RuntimeError as exc:
            disks.append(
                Disk(
                    path=f"/dev/{identifier}",
                    name="Unknown",
                    size_bytes=0,
                    reasons=[f"could not inspect disk: {exc}"],
                )
            )
    return disks


def list_linux_disks(max_bytes: int) -> list[Disk]:
    result = run_command(
        [
            "lsblk",
            "--json",
            "--bytes",
            "-o",
            "NAME,PATH,SIZE,TYPE,RM,HOTPLUG,RO,MODEL,VENDOR,TRAN",
        ]
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "lsblk failed")

    payload = json.loads(result.stdout)
    disks: list[Disk] = []
    for node in payload.get("blockdevices", []):
        if node.get("type") != "disk":
            continue
        path = node.get("path") or f"/dev/{node.get('name')}"
        protocol = str(node.get("tran") or "Unknown")
        removable = bool(node.get("rm") or node.get("hotplug") or protocol in {"usb", "mmc"})
        writable = not bool(node.get("ro"))
        name = " ".join(part for part in [node.get("vendor"), node.get("model")] if part).strip() or "Unknown"
        disk = Disk(
            path=path,
            name=name,
            size_bytes=int(node.get("size") or 0),
            protocol=protocol,
            removable=removable,
            writable=writable,
            virtual=False,
            whole_disk=True,
            internal=not removable,
        )
        add_safety_reasons(disk, max_bytes)
        disks.append(disk)
    return disks


def add_safety_reasons(disk: Disk, max_bytes: int) -> None:
    if not disk.whole_disk:
        disk.reasons.append("not a whole disk")
    if disk.internal:
        disk.reasons.append("internal disk")
    if disk.virtual:
        disk.reasons.append("virtual disk image")
    if not disk.removable:
        disk.reasons.append("not removable/external media")
    if not disk.writable:
        disk.reasons.append("not writable")
    if disk.size_bytes <= 0:
        disk.reasons.append("unknown size")
    elif disk.size_bytes > max_bytes:
        disk.reasons.append(f"larger than max size limit ({human_size(max_bytes)})")


def list_disks(max_bytes: int) -> list[Disk]:
    system = platform.system()
    if system == "Darwin":
        return list_macos_disks(max_bytes)
    if system == "Linux":
        return list_linux_disks(max_bytes)
    raise RuntimeError(f"Unsupported platform: {system}")


def print_disks(disks: list[Disk]) -> None:
    if not disks:
        print("No disks found.")
        return

    print("Detected disks:")
    for disk in disks:
        status = "eligible" if disk.eligible else "skipped: " + ", ".join(disk.reasons)
        print(f"  {disk.path:12} {human_size(disk.size_bytes):>9}  {disk.name}  [{disk.protocol}]  {status}")


def select_disk(args: argparse.Namespace) -> Disk | None:
    max_bytes = max_size_bytes(args.max_size_gb)
    disks = list_disks(max_bytes)

    if args.list:
        print_disks(disks)
        return None

    if args.disk:
        disk_path = args.disk
        matching = [disk for disk in disks if disk.path == disk_path or disk.path.replace("/dev/", "") == disk_path]
        if not matching:
            print_disks(disks)
            raise SystemExit(f"\nRefusing to continue: {disk_path} was not found.")
        disk = matching[0]
        if not disk.eligible:
            print_disks(disks)
            raise SystemExit(f"\nRefusing to format {disk.path}: {', '.join(disk.reasons)}.")
        return disk

    eligible = [disk for disk in disks if disk.eligible]
    if len(eligible) == 1:
        return eligible[0]

    print_disks(disks)
    if not eligible:
        raise SystemExit("\nNo eligible removable SD card found. Insert the card and run again.")
    raise SystemExit("\nMultiple eligible removable disks found. Re-run with --disk /dev/diskX.")


def run_formatter(disk: Disk, assume_yes: bool) -> int:
    formatter = Path(__file__).resolve().with_name("format_sd_card_local.py")
    if not formatter.exists():
        raise SystemExit(f"Formatter not found: {formatter}")

    print("\nSelected target:")
    print(f"  Device:   {disk.path}")
    print(f"  Name:     {disk.name}")
    print(f"  Size:     {human_size(disk.size_bytes)}")
    print(f"  Protocol: {disk.protocol}")
    print("\nThis will erase the selected disk and recreate it as INCUBATOR FAT32/MBR.")

    input_text = "YES\n" if assume_yes else None
    result = subprocess.run([sys.executable, str(formatter), disk.path], input=input_text, text=True, check=False)
    return result.returncode


def eject_disk(disk_path: str) -> int:
    system = platform.system()
    if system == "Darwin":
        result = subprocess.run(["diskutil", "eject", disk_path], check=False)
    elif system == "Linux":
        result = subprocess.run(["eject", disk_path], check=False)
    else:
        return 0
    return result.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auto-detect, format, prepare, and eject a Smart Incubator SD card."
    )
    parser.add_argument("--list", action="store_true", help="show detected disks and exit")
    parser.add_argument("--disk", help="format a specific disk, for example /dev/disk6")
    parser.add_argument(
        "--max-size-gb",
        type=float,
        default=DEFAULT_MAX_SIZE_GB,
        help=f"maximum eligible disk size in GB (default: {DEFAULT_MAX_SIZE_GB})",
    )
    parser.add_argument("--no-eject", action="store_true", help="leave the card mounted after formatting")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="feed YES to the underlying formatter after safety checks",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    disk = select_disk(args)
    if disk is None:
        return 0

    result = run_formatter(disk, args.yes)
    if result != 0:
        return result

    if args.no_eject:
        return 0

    print(f"\nEjecting {disk.path}...")
    eject_result = eject_disk(disk.path)
    if eject_result == 0:
        print("Ejected successfully.")
    else:
        print("Format completed, but eject failed. Eject the card manually before removing it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
