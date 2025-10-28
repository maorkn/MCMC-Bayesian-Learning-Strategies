# Commit Summary: SD Card Formatting Improvements & VS Code Build Task Fix

## Overview
This commit enhances the SD card formatting workflow and fixes VS Code integration issues that prevented the default build task from executing properly. The changes improve user experience by providing clear formatting options and enabling non-interactive deployment through VS Code.

## Changes Made

### 1. SD Card Formatting Documentation (`Smart_incubator/README.md`)
**Added a dedicated "SD Card Formatting" section** that clearly distinguishes between two methods:

#### Method 1: Full Local Reformat (New/Corrupted Cards)
- Creates fresh FAT32 (MBR) filesystem with required directories
- Platform-specific commands for macOS and Linux
- Uses `format_sd_card_local.py` script with proper disk enumeration
- Includes safe eject procedures

**macOS workflow:**
```bash
diskutil list
python3 Smart_incubator/format_sd_card_local.py --list
python3 Smart_incubator/format_sd_card_local.py /dev/disk6
diskutil eject /dev/disk6
```

**Linux workflow:**
```bash
lsblk
python3 Smart_incubator/format_sd_card_local.py --list
sudo python3 Smart_incubator/format_sd_card_local.py /dev/sdb
sudo eject /dev/sdb
```

#### Method 2: ESP32 Cleanup (Quick Cleanup)
- Clears files without reformatting filesystem
- Uses `format_sd_card.py` via mpremote
- Faster for routine data cleanup between experiments

**Improved clarity:**
- Removed confusing inline comments from Quick Start section
- Simplified Installation Steps to reference the dedicated formatting section
- Added clear guidance on when to use each method
- Cross-referenced `SD_CARD_FORMATTING_GUIDE.md` for detailed troubleshooting

### 2. VS Code Build Task Fix (`.vscode/tasks.json`)
**Problem:** Pressing `Cmd+Shift+B` (default build task) appeared "canceled" because `sync_firmware.py` was interactive.

**Solution:** Updated the "Smart Incubator: Sync Firmware (Auto)" task to:
- Pass `--yes` argument to skip confirmation prompts
- Set `SYNC_AUTO_YES=1` environment variable for redundant safeguard
- Explicitly set `cwd` to `${workspaceFolder}` to handle paths with spaces

**Before:**
```json
"args": ["${workspaceFolder}/Smart_incubator/sync_firmware.py"]
```

**After:**
```json
"args": ["${workspaceFolder}/Smart_incubator/sync_firmware.py", "--yes"],
"options": {
  "cwd": "${workspaceFolder}",
  "env": {
    "SYNC_AUTO_YES": "1"
  }
}
```

### 3. Non-Interactive Deployment Mode (`Smart_incubator/sync_firmware.py`)
**Implemented auto-confirmation** for CI/editor environments:

- Added `AUTO_YES` flag: `("--yes" in sys.argv) or (os.getenv("SYNC_AUTO_YES") == "1")`
- Applied to three interactive prompts:
  1. Full redeploy confirmation
  2. Manual reset wait after safe boot upload failure
  3. Manual reset wait when boot.py presence unknown

**Fixed indentation bug** in the same file:
- Corrected an if/elif/else block that could cause premature exit
- Ensures proper fallback behavior when device state is unknown

**Example change:**
```python
# Before (would block in VS Code tasks)
resp = input("\nProceed with FULL redeploy? [Y/n]: ").strip().lower()
if resp and resp != "y":
    print("❌ Redeploy cancelled")
    sys.exit(0)

# After (supports non-interactive mode)
AUTO_YES = ("--yes" in sys.argv) or (os.getenv("SYNC_AUTO_YES") == "1")
if AUTO_YES:
    print("Auto-confirmed full redeploy (--yes or SYNC_AUTO_YES=1)")
else:
    resp = input("\nProceed with FULL redeploy? [Y/n]: ").strip().lower()
    if resp and resp != "y":
        print("❌ Redeploy cancelled")
        sys.exit(0)
```

### 4. Minor Configuration Change (`Smart_incubator/Firmware/main.py`)
- Changed default correlation mode from `0` (non-temporal control) to `1` (temporal predictive)
- This is the standard configuration for temporal learning experiments
- Comment updated to reflect: "US precedes heat shock at end of cycle"

## Testing Performed

1. **SD Card Formatting:**
   - Successfully formatted `/dev/disk6` (62.9 GB) using `format_sd_card_local.py`
   - Verified FAT32 (MS-DOS) filesystem with MBR partition
   - Confirmed directory creation: `/data/markovian_experiments` and `/configs_backup`
   - Validated mount at `/Volumes/INCUBATOR`

2. **VS Code Build Task:**
   - Pressed `Cmd+Shift+B` and confirmed sync runs non-interactively
   - No "canceled" status; task completes successfully
   - `--yes` flag and `SYNC_AUTO_YES=1` env var both work correctly

3. **Non-Interactive Mode:**
   - Verified `python3 Smart_incubator/sync_firmware.py --yes` skips all prompts
   - Environment variable `SYNC_AUTO_YES=1` also enables auto-confirmation
   - Script proceeds through all deployment steps without user interaction

## Benefits

### User Experience
- **Clear formatting workflow**: Users now have explicit, step-by-step instructions for both macOS and Linux
- **Method selection guidance**: Clear explanation of when to use full reformat vs quick cleanup
- **One-click deployment**: VS Code build task (`Cmd+Shift+B`) works seamlessly without manual intervention

### Reliability
- **Reduced errors**: Non-interactive mode prevents task cancellation in automated environments
- **Path handling**: Explicit `cwd` setting handles workspace paths with spaces
- **Redundant safeguards**: Both CLI flag and env var enable non-interactive mode

### Documentation
- **Centralized SD formatting info**: Dedicated section in README eliminates scattered instructions
- **Cross-references**: Links to detailed guide for troubleshooting
- **Platform-specific commands**: Separate workflows for macOS and Linux reduce confusion

## Files Modified
1. `Smart_incubator/README.md` - Enhanced SD card formatting section and Quick Start
2. `.vscode/tasks.json` - Added non-interactive flags to default build task
3. `Smart_incubator/sync_firmware.py` - Implemented `AUTO_YES` mode and fixed indentation bug
4. `Smart_incubator/Firmware/main.py` - Changed default correlation mode to 1

## Related Documentation
- `Smart_incubator/SD_CARD_FORMATTING_GUIDE.md` - Canonical formatting reference
- `Smart_incubator/format_sd_card_local.py` - Local formatting script with --list and disk arg
- `Smart_incubator/format_sd_card.py` - ESP32 cleanup script via mpremote

## Notes
- The SD card formatting script (`format_sd_card_local.py`) was already present and functional; this commit improves its visibility and documentation
- Non-interactive mode is safe because it only skips confirmation prompts; all deployment steps still execute with full validation
- The `correlation = 1` change aligns with the platform's primary use case (temporal predictive learning experiments)
