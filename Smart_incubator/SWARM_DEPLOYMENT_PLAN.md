# Smart Incubator Swarm Deployment Plan

## Purpose

Build one central place to define a swarm experiment, choose one or more parameters to sweep, assign per-incubator values from a distribution, and deploy the resulting device-specific experiment configuration across many Smart Incubator units.

The immediate target is this workflow:

1. Enter the full experiment once.
2. Keep most parameters fixed across all incubators.
3. Choose a parameter to vary, such as correlation, basal temperature, heat shock temperature, interval range, US duration, or stimulus intensity.
4. Choose an assignment distribution, such as uniform, normal, log normal, fixed grid, random categorical, or fixed/manual.
5. Set `n`, the size of the swarm.
6. Generate one reproducible bulk swarm config containing `n` assignment chunks.
7. Flash units sequentially by assignment order.
8. Boot each unit into its assigned chunk without using the AP setup page.
9. Log enough metadata on each SD card to reconstruct exactly what each unit ran.

No firmware code should be changed until this design is discussed and accepted.

## Current System Summary

The current firmware is built around a single incubator:

- `Firmware/main.py` boots into a WiFi AP configuration mode, receives one experiment config, shuts down the setup server, and runs cycles.
- `Firmware/experiment_setup_server.py` exposes a lightweight AP web form for one device at `192.168.4.1`.
- Runtime experiment parameters currently include:
  - `experiment_name`
  - `correlation`
  - `basal_temp`
  - `heat_shock_temp`
  - `us_type`
  - `min_interval`
  - `max_interval`
  - `us_duration`
  - `heat_duration`
- `Firmware/run_experiment_cycle.py` turns these parameters into cycle timing and controller behavior.
- `Firmware/sd_logger.py` writes metadata, snapshots, summaries, manifests, and checksums to SD.
- `sync_firmware.py` already supports device deployment and contains an old source-level correlation override hook, but editing source text per device is not the right model for swarm deployment.

Important resource constraint: unused `.py` files on the ESP32 mostly cost flash storage, not heap. Heap is consumed by imports and retained module state. Swarm support should therefore avoid adding large runtime modules to the ESP32 experiment path.

## Design Principle

Use the laptop as the swarm planner and deployment authority. Use each ESP32 as a deterministic executor of a small assigned config.

The firmware should not know how to sample distributions or reason about the whole swarm. It should only:

- Load its assigned config.
- Apply validated parameters.
- Record the assigned swarm metadata in SD logs.
- Run the experiment as it already does.

This keeps the ESP32 simple and makes the whole swarm reproducible.

## Proposed Architecture

### 1. Host-Side Swarm Planner

Add a desktop-side planning tool, likely:

```text
Smart_incubator/swarm_planner.py
Smart_incubator/swarm_dashboard.py
Smart_incubator/swarm_configs/
```

The planner owns:

- Global experiment parameters.
- Device inventory.
- Sweep definitions.
- Distribution sampling.
- Random seeds.
- Generated per-device config files.
- A swarm manifest for analysis and audit.

The first version can be command line plus a JSON/YAML input file. A local browser dashboard can follow once the schema is stable.

### 2. Swarm Experiment Spec

Create one canonical host-side spec file, for example:

```json
{
  "swarm_id": "correlation_sweep_2026_06_09_a",
  "experiment_name": "capsaspora_correlation_sweep",
  "seed": 18421,
  "devices": [
    {"unit_id": "inc_8F0C", "port": "/dev/cu.usbserial-0001"},
    {"unit_id": "inc_C928", "port": "/dev/cu.usbserial-0002"}
  ],
  "base_config": {
    "mode": "experiment",
    "basal_temp": 23.0,
    "heat_shock_temp": 32.0,
    "correlation": 1.0,
    "us_type": "BOTH",
    "min_interval": 200,
    "max_interval": 400,
    "us_duration_seconds": 1800,
    "heat_duration_seconds": 1800,
    "log_interval": 10
  },
  "sweeps": [
    {
      "parameter": "correlation",
      "distribution": "uniform",
      "min": 0.0,
      "max": 1.0,
      "assignment": "random"
    }
  ]
}
```

This file is the single source of truth. Generated device configs should never be manually edited unless explicitly marked as manual.

### 3. Per-Device Config

The planner derives one compact config per incubator:

```json
{
  "swarm_id": "correlation_sweep_2026_06_09_a",
  "unit_id": "inc_8F0C",
  "assignment_index": 0,
  "experiment_name": "capsaspora_correlation_sweep_inc_8F0C",
  "seed": 9237741,
  "sweep": {
    "parameter": "correlation",
    "value": 0.37,
    "distribution": "uniform",
    "source_seed": 18421
  },
  "config": {
    "mode": "experiment",
    "basal_temp": 23.0,
    "heat_shock_temp": 32.0,
    "correlation": 0.37,
    "us_type": "BOTH",
    "min_interval": 200,
    "max_interval": 400,
    "us_duration_seconds": 1800,
    "heat_duration_seconds": 1800,
    "log_interval": 10
  }
}
```

This can be uploaded to:

```text
/swarm_config.json
```

or copied to the SD card as:

```text
/sd/swarm_config.json
```

Preferred for v1: upload to ESP32 flash as `/swarm_config.json`, then mirror it into SD metadata when the experiment starts.

### 4. Swarm Manifest

The planner also writes one host-side manifest and assignment table:

```text
Smart_incubator/swarm_configs/correlation_sweep_2026_06_09_a/manifest.json
Smart_incubator/swarm_configs/correlation_sweep_2026_06_09_a/assignments.csv
Smart_incubator/swarm_configs/correlation_sweep_2026_06_09_a/bulk_config.json
```

The manifest should contain:

- `swarm_id`
- `swarm_size`
- generation timestamp
- planner version
- firmware version or git commit
- random seed
- full base config
- sweep definitions
- device list
- assigned value per device
- deployment status per device
- SD card ID if available
- expected output path on each SD card

This is essential for post-run analysis and preventing accidental mixups.

The bulk config should be ordered and explicit:

```json
{
  "swarm_id": "correlation_sweep_2026_06_09_a",
  "swarm_size": 12,
  "seed": 18421,
  "base_config": {
    "mode": "experiment",
    "basal_temp": 23.0,
    "heat_shock_temp": 32.0,
    "us_type": "BOTH",
    "min_interval": 200,
    "max_interval": 400,
    "us_duration_seconds": 1800,
    "heat_duration_seconds": 1800,
    "log_interval": 10
  },
  "assignments": [
    {"assignment_index": 0, "correlation": 0.00, "device_seed": 9237741},
    {"assignment_index": 1, "correlation": 0.09, "device_seed": 8145522},
    {"assignment_index": 2, "correlation": 0.18, "device_seed": 1043883}
  ]
}
```

During deployment, only one assignment chunk is written to each ESP32 as `/swarm_config.json`. The full `bulk_config.json` remains on the laptop as the source of truth.

## Parameter Sweep Model

### Supported Parameters

Initial sweepable parameters should include:

- `correlation`
- `basal_temp`
- `heat_shock_temp`
- `min_interval`
- `max_interval`
- `us_duration_seconds`
- `heat_duration_seconds`
- `us_type`
- `led_intensity`
- `vib_intensity`

The first swarm sweep should use the existing `correlation` parameter and keep that nomenclature everywhere: planner, manifest, per-device config, boot display, OLED display, and analysis tables.

Current firmware interpretation:

- `correlation = 1`: every cycle is paired; US precedes heat shock.
- `correlation = 0`: US and heat shock timings are independent/random.
- `correlation = -1`: no US; heat shock remains deterministic at the end of the cycle.
- Intermediate positive values mix paired and random cycles.
- Intermediate negative values mix no-US and random cycles.

For the first swarm implementation, the user-facing label should be `correlation`, matching the machine-readable config field.

### Distribution Types

Minimum useful set:

- `fixed`: same value for every incubator.
- `uniform`: sample between `min` and `max`.
- `normal`: sample from `mean` and `sd`, optionally clipped.
- `lognormal`: sample from log-space `mean` and `sigma`, optionally clipped.
- `grid`: evenly spaced values across the swarm.
- `categorical`: choose from a set of values, with optional weights.
- `manual`: explicit value per unit.

Each distribution must define whether assignments are:

- `random`: seeded random samples.
- `grid`: deterministic sorted values.
- `balanced`: repeated values across replicates.
- `blocked`: randomization constrained by hardware batch, shelf, date, or treatment block.

### Reproducibility

Every generated assignment should be reproducible from:

- `swarm_id`
- base config
- sweep definitions
- global seed
- device ordering

The planner should refuse to regenerate over an existing `swarm_id` unless a `--force` flag is used.

## Deployment Workflow

### Version 0: Ordered USB Flashing, Headless Swarm Execution

This is the safest near-term version and fits the current tooling.

1. User creates or edits a swarm spec on the laptop.
2. Planner validates the schema and generates a `bulk_config.json` with `n = swarm_size` assignment chunks.
3. User lines up incubators physically in assignment order.
4. User plugs in one incubator at a time.
5. Deployment tool uploads the next assignment chunk in order as `/swarm_config.json`.
6. Tool uploads:
   - production firmware files
   - updated `sdcard.py`
   - assigned `/swarm_config.json`
   - real `boot.py`
7. Tool records the flashed assignment index, config hash, port, and observed device ID in the manifest.
8. Device boots, loads its assigned config, displays the assignment on OLED, and starts the assigned experiment without showing the AP setup page.

This avoids needing all ESP32 units on the same network, avoids AP collisions, and avoids configuring each unit manually. The cost is operational discipline: the physical flashing order must match the assignment order.

### Version 1: Multi-Port USB Batch Deployment

If several ESP32 units are connected at once:

1. Detect all serial ports.
2. Query each device ID.
3. Match each device to a manifest assignment.
4. Deploy in parallel or controlled sequence.
5. Record deployment success/failure in `manifest.json`.

This is useful in the lab if several USB adapters are available. It should still preserve assignment order unless device IDs are pre-registered.

### Version 2: WiFi Swarm Deployment

Longer-term option:

1. Each incubator joins a lab router as a station instead of creating only an AP.
2. A laptop dashboard discovers devices over mDNS or a simple registry.
3. Dashboard pushes assigned config over HTTP.
4. Devices acknowledge config hash and readiness.
5. Dashboard starts the whole swarm or specific subsets.

This is more convenient but requires more firmware and network reliability work. It should not be the first implementation.

## Firmware Changes Proposed Later

No firmware changes are made in this plan. If accepted, these are likely changes:

### 1. Config Loader

Add a small module:

```text
Firmware/config_loader.py
```

Responsibilities:

- Load `/swarm_config.json` if present.
- Validate values and bounds.
- Normalize units, especially minutes vs seconds.
- Return a clear validity/error result before any heavy runtime modules are imported.
- Fall back to AP config only if no valid swarm config is present.
- Return one normalized config dictionary to `main.py`.

### 2. Main Runtime Integration

Modify `main.py` so it supports:

- Headless file-based swarm execution from `/swarm_config.json`.
- AP manual config as fallback/debug behavior when no valid swarm config exists.
- Serial/OLED reporting of the selected `swarm_id`, `assignment_index`, and swept `correlation`.

For swarm deployment, the normal path is not the AP. The boot sequence should initiate the assigned swarm chunk automatically after validation. The AP remains useful for single-unit setup, hardware test, and recovery.

### 3. Logger Metadata

Extend `sd_logger.ExperimentLogger` metadata to include:

- `swarm_id`
- `unit_id`
- `assignment_index`
- `sweep_parameter`
- `sweep_value`
- `distribution`
- `global_seed`
- `device_seed`
- `config_hash`
- `firmware_hash`

This should be written to `meta.json` and the experiment manifest.

### 4. OLED Assignment Page

Before or at experiment start, OLED should show:

```text
SWARM
correlation_sweep
unit inc_8F0C
corr 0.37
```

This helps catch wrong-card/wrong-unit mistakes.

### 5. Optional AP Swarm Tab

Add an AP page that can display the loaded assigned config and allow:

- Start assigned swarm experiment.
- Reject/delete assigned config.
- Run hardware test.
- Fall back to manual config.

The AP should not generate swarm assignments itself, and it is not part of the Version 0 swarm deployment path.

## Host-Side Tooling Proposed Later

### `swarm_planner.py`

Core functions:

- Read swarm spec.
- Validate schema.
- Generate `n = swarm_size` ordered assignments.
- Write the full `bulk_config.json`.
- Write one derived per-device config per assignment index.
- Write manifest and assignment table.
- Support dry run.

Example commands:

```bash
python3 Smart_incubator/swarm_planner.py generate Smart_incubator/swarm_specs/correlation_sweep.json
python3 Smart_incubator/swarm_planner.py show Smart_incubator/swarm_configs/correlation_sweep_2026_06_09_a/manifest.json
```

### `swarm_deploy.py`

Core functions:

- Track the next unflashed assignment index.
- Query connected ESP32 unit ID if available.
- Upload the selected assignment chunk as `/swarm_config.json`.
- Upload production firmware and `/swarm_config.json`.
- Verify uploaded config hash.
- Record deployment status.

Example commands:

```bash
python3 Smart_incubator/swarm_deploy.py --manifest Smart_incubator/swarm_configs/correlation_sweep_2026_06_09_a/manifest.json --port /dev/cu.usbserial-0001
python3 Smart_incubator/swarm_deploy.py --manifest Smart_incubator/swarm_configs/correlation_sweep_2026_06_09_a/manifest.json --next --port /dev/cu.usbserial-0001
python3 Smart_incubator/swarm_deploy.py --manifest Smart_incubator/swarm_configs/correlation_sweep_2026_06_09_a/manifest.json --slot 3 --port /dev/cu.usbserial-0001
python3 Smart_incubator/swarm_deploy.py --manifest Smart_incubator/swarm_configs/correlation_sweep_2026_06_09_a/manifest.json --all-ports
```

### Local Dashboard

Once the command-line flow works, add a local dashboard for experiment design:

- Enter base parameters once.
- Choose sweep parameter.
- Choose distribution and bounds.
- Preview histogram/table of assignments.
- Lock manifest.
- Deploy unit-by-unit.
- Track deployment status.

This should run on the laptop, not the ESP32.

## Data Analysis Integration

Post-run analysis should be able to join logged SD data back to the swarm manifest by:

- `swarm_id`
- `unit_id`
- `assignment_index`
- `experiment_id`

Recommended outputs:

- `assignments.csv`: one row per incubator.
- `manifest.json`: complete reproducible spec.
- `analysis_index.csv`: generated after SD card collection, linking SD data paths to assignments.

This avoids relying on experiment folder names alone.

## Validation Plan

### Host-Side Tests

- Schema validation rejects invalid parameters.
- Distribution generation is reproducible for a fixed seed.
- Assignment count matches device count.
- Bound checks work for all sweepable parameters.
- Config hash changes when relevant fields change.
- Existing fixed-parameter experiment can be represented as a swarm of size 1.

### Firmware Tests

- Device loads `/swarm_config.json`.
- Missing config falls back to AP mode.
- Invalid config falls back safely and reports error on OLED/serial.
- Valid config bypasses AP and starts the assigned swarm chunk from boot.
- `meta.json` contains full swarm metadata.
- Normal experiment behavior is unchanged when no swarm config exists.

### Hardware/Operational Tests

- Deploy two devices with identical base config and different swept values.
- Verify OLED shows correct assignment on each unit.
- Run short hardware test before full experiment.
- Run a short simulated cycle and confirm SD metadata matches manifest.
- Confirm legacy SD card and strict-CRC SD card both still mount.

## Risks And Mitigations

### Risk: Wrong Assignment On Wrong Unit

Mitigation:

- Treat assignment order as explicit and visible.
- Print and display the assignment index before and after flashing.
- Use stable `unit_id` from MAC/device ID when available, even if the primary workflow is ordered flashing.
- Show assignment on OLED.
- Write config hash to manifest and SD metadata.
- Require explicit `--slot` if the operator wants to flash out of order.
- Record physical label, observed device ID, port, timestamp, and config hash in the manifest.

### Risk: Correlation Semantics Are Misunderstood

Mitigation:

- Define each sweepable parameter in the spec schema.
- Use the label `correlation` consistently in UI, manifests, device configs, OLED text, and analysis outputs.
- Display the allowed range and current firmware meaning beside the field where space allows.

### Risk: Runtime Heap Pressure

Mitigation:

- Keep sampling and manifest generation on laptop.
- Upload only compact assigned config to ESP32.
- Load config before heavy modules.
- Remove AP/setup modules from `sys.modules` before experiment, as current firmware already does.

### Risk: Reproducibility Loss

Mitigation:

- Use explicit seeds.
- Store complete manifest.
- Store per-device config and config hash.
- Do not regenerate an existing swarm ID without force.

### Risk: Simultaneous WiFi AP Management Is Awkward

Mitigation:

- Start with USB sequential deployment.
- Treat WiFi swarm deployment as a later version.

## Open Questions

1. Should one swarm support multiple simultaneous swept parameters, or only one parameter at first?
2. Do we want random sampling, evenly spaced grid values, or balanced replicates as the default?
3. How should units be identified physically: MAC-derived ID, printed label, QR code, SD card label, or all of these?
4. Should stress-test mode also support swarm assignment, or only the main experiment at first?
5. Should deployment write config to ESP32 flash, SD card, or both?
6. Should ordered flashing require a printed checklist or QR label workflow to reduce operator error?

## Recommended MVP

Build the smallest useful system in this order:

1. Define `swarm_spec.json`, `bulk_config.json`, and per-device `swarm_config.json` schemas.
2. Implement host-side `swarm_planner.py` with deterministic ordered assignments and a manifest.
3. Add firmware support for loading `/swarm_config.json` before AP setup.
4. Extend SD metadata with swarm fields.
5. Add `swarm_deploy.py --next` for ordered sequential USB flashing.
6. Make valid swarm configs boot directly into the assigned experiment chunk without AP setup.
7. Test with two or three incubators using a simple `correlation` sweep.
8. After that, add additional sweep parameters such as `basal_temp` or stimulus intensity.

This gives us a real swarm deployment flow while keeping the current AP workflow available as fallback and recovery tooling.
