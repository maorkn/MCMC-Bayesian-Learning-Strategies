# Markovian Hidden Environmental States (HES) Feature Outline

## Overview

This document outlines the design and implementation plan for a Markovian Hidden Environmental States (HES) experimental framework for the Smart Incubator platform. This feature enables researchers to create complex, stochastic environmental sequences that test whether single-celled organisms can learn predictable versus unpredictable environmental patterns.

## Conceptual Background

### Hidden Environmental States (HES)
Based on the simulation model in the manuscript, Hidden Environmental States represent discrete environmental conditions, each characterized by specific actuator settings (temperature, LED intensity, vibration patterns). Organisms experience these states sequentially, with transitions governed by either:
- **Deterministic progression** (canonical sequence): HES 0 → 1 → 2 → 3 → 4 → 0...
- **Markovian stochastic transitions**: Probabilistic jumps to non-sequential states

### Markovian Transition Logic
The `Markovian_p` parameter controls environmental predictability:
- **Markovian_p = 0**: Fully deterministic, follows canonical sequence
- **Markovian_p = 0.5**: 50% chance of following sequence, 50% chance of random jump
- **Markovian_p = 1.0**: Fully stochastic, always jumps to random state

**Transition Probability Formula:**
```
If at HES[i]:
  - P(next = HES[i+1]) = 1 - Markovian_p
  - P(next = any other HES[j≠i+1]) = Markovian_p / (num_HES - 1)
```

**Example with 5 states, Markovian_p = 0.3, currently at HES 0:**
- P(HES 1) = 0.7 (70% chance to follow sequence)
- P(HES 2) = 0.075 (7.5% chance)
- P(HES 3) = 0.075 (7.5% chance)
- P(HES 4) = 0.075 (7.5% chance)
- P(HES 0) = 0.075 (7.5% chance to stay)

---

## Architecture Overview

### File Structure
```
Smart_incubator/
├── Firmware/
│   ├── markovian_hes_executor.py    # Main execution script (NEW)
│   ├── hes_config_loader.py         # Configuration file parser (NEW)
│   ├── hes_transition_engine.py     # Markovian transition logic (NEW)
│   ├── hes_actuator_controller.py   # Coordinated actuator control (NEW)
│   ├── hes_logger.py                # HES-specific data logging (NEW)
│   └── (existing hardware modules)
├── Configs/                          # Configuration directory (NEW)
│   ├── example_deterministic_5state.json
│   ├── example_stochastic_3state.json
│   └── experiment_template.json
└── Docs/
    └── MARKOVIAN_HES_FEATURE_OUTLINE.md  (this file)
```

### Component Responsibilities

#### 1. **markovian_hes_executor.py** (Main Script)
- Initialize hardware (temperature sensor, actuators, SD card, display)
- Load HES configuration from JSON file
- Execute main experiment loop:
  - Stay in current HES for specified duration
  - Log actuator state and HES every 10 seconds
  - Determine next HES using transition engine
  - Transition to next HES (with optional ramping)
- Handle errors and emergency shutdown
- Generate experiment summary on completion

#### 2. **hes_config_loader.py** (Configuration Parser)
- Load and validate JSON configuration files
- Parse HES definitions (actuator settings, durations)
- Extract experiment metadata (name, canonical sequence, Markovian_p)
- Validate parameter ranges (temp: 15-40°C, LED: 0-100%, etc.)
- Provide default values for optional parameters

#### 3. **hes_transition_engine.py** (Transition Logic)
- Implement Markovian transition probability calculations
- Random state selection based on `Markovian_p`
- Track transition history (for analysis)
- Calculate transition statistics in real-time

#### 4. **hes_actuator_controller.py** (Coordinated Control)
- Unified interface for all actuators
- **Instant transitions**: Immediate actuator value changes
- **Ramped transitions**: Linear interpolation over specified duration
  - Example: Temp 23°C → 32°C over 10 minutes
  - Calculate step size and update interval
- Maintain actuator state consistency
- Safety limits enforcement

#### 5. **hes_logger.py** (Data Logging)
- Create timestamped experiment directory
- Log HES sequence data:
  - Timestamp of each HES entry/exit
  - HES index and canonical position
  - Transition type (sequential vs. jump)
  - Duration spent in HES
- Log actuator data (every 10 seconds):
  - Current temperature (measured)
  - Target temperature (setpoint)
  - LED intensity (current %)
  - Vibration state (on/off, pattern, intensity)
  - TEC/PTC power output
- Generate summary statistics:
  - Total time per HES
  - Transition matrix (observed probabilities)
  - Entropy of state sequence
- JSON format with SHA-256 checksums (compatible with existing system)

---

## Configuration File Specification

### JSON Schema

```json
{
  "experiment_metadata": {
    "name": "Markovian_5State_p03_Test",
    "description": "5-state HES with 30% stochasticity to test learning thresholds",
    "researcher": "Maor Knafo",
    "organism": "Capsaspora owczarzaki",
    "culture_volume_ml": 10,
    "date_created": "2025-10-13"
  },
  
  "markovian_parameters": {
    "num_HES": 5,
    "canonical_sequence": [0, 1, 2, 3, 4],
    "Markovian_p": 0.3,
    "loop_mode": "continuous",
    "max_cycles": null,
    "max_duration_hours": 72
  },
  
  "genetic_lock_in": {
    "enable_lock_in": true,
    "lock_in_cycles": 100,
    "new_canonical_sequence": [0, 2, 4, 1, 3],
    "lock_in_transition_type": "instant",
    "maintain_markovian_p": true,
    "log_lock_in_event": true
  },
  
  "HES_definitions": [
    {
      "HES_index": 0,
      "name": "Basal_Rest",
      "duration": {
        "type": "fixed",
        "value_minutes": 60
      },
      "actuators": {
        "temperature": {
          "value_celsius": 23.0,
          "transition_type": "instant"
        },
        "LED": {
          "intensity_percent": 10,
          "transition_type": "instant"
        },
        "vibration": {
          "enabled": true,
          "on_seconds": 5,
          "off_seconds": 100,
          "intensity_percent": 100,
          "transition_type": "instant"
        }
      }
    },
    {
      "HES_index": 1,
      "name": "Heat_Stress",
      "duration": {
        "type": "fixed",
        "value_minutes": 30
      },
      "actuators": {
        "temperature": {
          "value_celsius": 32.0,
          "transition_type": "ramp",
          "ramp_duration_minutes": 5
        },
        "LED": {
          "intensity_percent": 25,
          "transition_type": "instant"
        },
        "vibration": {
          "enabled": false
        }
      }
    },
    {
      "HES_index": 2,
      "name": "Light_Pulse",
      "duration": {
        "type": "random",
        "min_minutes": 40,
        "max_minutes": 80
      },
      "actuators": {
        "temperature": {
          "value_celsius": 27.0,
          "transition_type": "ramp",
          "ramp_duration_minutes": 10
        },
        "LED": {
          "intensity_percent": 75,
          "transition_type": "ramp",
          "ramp_duration_minutes": 3
        },
        "vibration": {
          "enabled": true,
          "on_seconds": 10,
          "off_seconds": 50,
          "intensity_percent": 80,
          "transition_type": "instant"
        }
      }
    },
    {
      "HES_index": 3,
      "name": "Recovery_Phase",
      "duration": {
        "type": "fixed",
        "value_minutes": 45
      },
      "actuators": {
        "temperature": {
          "value_celsius": 25.0,
          "transition_type": "ramp",
          "ramp_duration_minutes": 8
        },
        "LED": {
          "intensity_percent": 15,
          "transition_type": "ramp",
          "ramp_duration_minutes": 5
        },
        "vibration": {
          "enabled": true,
          "on_seconds": 2,
          "off_seconds": 60,
          "intensity_percent": 50,
          "transition_type": "instant"
        }
      }
    },
    {
      "HES_index": 4,
      "name": "Preparatory_Cue",
      "duration": {
        "type": "random",
        "min_minutes": 20,
        "max_minutes": 40
      },
      "actuators": {
        "temperature": {
          "value_celsius": 23.0,
          "transition_type": "ramp",
          "ramp_duration_minutes": 12
        },
        "LED": {
          "intensity_percent": 50,
          "transition_type": "ramp",
          "ramp_duration_minutes": 2
        },
        "vibration": {
          "enabled": true,
          "on_seconds": 20,
          "off_seconds": 60,
          "intensity_percent": 100,
          "transition_type": "instant"
        }
      }
    }
  ],
  
  "logging_parameters": {
    "snapshot_interval_seconds": 10,
    "save_raw_temperature": true,
    "save_pid_output": true,
    "calculate_statistics": true
  },
  
  "safety_parameters": {
    "max_temperature_celsius": 40.0,
    "min_temperature_celsius": 18.0,
    "enable_failsafe": true,
    "emergency_shutdown_temp": 42.0
  }
}
```

### Configuration Parameters Explained

#### Experiment Metadata
- **name**: Unique identifier for experiment
- **description**: Human-readable experiment summary
- **researcher**: Principal investigator
- **organism**: Species under study
- **culture_volume_ml**: Volume for dilution rate calculations
- **date_created**: ISO format date

#### Markovian Parameters
- **num_HES**: Total number of Hidden Environmental States (2-10 recommended)
- **canonical_sequence**: Array defining deterministic order [0,1,2,3,4]
- **Markovian_p**: Stochasticity level (0.0 = deterministic, 1.0 = fully random)
- **loop_mode**: "continuous" (cycles indefinitely) or "single_pass" (one sequence then stop)
- **max_cycles**: Maximum number of complete canonical sequences (null = unlimited)
- **max_duration_hours**: Maximum experiment runtime (null = unlimited)

#### Genetic Lock-In Parameters (Optional)
- **enable_lock_in**: Boolean, enables sequence shift after adaptation period
- **lock_in_cycles**: Number of complete cycles before shifting to new sequence
- **new_canonical_sequence**: New sequence to adopt after lock-in (permutation of original)
- **lock_in_transition_type**: "instant" (immediate shift) or "gradual" (phased over N transitions)
- **maintain_markovian_p**: Boolean, if true, keeps same stochasticity level after shift

#### HES Definitions
Each HES contains:

**Duration:**
- `type: "fixed"`: Constant duration, specify `value_minutes`
- `type: "random"`: Randomized duration, specify `min_minutes` and `max_minutes`

**Actuators:**

*Temperature:*
- `value_celsius`: Target temperature (15-40°C range)
- `transition_type`: 
  - `"instant"`: Jump immediately
  - `"ramp"`: Linear interpolation over `ramp_duration_minutes`

*LED:*
- `intensity_percent`: LED brightness (0-100%)
- `transition_type`: Same as temperature

*Vibration:*
- `enabled`: Boolean on/off
- `on_seconds`: Active vibration duration
- `off_seconds`: Inactive vibration duration
- `intensity_percent`: Vibration motor PWM (0-100%)
- `transition_type`: Typically "instant" (on/off patterns don't ramp well)

*Media Spike:*
- `spike_type`: Type of media addition ("fresh_media", "nutrient_pulse", "dilution")
- `volume_ml`: Volume to add (0.1-5.0 mL)
- `dilution_factor`: Effective dilution (0.0-1.0)
- `transition_type`: Typically "instant" (immediate injection)

*FBS (Fetal Bovine Serum) Spike:*
- `concentration_percent`: Final FBS concentration (0-20%)
- `volume_ml`: Volume to inject (0.1-2.0 mL)
- `transition_type`: "instant" or "ramp" (gradual addition over minutes)

*pH Modulation:*
- `target_pH`: Target pH value (6.0-8.5)
- `acid_pump_duration_ms`: Duration to run acid pump (0-5000 ms)
- `base_pump_duration_ms`: Duration to run base pump (0-5000 ms)
- `transition_type`: "instant" or "ramp"
- `ramp_duration_minutes`: For gradual pH shifts

*Anesthetic (Lidocaine/Other):*
- `compound`: Anesthetic type ("lidocaine", "procaine", "propofol", "xenon", "sevoflurane")
- `concentration_uM`: Final concentration in micromolar (0-1000 μM)
- `volume_ml`: Volume to inject (0.01-1.0 mL)
- `stock_concentration_mM`: Stock solution concentration for calculation
- `transition_type`: Typically "instant" (immediate injection)
- `washout`: Boolean, whether to dilute out at end of HES
- `washout_volume_ml`: Volume to remove and replace with fresh media

---

## Data Logging Specification

### Directory Structure
```
/sd/data/markovian_experiments/
└── YYYYMMDD_HHMMSS_ExperimentName/
    ├── config.json                      # Copy of configuration file
    ├── experiment_metadata.json         # System info, start time, etc.
    ├── hes_sequence.json                # HES transition log
    ├── actuator_timeseries.json         # Actuator data (10-sec snapshots)
    ├── transition_matrix.json           # Observed transition probabilities
    ├── statistics_summary.json          # Experiment statistics
    └── checksums.txt                    # SHA-256 for all files
```

### File Formats

#### hes_sequence.json
```json
{
  "experiment_name": "Markovian_5State_p03_Test",
  "start_time": "2025-10-13T14:30:00",
  "transitions": [
    {
      "transition_index": 0,
      "timestamp": "2025-10-13T14:30:00",
      "from_HES": null,
      "to_HES": 0,
      "HES_name": "Basal_Rest",
      "transition_type": "initial",
      "planned_duration_min": 60,
      "actual_duration_min": 60.02
    },
    {
      "transition_index": 1,
      "timestamp": "2025-10-13T15:30:02",
      "from_HES": 0,
      "to_HES": 1,
      "HES_name": "Heat_Stress",
      "transition_type": "sequential",
      "probability": 0.7,
      "planned_duration_min": 30,
      "actual_duration_min": 30.01
    },
    {
      "transition_index": 2,
      "timestamp": "2025-10-13T16:00:03",
      "from_HES": 1,
      "to_HES": 4,
      "HES_name": "Preparatory_Cue",
      "transition_type": "stochastic_jump",
      "probability": 0.075,
      "planned_duration_min": 32,
      "actual_duration_min": 32.15
    }
  ]
}
```

#### actuator_timeseries.json
```json
{
  "experiment_name": "Markovian_5State_p03_Test",
  "sampling_interval_seconds": 10,
  "snapshots": [
    {
      "timestamp": "2025-10-13T14:30:00",
      "elapsed_seconds": 0,
      "current_HES": 0,
      "HES_name": "Basal_Rest",
      "temperature": {
        "measured_celsius": 23.1,
        "target_celsius": 23.0,
        "deviation_celsius": 0.1,
        "pid_output_percent": 5.2,
        "heater_active": true,
        "cooler_active": false
      },
      "LED": {
        "intensity_percent": 10,
        "target_intensity_percent": 10
      },
      "vibration": {
        "enabled": true,
        "current_state": "on",
        "on_seconds": 5,
        "off_seconds": 100,
        "intensity_percent": 100,
        "time_in_state_seconds": 2.3
      }
    },
    {
      "timestamp": "2025-10-13T14:30:10",
      "elapsed_seconds": 10,
      "current_HES": 0,
      "HES_name": "Basal_Rest",
      "temperature": {
        "measured_celsius": 23.0,
        "target_celsius": 23.0,
        "deviation_celsius": 0.0,
        "pid_output_percent": 0.0,
        "heater_active": false,
        "cooler_active": false
      },
      "LED": {
        "intensity_percent": 10,
        "target_intensity_percent": 10
      },
      "vibration": {
        "enabled": true,
        "current_state": "off",
        "on_seconds": 5,
        "off_seconds": 100,
        "intensity_percent": 100,
        "time_in_state_seconds": 7.7
      }
    }
  ]
}
```

#### transition_matrix.json
```json
{
  "experiment_name": "Markovian_5State_p03_Test",
  "num_HES": 5,
  "canonical_sequence": [0, 1, 2, 3, 4],
  "configured_Markovian_p": 0.3,
  "total_transitions": 156,
  "observed_transition_matrix": {
    "from_HES_0": {
      "to_HES_0": 3,
      "to_HES_1": 24,
      "to_HES_2": 2,
      "to_HES_3": 1,
      "to_HES_4": 2
    },
    "from_HES_1": {
      "to_HES_0": 1,
      "to_HES_1": 0,
      "to_HES_2": 22,
      "to_HES_3": 3,
      "to_HES_4": 2
    },
    "...": "..."
  },
  "observed_probabilities": {
    "from_HES_0": {
      "to_HES_1": 0.75,
      "to_others": 0.25
    },
    "...": "..."
  },
  "entropy_metrics": {
    "sequence_entropy": 1.85,
    "max_possible_entropy": 2.32,
    "normalized_entropy": 0.80
  }
}
```

#### statistics_summary.json
```json
{
  "experiment_name": "Markovian_5State_p03_Test",
  "start_time": "2025-10-13T14:30:00",
  "end_time": "2025-10-16T14:30:00",
  "total_duration_hours": 72.0,
  "total_transitions": 156,
  "time_per_HES": {
    "HES_0": {
      "name": "Basal_Rest",
      "total_minutes": 1920,
      "visits": 32,
      "avg_duration_minutes": 60.0,
      "percent_of_experiment": 44.4
    },
    "HES_1": {
      "name": "Heat_Stress",
      "total_minutes": 840,
      "visits": 28,
      "avg_duration_minutes": 30.0,
      "percent_of_experiment": 19.4
    },
    "...": "..."
  },
  "temperature_statistics": {
    "mean_celsius": 25.8,
    "std_dev_celsius": 3.2,
    "min_celsius": 23.0,
    "max_celsius": 32.1,
    "time_above_30C_hours": 14.0
  },
  "transition_statistics": {
    "sequential_transitions": 109,
    "stochastic_jumps": 47,
    "observed_stochasticity": 0.301
  }
}
```

---

## Implementation Workflow

### Phase 1: Core Infrastructure (Week 1)
1. **Configuration Parser** (`hes_config_loader.py`)
   - JSON loading and validation
   - Schema checking
   - Default value handling
   - Error reporting

2. **Transition Engine** (`hes_transition_engine.py`)
   - Markovian probability calculator
   - Random state selection
   - Transition logging
   - Statistics tracking

### Phase 2: Actuator Control (Week 2)
3. **Actuator Controller** (`hes_actuator_controller.py`)
   - Unified actuator interface
   - Instant transition implementation
   - Ramped transition with linear interpolation
   - Safety limit enforcement

4. **HES Logger** (`hes_logger.py`)
   - Directory creation
   - JSON file writing
   - Timestamp management
   - Checksum generation

### Phase 3: Main Executor (Week 3)
5. **Main Script** (`markovian_hes_executor.py`)
   - Hardware initialization
   - Configuration loading
   - Main experiment loop
   - Error handling
   - Graceful shutdown

### Phase 4: Testing & Validation (Week 4)
6. **Create Example Configurations**
   - Deterministic 5-state (Markovian_p = 0)
   - Moderate stochasticity (Markovian_p = 0.2)
   - High stochasticity (Markovian_p = 0.8)
   - Short test run (3 states, 5 min each)

7. **Hardware Testing**
   - Verify actuator transitions (instant & ramp)
   - Validate timing accuracy
   - Check data logging integrity
   - Test emergency shutdown

8. **Data Analysis Scripts**
   - Transition matrix visualization
   - Entropy calculation
   - Actuator time-series plotting
   - Comparison to theoretical probabilities

---

## Usage Instructions

### Basic Usage

1. **Prepare Configuration File**
   ```bash
   # Copy template to Configs directory
   cp Configs/experiment_template.json Configs/my_experiment.json
   
   # Edit configuration
   nano Configs/my_experiment.json
   ```

2. **Upload to ESP32**
   ```bash
   # Using Thonny or ampy
   ampy --port /dev/ttyUSB0 put markovian_hes_executor.py
   ampy --port /dev/ttyUSB0 put hes_config_loader.py
   ampy --port /dev/ttyUSB0 put hes_transition_engine.py
   ampy --port /dev/ttyUSB0 put hes_actuator_controller.py
   ampy --port /dev/ttyUSB0 put hes_logger.py
   ampy --port /dev/ttyUSB0 put Configs/my_experiment.json /sd/my_experiment.json
   ```

3. **Run Experiment**
   ```python
   # In Thonny REPL or main.py
   import markovian_hes_executor
   markovian_hes_executor.run_experiment("/sd/my_experiment.json")
   ```

4. **Monitor Progress**
   - OLED display shows: Current HES, elapsed time, next transition countdown
   - Serial output logs transitions and errors
   - SD card saves data in real-time

5. **Stop Experiment**
   ```python
   # Graceful stop (completes current HES)
   markovian_hes_executor.stop_experiment()
   
   # Emergency stop (immediate)
   markovian_hes_executor.emergency_stop()
   ```

### Advanced Usage

**Running from Boot:**
```python
# Edit boot.py to auto-start experiment
import markovian_hes_executor
markovian_hes_executor.run_experiment("/sd/auto_experiment.json")
```

**Real-time Parameter Adjustment:**
```python
# Modify Markovian_p during run (for adaptive experiments)
markovian_hes_executor.update_markovian_p(0.5)
```

**Multi-Day Experiments:**
```json
// In config file
"markovian_parameters": {
  "loop_mode": "continuous",
  "max_duration_hours": 168  // 1 week
}
```

---

## Analysis Tools & Visualization

### Planned Analysis Scripts (Python on host computer)

1. **transition_matrix_plotter.py**
   - Heatmap of observed transition probabilities
   - Compare to theoretical Markovian model
   - Statistical significance testing (chi-square)

2. **entropy_analyzer.py**
   - Calculate Shannon entropy of HES sequence
   - Time-resolved entropy (sliding window)
   - Predictability metrics

3. **actuator_timeseries_plotter.py**
   - Multi-panel plots (temperature, LED, vibration)
   - HES annotations on timeline
   - Transition markers

4. **learning_detector.py**
   - Detect non-random patterns in state visits
   - Identify preferred sequences
   - Test for temporal correlations

### Example Visualization Output

```
Transition Matrix Heatmap:
         To HES 0  To HES 1  To HES 2  To HES 3  To HES 4
From HES 0   0.06      0.75      0.06      0.06      0.06
From HES 1   0.05      0.04      0.71      0.10      0.10
From HES 2   0.08      0.07      0.07      0.69      0.09
From HES 3   0.09      0.08      0.07      0.06      0.70
From HES 4   0.72      0.07      0.07      0.07      0.07

Entropy Analysis:
- Sequence Entropy: 1.85 bits
- Max Possible Entropy: 2.32 bits (log2(5))
- Normalized Entropy: 0.80 (80% of maximum randomness)
- Predictability Score: 0.20 (20% predictable)
```

---

## Experimental Design Recommendations

### Testing Markovian Learning Hypothesis

**Experimental Series:**

1. **Baseline (Markovian_p = 0)**: Fully predictable, deterministic sequence
   - Expected: Organisms learn optimal preparatory responses
   - Measure: Response latency decreases over cycles
   - Duration: 3-5 days (50+ complete cycles)

2. **Low Stochasticity (Markovian_p = 0.1-0.2)**: Mostly predictable with occasional surprises
   - Expected: Organisms maintain learned response, slowly adapt to surprises
   - Measure: Response persistence vs. adaptation rate
   - Duration: 5-7 days (70+ cycles)

3. **Moderate Stochasticity (Markovian_p = 0.3-0.5)**: Balanced predictability
   - Expected: Threshold where learning breaks down
   - Measure: Response variability increases, entropy of phenotypic states
   - Duration: 7-10 days (100+ cycles)

4. **High Stochasticity (Markovian_p = 0.6-0.8)**: Mostly unpredictable
   - Expected: Organisms abandon predictive strategy, adopt generalist phenotype
   - Measure: Response latency returns to baseline, reduced phenotypic variance
   - Duration: 3-5 days (50+ cycles)

5. **Fully Random (Markovian_p = 1.0)**: No predictability
   - Expected: Pure reactive behavior, no anticipation
   - Measure: Baseline response characteristics
   - Duration: 3-5 days (50+ cycles)

### Recommended HES Design Patterns

**Pattern 1: Classical Conditioning Analog**
```
HES 0: Basal (neutral)
HES 1: Cue (LED flash) - preparatory signal
HES 2: Stress (heat shock) - follows cue in deterministic mode
HES 3: Recovery (return to basal)
```

**Pattern 2: Multi-Modal Landscape**
```
HES 0: Cool + Dim + No Vibration
HES 1: Warm + Bright + No Vibration
HES 2: Hot + Dim + High Vibration (compound stress)
HES 3: Cool + Bright + Low Vibration (mixed signals)
HES 4: Optimal (23°C, moderate light, gentle vibration)
```

**Pattern 3: Circadian-Like Cycling**
```
HES 0: Dawn (warming, increasing light)
HES 1: Day (warm, bright)
HES 2: Dusk (cooling, decreasing light)
HES 3: Night (cool, dark)
```

**Pattern 4: Anesthetic Inhibition Test (Orch OR Hypothesis)**
```
Control Phase (Cycles 1-50):
HES 0: Basal (23°C, 10% light, no drug)
HES 1: Preparatory Cue (LED pulse, vibration)
HES 2: Stress (heat, 32°C)
HES 3: Recovery (return to basal)

Treatment Phase (Cycles 51-100):
HES 0: Basal + Lidocaine 100μM
HES 1: Preparatory Cue + Lidocaine 100μM
HES 2: Stress + Lidocaine 100μM (heat, 32°C)
HES 3: Recovery + Lidocaine washout

Washout Phase (Cycles 101-150):
HES 0-3: Same as Control Phase (no drug)
```

**Hypothesis**: If learning requires quantum coherence in microtubules (Orch OR), lidocaine should:
- Abolish learned anticipatory responses during treatment phase
- Preserve reactive responses (heat shock proteins still induced)
- Show recovery of learning after washout (if effect is reversible)

### Anesthetic Testing Experimental Design

#### Rationale
The **Orchestrated Objective Reduction (Orch OR)** theory by Penrose & Hameroff proposes that:
1. Consciousness/cognition emerges from quantum coherence in microtubules
2. Anesthetics work by disrupting this quantum coherence
3. Single-celled organisms with microtubules may exhibit similar sensitivity

**Key Predictions:**
- **Lidocaine** (sodium channel blocker + microtubule binding): Should inhibit learning but not basic stress responses
- **Propofol** (GABA modulator + microtubule effects): Should show similar learning inhibition
- **Xenon** (NMDA antagonist, minimal microtubule effects): May show weaker or no effect
- **Sevoflurane** (volatile anesthetic, microtubule binding): Should inhibit learning

#### Recommended Concentrations (for *Capsaspora owczarzaki*)

| Anesthetic | Concentration Range | Stock Solution | Expected Effect |
|------------|---------------------|----------------|-----------------|
| Lidocaine | 50-500 μM | 100 mM in H₂O | Microtubule disruption + Na⁺ channel block |
| Procaine | 100-1000 μM | 100 mM in H₂O | Microtubule disruption (weaker) |
| Propofol | 10-100 μM | 10 mM in DMSO | GABA modulation + microtubule binding |
| Xenon | Saturated (~4 mM) | Bubbled gas | NMDA antagonism (control for non-microtubule effects) |
| Sevoflurane | 1-5% (vol/vol) | Vapor delivery | Microtubule binding + membrane effects |

#### Experimental Protocol

**Phase 1: Baseline Learning (Markovian_p = 0, No Drug)**
- Duration: 50 cycles (~5-7 days)
- Measure: Establish learning baseline
  - Response latency to stress (HES 2)
  - Preparatory gene expression after cue (HES 1)
  - Phenotypic variance decrease over time

**Phase 2: Anesthetic Treatment (Same Markovian_p, Drug Present)**
- Duration: 50 cycles (~5-7 days)
- Concentration: Start with EC₅₀ (e.g., 100 μM lidocaine)
- Prediction: Learning disrupted, but stress responses intact
  - Response latency returns to baseline (no anticipation)
  - Preparatory cues no longer trigger adaptive responses
  - But reactive stress responses (HSPs, etc.) still occur

**Phase 3: Washout & Recovery (No Drug)**
- Duration: 50 cycles (~5-7 days)
- Measure: Recovery of learning ability
  - If reversible: Learning re-emerges within 10-20 cycles
  - If irreversible: Persistent learning deficit (suggests structural damage)

**Phase 4: Dose-Response (Multiple Concentrations)**
- Test: 0, 10, 50, 100, 250, 500 μM lidocaine
- Measure: EC₅₀ for learning inhibition
- Compare to: Concentrations that inhibit growth or viability

#### Configuration Example: Lidocaine Learning Inhibition Test

```json
{
  "experiment_metadata": {
    "name": "Lidocaine_Learning_Inhibition_p0",
    "description": "Test Orch OR hypothesis: Does lidocaine abolish Markovian learning?",
    "hypothesis": "Lidocaine disrupts microtubule-based learning while preserving reactive responses"
  },
  
  "markovian_parameters": {
    "num_HES": 4,
    "canonical_sequence": [0, 1, 2, 3],
    "Markovian_p": 0.0,
    "max_cycles": 150
  },
  
  "genetic_lock_in": {
    "enable_lock_in": true,
    "lock_in_cycles": 50,
    "new_canonical_sequence": [0, 1, 2, 3],
    "lock_in_transition_type": "anesthetic_treatment",
    "anesthetic_phase": true
  },
  
  "HES_definitions": [
    {
      "HES_index": 0,
      "name": "Basal_Control",
      "duration": {"type": "fixed", "value_minutes": 60},
      "actuators": {
        "temperature": {"value_celsius": 23.0, "transition_type": "instant"},
        "LED": {"intensity_percent": 10, "transition_type": "instant"},
        "vibration": {"enabled": false},
        "anesthetic": {
          "compound": "lidocaine",
          "concentration_uM": 0,
          "transition_type": "instant",
          "enable_after_cycle": 50,
          "disable_after_cycle": 100
        }
      }
    },
    {
      "HES_index": 1,
      "name": "Preparatory_Cue",
      "duration": {"type": "fixed", "value_minutes": 20},
      "actuators": {
        "temperature": {"value_celsius": 23.0, "transition_type": "instant"},
        "LED": {
          "intensity_percent": 75,
          "transition_type": "ramp",
          "ramp_duration_minutes": 2
        },
        "vibration": {
          "enabled": true,
          "on_seconds": 10,
          "off_seconds": 30,
          "intensity_percent": 100
        },
        "anesthetic": {
          "compound": "lidocaine",
          "concentration_uM": 100,
          "enable_after_cycle": 50,
          "disable_after_cycle": 100
        }
      }
    },
    {
      "HES_index": 2,
      "name": "Heat_Stress",
      "duration": {"type": "fixed", "value_minutes": 30},
      "actuators": {
        "temperature": {
          "value_celsius": 32.0,
          "transition_type": "ramp",
          "ramp_duration_minutes": 5
        },
        "LED": {"intensity_percent": 25, "transition_type": "instant"},
        "vibration": {"enabled": false},
        "anesthetic": {
          "compound": "lidocaine",
          "concentration_uM": 100,
          "enable_after_cycle": 50,
          "disable_after_cycle": 100
        }
      }
    },
    {
      "HES_index": 3,
      "name": "Recovery",
      "duration": {"type": "fixed", "value_minutes": 40},
      "actuators": {
        "temperature": {
          "value_celsius": 23.0,
          "transition_type": "ramp",
          "ramp_duration_minutes": 8
        },
        "LED": {"intensity_percent": 10, "transition_type": "instant"},
        "vibration": {"enabled": false},
        "anesthetic": {
          "compound": "lidocaine",
          "concentration_uM": 0,
          "transition_type": "instant",
          "washout": true,
          "washout_volume_ml": 2.0
        }
      }
    }
  ]
}
```

#### Critical Measurements

**Learning-Specific Metrics:**
1. **Response Latency**: Time from HES 1 (cue) → preparatory gene expression
   - Control: Should decrease over cycles 1-50
   - Treatment: Should return to baseline (cycles 51-100)
   - Washout: Should re-decrease (cycles 101-150)

2. **Anticipatory Behavior**: Phenotypic changes during HES 1 (before stress)
   - Control: Organisms pre-adapt before HES 2
   - Treatment: No anticipatory changes (but respond reactively in HES 2)

3. **Phenotypic Variance**: Population heterogeneity
   - Control: Decreases as organisms converge on optimal strategy
   - Treatment: Increases (loss of coordinated response)

**Control Metrics (Should NOT Change):**
4. **Stress Response Amplitude**: Max HSP expression during HES 2
   - Should remain constant across all phases
   - Confirms lidocaine doesn't block basic stress machinery

5. **Growth Rate**: Cell division rate
   - Slight decrease acceptable (<20%), but not catastrophic
   - Rules out general toxicity

6. **Viability**: Live/dead assay
   - Should remain >95% across all phases

#### Expected Outcomes

**Hypothesis 1: Lidocaine Disrupts Learning (Supports Orch OR)**
- Phase 1: Learning evident (anticipatory responses)
- Phase 2: Learning abolished (no anticipation, only reaction)
- Phase 3: Learning recovers (reversible effect)
- Conclusion: Microtubule-based quantum processes mediate learning

**Hypothesis 2: Lidocaine Has No Effect (Refutes Orch OR)**
- All phases: Learning persists
- Conclusion: Learning is independent of microtubule coherence

**Hypothesis 3: Lidocaine Causes General Toxicity (Non-Specific)**
- Phase 2: Both learning AND reactive responses impaired
- Phase 3: No recovery
- Conclusion: Need lower dose or different anesthetic

#### Control Experiments

**Positive Control: High Markovian_p (No Learning Expected)**
- Run same protocol with Markovian_p = 0.8
- Neither control nor treatment should show learning
- Confirms assay sensitivity

**Vehicle Control: DMSO/Saline Only**
- For drugs requiring solvents (propofol in DMSO)
- Ensure solvent alone doesn't affect learning

**Structural Analog Control: Benzocaine**
- Similar structure to lidocaine but weaker microtubule binding
- Should show less or no effect on learning

**Non-Anesthetic Control: Tetracycline**
- Affects mitochondria but not microtubules
- Should not affect learning (unless mitochondria involved)

#### Mechanism Dissection

If lidocaine abolishes learning, test specificity:

**Test 1: Sodium Channel Involvement**
- Use **TTX (tetrodotoxin)**: Pure Na⁺ channel blocker, no microtubule effect
- If TTX has no effect → confirms microtubule mechanism

**Test 2: Microtubule Stabilization Rescue**
- Pre-treat with **taxol/paclitaxel**: Stabilizes microtubules
- If taxol rescues learning under lidocaine → confirms microtubule target

**Test 3: Temperature Dependence**
- Orch OR predicts quantum coherence is temperature-sensitive
- Test lidocaine effect at 15°C vs. 30°C
- Stronger effect at higher temp would support quantum decoherence mechanism

**Test 4: Ultrafast Recovery**
- If quantum coherence, recovery should be rapid (<1 cycle)
- If genetic/epigenetic, recovery should be slow (10-20 cycles)

#### Safety Considerations

**Toxicity Monitoring:**
- Lidocaine LD₅₀ in mammalian cells: ~1-5 mM
- Start with 10x lower (100 μM) for *Capsaspora*
- Monitor: Growth rate, morphology, membrane integrity

**Drug Stability:**
- Lidocaine in aqueous solution: Stable for weeks at 4°C
- Propofol: Light-sensitive, prepare fresh
- Xenon: Must bubble continuously (escapes solution)

**Washout Efficiency:**
- Single dilution removes ~80-90% of drug
- For complete washout, perform 2-3 serial dilutions
- Monitor residual drug with LC-MS if available

#### Analysis Scripts

Add to analysis pipeline:
- `analyze_anesthetic_effect.py`: Compare learning curves ±drug
- `latency_analyzer.py`: Quantify response timing changes
- `recovery_dynamics.py`: Model washout and re-learning kinetics

### Sample Size & Replication
- **Biological replicates**: 3-5 independent cultures per condition
- **Technical replicates**: 2-3 runs per culture
- **Control**: Always run Markovian_p = 0 (deterministic) in parallel
- **Total experiment time**: 2-4 weeks for complete series

---

## Safety & Error Handling

### Safety Features

1. **Temperature Limits**
   - Hard limit: 42°C (emergency shutdown)
   - Soft limit: 40°C (configurable in safety_parameters)
   - Minimum: 18°C (prevent cold stress)

2. **Failsafe Mechanisms**
   - Sensor fault detection (stuck readings, outliers)
   - Actuator verification (compare set vs. measured)
   - Watchdog timer (detect frozen main loop)
   - Power loss recovery (resume from last HES)

3. **Emergency Stop Conditions**
   - Temperature > 42°C for >30 seconds
   - Sensor disconnection
   - SD card full or write error
   - Manual stop command via serial

### Error Recovery

**Non-Critical Errors** (log but continue):
- Temporary sensor read failure (retry 3x)
- Slight timing deviation (<5% of HES duration)
- Display update failure

**Critical Errors** (safe shutdown):
- Persistent sensor failure (>5 consecutive reads)
- Temperature runaway (>2°C deviation for >5 minutes)
- File system corruption
- Hardware initialization failure

**Recovery Protocol:**
```python
def safe_shutdown():
    """Graceful shutdown on critical error"""
    # Turn off all heating
    heater.set_power(0)
    # Enable cooling
    cooler.set_power(100)
    # Flash error on LED
    led.flash_error_pattern()
    # Save emergency log
    logger.save_emergency_state()
    # Send alert via display
    display.show_error("CRITICAL ERROR - SYSTEM HALTED")
```

---

## Future Enhancements (Post-MVP)

### Implemented Features
1. **Genetic Lock-In**: Automatic sequence shift after N cycles to test adaptation resilience

### Phase 2 Features
2. **Adaptive Markovian_p**: Adjust stochasticity based on organism response
3. **Context-Dependent Transitions**: Different transition probabilities from each HES
4. **Reward-Based State Selection**: Bias transitions toward states that elicited strong responses
5. **Multi-Chamber Parallel Experiments**: Run different Markovian_p values simultaneously

### Phase 3 Features
5. **Real-Time Phenotype Feedback**: Integrate microscopy for response-based state transitions
6. **Machine Learning State Optimizer**: Automatically design HES to maximize learning detection
7. **Web Interface**: Remote monitoring and control via WiFi
8. **MQTT Integration**: Real-time data streaming to analysis pipeline

---

## Testing Checklist

### Unit Tests
- [ ] Configuration loader handles valid JSON
- [ ] Configuration loader rejects invalid ranges
- [ ] Transition engine produces correct probabilities
- [ ] Transition engine generates valid state sequences
- [ ] Actuator controller sets instant transitions
- [ ] Actuator controller ramps smoothly (measured)
- [ ] Logger creates correct directory structure
- [ ] Logger writes valid JSON

### Integration Tests
- [ ] Full experiment runs for 3 hours without errors
- [ ] Markovian_p = 0 produces only sequential transitions
- [ ] Markovian_p = 1 produces no sequential transitions
- [ ] Observed probabilities match configured Markovian_p (±10%)
- [ ] Temperature ramps complete within ±30 seconds
- [ ] LED ramps visible and smooth
- [ ] Vibration patterns execute correctly
- [ ] Data logging captures all transitions

### Hardware Tests
- [ ] Temperature sensor initialization succeeds
- [ ] PTC heater responds to PWM
- [ ] TEC cooler responds to PWM
- [ ] LED intensity control verified
- [ ] Vibration motor operates reliably
- [ ] SD card writes sustained for 24+ hours
- [ ] OLED display updates without lag

### Scientific Validation
- [ ] Deterministic sequence replicable across runs
- [ ] Stochastic sequences show correct entropy
- [ ] Transition statistics converge to theory with large N
- [ ] Actuator values logged match actual measured values
- [ ] Timing accuracy within ±1% of configured durations

---

## Conclusion

This Markovian HES feature provides a powerful experimental framework for testing adaptive learning in single-celled organisms. By creating environments with tunable predictability, researchers can:

1. **Test the MBA hypothesis**: Does *Capsaspora* behave as a Markovian-Bayesian Agent?
2. **Identify learning thresholds**: At what Markovian_p does predictive behavior break down?
3. **Measure plasticity costs**: How quickly can organisms switch strategies?
4. **Explore memory persistence**: Do learned responses persist through stochastic disruptions?

The modular design allows easy extension to more complex experimental paradigms while maintaining compatibility with existing Smart Incubator infrastructure.

---

## References & Related Documentation

- **Manuscript**: Draft_18_09_25.tex (Section: "The Simulated Environment")
- **Smart Incubator README**: ../README.md
- **Existing Firmware**: main.py, run_experiment_cycle.py
- **Temperature Controller**: temp_controller.py
- **US Control**: us_control.py
- **Data Logging**: sd_logger.py

---

**Document Version**: 1.0  
**Author**: Design outline for Maor Knafo  
**Date**: 2025-10-13  
**Status**: Ready for implementation review

---

## Appendix A: Example Minimal Configuration

```json
{
  "experiment_metadata": {
    "name": "Quick_Test_3State",
    "description": "Minimal 3-state test for validation"
  },
  
  "markovian_parameters": {
    "num_HES": 3,
    "canonical_sequence": [0, 1, 2],
    "Markovian_p": 0.0,
    "max_duration_hours": 1
  },
  
  "HES_definitions": [
    {
      "HES_index": 0,
      "name": "State_A",
      "duration": {"type": "fixed", "value_minutes": 10},
      "actuators": {
        "temperature": {"value_celsius": 23.0, "transition_type": "instant"},
        "LED": {"intensity_percent": 20, "transition_type": "instant"},
        "vibration": {"enabled": false}
      }
    },
    {
      "HES_index": 1,
      "name": "State_B",
      "duration": {"type": "fixed", "value_minutes": 10},
      "actuators": {
        "temperature": {"value_celsius": 28.0, "transition_type": "ramp", "ramp_duration_minutes": 3},
        "LED": {"intensity_percent": 50, "transition_type": "instant"},
        "vibration": {"enabled": true, "on_seconds": 5, "off_seconds": 30, "intensity_percent": 100}
      }
    },
    {
      "HES_index": 2,
      "name": "State_C",
      "duration": {"type": "fixed", "value_minutes": 10},
      "actuators": {
        "temperature": {"value_celsius": 23.0, "transition_type": "ramp", "ramp_duration_minutes": 5},
        "LED": {"intensity_percent": 10, "transition_type": "instant"},
        "vibration": {"enabled": false}
      }
    }
  ]
}
```

**Expected behavior**: 
- Total runtime: 30 minutes (10 min × 3 states) × 2 cycles = 60 minutes
- Sequence: 0→1→2→0→1→2 (deterministic)
- Temperature: 23°C → ramps to 28°C → ramps back to 23°C
- Perfect for hardware validation

---

## Appendix B: Transition Probability Mathematics

### General Formula

For a system with `n` HES states and Markovian parameter `p`:

**Transition from state i to state j:**

```
P(i → j) = {
    1 - p,              if j = (i + 1) mod n  [sequential transition]
    p / (n - 1),        if j ≠ (i + 1) mod n  [stochastic jump]
}
```

### Example Calculations

**5 states, Markovian_p = 0.3, currently at HES 2:**

```
Next state = (2 + 1) mod 5 = 3 (sequential)

P(2 → 3) = 1 - 0.3 = 0.70        (follow sequence)
P(2 → 0) = 0.3 / 4 = 0.075       (jump to 0)
P(2 → 1) = 0.3 / 4 = 0.075       (jump to 1)
P(2 → 4) = 0.3 / 4 = 0.075       (jump to 4)
P(2 → 2) = 0.3 / 4 = 0.075       (stay at 2)

Total: 0.70 + 4×0.075 = 0.70 + 0.30 = 1.00 ✓
```

**3 states, Markovian_p = 1.0, currently at HES 0:**

```
Next state = 1 (sequential, but p=1.0 so never taken)

P(0 → 1) = 1 - 1.0 = 0.00        (never follow sequence)
P(0 → 2) = 1.0 / 2 = 0.50        (jump to 2)
P(0 → 0) = 1.0 / 2 = 0.50        (stay at 0)

Total: 0.00 + 0.50 + 0.50 = 1.00 ✓
```

### Implementation in Python

```python
def calculate_transition_probabilities(current_HES, num_HES, markovian_p):
    """
    Calculate transition probabilities for all possible next states.
    
    Returns: dict mapping HES index -> probability
    """
    probabilities = {}
    next_sequential = (current_HES + 1) % num_HES
    
    # Sequential transition probability
    p_sequential = 1.0 - markovian_p
    
    # Stochastic jump probability (distributed equally among other states)
    p_jump = markovian_p / (num_HES - 1)
    
    for i in range(num_HES):
        if i == next_sequential:
            probabilities[i] = p_sequential
        else:
            probabilities[i] = p_jump
    
    return probabilities

def select_next_state(current_HES, num_HES, markovian_p):
    """
    Randomly select next HES based on transition probabilities.
    """
    import urandom
    
    probs = calculate_transition_probabilities(current_HES, num_HES, markovian_p)
    
    # Generate random number [0, 1)
    rand = urandom.random()
    
    # Select state based on cumulative probability
    cumulative = 0.0
    for state, prob in probs.items():
        cumulative += prob
        if rand < cumulative:
            return state
    
    # Fallback (should never reach here)
    return (current_HES + 1) % num_HES
```

---

## Appendix C: Genetic Lock-In Feature Details

### Overview
The genetic lock-in feature allows researchers to test organismal resilience by suddenly changing the canonical sequence after an adaptation period. This mimics the manuscript's "genetic lock-in" experiment (Figure 3B) where MBA populations experienced fitness collapse followed by rapid recovery.

### Configuration Example

```json
{
  "experiment_metadata": {
    "name": "Lock_In_Test_5State_p02",
    "description": "Test adaptation resilience with sequence shift after 100 cycles"
  },
  
  "markovian_parameters": {
    "num_HES": 5,
    "canonical_sequence": [0, 1, 2, 3, 4],
    "Markovian_p": 0.2,
    "loop_mode": "continuous",
    "max_cycles": 200,
    "max_duration_hours": null
  },
  
  "genetic_lock_in": {
    "enable_lock_in": true,
    "lock_in_cycles": 100,
    "new_canonical_sequence": [0, 3, 1, 4, 2],
    "lock_in_transition_type": "instant",
    "maintain_markovian_p": true,
    "log_lock_in_event": true,
    "lock_in_marker_HES": 0
  },
  
  "HES_definitions": [
    // ... same HES definitions as before
  ]
}
```

### Lock-In Parameters Explained

**enable_lock_in** (boolean)
- Set to `true` to activate lock-in feature
- Set to `false` to run normal continuous experiment

**lock_in_cycles** (integer)
- Number of complete canonical cycles before triggering shift
- Example: `100` means shift occurs after 100 complete traversals of [0→1→2→3→4]
- Note: Stochastic jumps don't count toward cycle completion

**new_canonical_sequence** (array)
- Permutation of original sequence indices
- Must contain same HES indices, just reordered
- Example: `[0, 1, 2, 3, 4]` → `[0, 3, 1, 4, 2]`
- Validation: Must be valid permutation (no duplicates, all indices present)

**lock_in_transition_type** (string)
- `"instant"`: Immediate shift to new sequence at next transition
- `"gradual"`: Phase in new sequence over multiple transitions (future feature)

**maintain_markovian_p** (boolean)
- `true`: Keep same Markovian_p value after shift
- `false`: Can specify new Markovian_p for post-shift period (future feature)

**log_lock_in_event** (boolean)
- `true`: Create detailed log of lock-in moment
- Records: timestamp, cycle count, current HES, organism state

**lock_in_marker_HES** (integer, optional)
- Which HES to use as cycle completion marker
- Default: 0 (count cycles by returns to HES 0)
- Useful if HES 0 has special meaning in your experiment

### Implementation Logic

```python
class MarkovianHESExecutor:
    def __init__(self, config):
        self.config = config
        self.current_sequence = config['markovian_parameters']['canonical_sequence']
        self.markovian_p = config['markovian_parameters']['Markovian_p']
        
        # Lock-in tracking
        self.lock_in_enabled = config.get('genetic_lock_in', {}).get('enable_lock_in', False)
        self.lock_in_cycles = config.get('genetic_lock_in', {}).get('lock_in_cycles', None)
        self.new_sequence = config.get('genetic_lock_in', {}).get('new_canonical_sequence', None)
        self.lock_in_triggered = False
        
        self.completed_cycles = 0
        self.cycle_start_HES = 0  # Track when we complete a cycle
        self.in_cycle = False
        
    def check_cycle_completion(self, current_HES, next_HES):
        """
        Check if we've completed a full canonical cycle.
        A cycle completes when we return to the starting HES via sequential transitions.
        """
        if not self.in_cycle and current_HES == self.cycle_start_HES:
            self.in_cycle = True
            
        # Check if we've traversed entire sequence and returned to start
        if self.in_cycle and next_HES == self.cycle_start_HES:
            self.completed_cycles += 1
            self.in_cycle = False
            print(f"[Lock-In] Completed cycle {self.completed_cycles}/{self.lock_in_cycles}")
            
            # Check if lock-in should trigger
            if self.lock_in_enabled and not self.lock_in_triggered:
                if self.completed_cycles >= self.lock_in_cycles:
                    self.trigger_lock_in()
                    
    def trigger_lock_in(self):
        """
        Execute the genetic lock-in: shift to new canonical sequence.
        """
        print("\n" + "="*60)
        print("🔒 GENETIC LOCK-IN TRIGGERED!")
        print("="*60)
        print(f"Old sequence: {self.current_sequence}")
        print(f"New sequence: {self.new_sequence}")
        print(f"Markovian_p: {self.markovian_p} (maintained)")
        print(f"Cycles completed: {self.completed_cycles}")
        print("="*60 + "\n")
        
        # Log lock-in event
        self.logger.log_lock_in_event(
            cycle_count=self.completed_cycles,
            old_sequence=self.current_sequence,
            new_sequence=self.new_sequence,
            timestamp=time.time()
        )
        
        # Switch to new sequence
        self.current_sequence = self.new_sequence.copy()
        self.lock_in_triggered = True
        
        # Reset cycle counter to track post-lock-in adaptation
        self.completed_cycles = 0
        
    def select_next_state(self, current_HES):
        """
        Select next HES using current canonical sequence.
        """
        # Find next state in current sequence (accounting for lock-in shifts)
        current_idx = self.current_sequence.index(current_HES)
        next_idx = (current_idx + 1) % len(self.current_sequence)
        next_sequential = self.current_sequence[next_idx]
        
        # Apply Markovian probability
        rand = urandom.random()
        if rand < (1.0 - self.markovian_p):
            # Follow sequence
            next_HES = next_sequential
            transition_type = "sequential"
        else:
            # Stochastic jump to any other state
            other_states = [s for s in self.current_sequence if s != next_sequential]
            next_HES = other_states[urandom.randint(0, len(other_states)-1)]
            transition_type = "stochastic_jump"
            
        # Check if cycle completed
        self.check_cycle_completion(current_HES, next_HES)
        
        return next_HES, transition_type
```

### Data Logging for Lock-In

The `hes_sequence.json` file will include lock-in metadata:

```json
{
  "experiment_name": "Lock_In_Test_5State_p02",
  "lock_in_enabled": true,
  "lock_in_triggered_at_cycle": 100,
  "lock_in_timestamp": "2025-10-13T18:45:23",
  "original_sequence": [0, 1, 2, 3, 4],
  "new_sequence": [0, 3, 1, 4, 2],
  
  "transitions": [
    {
      "transition_index": 0,
      "cycle_number": 1,
      "pre_lock_in": true,
      "canonical_sequence_active": [0, 1, 2, 3, 4],
      // ... standard transition data
    },
    // ... transitions 1-499 (cycles 1-100, pre-lock-in)
    {
      "transition_index": 500,
      "cycle_number": 100,
      "pre_lock_in": true,
      "canonical_sequence_active": [0, 1, 2, 3, 4],
      "lock_in_event": "ABOUT_TO_TRIGGER"
    },
    {
      "transition_index": 501,
      "cycle_number": 101,
      "pre_lock_in": false,
      "post_lock_in": true,
      "canonical_sequence_active": [0, 3, 1, 4, 2],
      "lock_in_event": "TRIGGERED",
      "lock_in_timestamp": "2025-10-13T18:45:23"
    },
    // ... transitions 502+ (cycles 101-200, post-lock-in)
  ]
}
```

### Expected Biological Outcomes

Based on Figure 3B from the manuscript:

**Phase 1: Pre-Lock-In (Cycles 1-100)**
- Organisms adapt to original sequence [0→1→2→3→4]
- Response latency decreases (learning)
- Phenotypic entropy decreases (convergence)
- Fitness increases toward optimum

**Phase 2: Lock-In Event (Cycle 100)**
- Sequence suddenly shifts to [0→3→1→4→2]
- Previous learned associations become maladaptive
- Expected: Immediate fitness drop (similar to manuscript's 39% drop)

**Phase 3: Post-Lock-In Adaptation (Cycles 101-200)**
- **MBA-like behavior**: Rapid re-learning of new sequence
  - Fitness recovers within 10-20 cycles
  - May exceed pre-lock-in fitness (better optimization)
- **BA-like behavior**: Slow or no adaptation
  - Fitness remains depressed
  - Requires genetic mutations to adapt

### Experimental Design Recommendations

**Single Lock-In Design:**
```
Markovian_p = 0.0 (deterministic)
Original sequence: [0, 1, 2, 3, 4]
Lock-in at cycle: 100
New sequence: [0, 4, 2, 1, 3]  (maximal disruption)
Continue for: 100 more cycles
```

**Multiple Lock-In Design** (future feature):
```json
"genetic_lock_in": {
  "enable_lock_in": true,
  "lock_in_schedule": [
    {
      "trigger_at_cycle": 100,
      "new_sequence": [0, 3, 1, 4, 2]
    },
    {
      "trigger_at_cycle": 200,
      "new_sequence": [0, 2, 4, 1, 3]
    },
    {
      "trigger_at_cycle": 300,
      "new_sequence": [0, 1, 2, 3, 4]  // return to original
    }
  ]
}
```

**Lock-In with Markovian_p Shift** (future feature):
```json
"genetic_lock_in": {
  "enable_lock_in": true,
  "lock_in_cycles": 100,
  "new_canonical_sequence": [0, 3, 1, 4, 2],
  "maintain_markovian_p": false,
  "new_markovian_p": 0.5,  // increase stochasticity post-shift
  "test_recovery_under_stress": true
}
```

### Validation Tests

**Test 1: Lock-In Triggers at Correct Cycle**
```python
assert executor.completed_cycles == 100 when lock_in_triggered == True
```

**Test 2: Sequence Actually Changes**
```python
assert executor.current_sequence == [0, 3, 1, 4, 2]
assert executor.current_sequence != original_sequence
```

**Test 3: Markovian_p Maintained**
```python
assert executor.markovian_p == 0.2  # unchanged
```

**Test 4: Transition Statistics Reset**
```python
# Pre-lock-in transitions should show adaptation to [0,1,2,3,4]
# Post-lock-in transitions should show adaptation to [0,3,1,4,2]
assert transition_matrix_pre != transition_matrix_post
```

**Test 5: Logging Captures Event**
```python
assert "lock_in_event" in transition_log[500]
assert transition_log[501]["post_lock_in"] == True
```

### Analysis Script Example

```python
# analyze_lock_in_recovery.py

import json
import matplotlib.pyplot as plt
import numpy as np

def analyze_lock_in_experiment(hes_sequence_file):
    """
    Analyze fitness recovery after genetic lock-in event.
    """
    with open(hes_sequence_file, 'r') as f:
        data = json.load(f)
    
    # Find lock-in event
    lock_in_cycle = data['lock_in_triggered_at_cycle']
    
    # Extract transition data
    transitions = data['transitions']
    
    # Calculate "fitness" proxy (e.g., % sequential transitions)
    window_size = 20
    fitness_over_time = []
    
    for i in range(len(transitions) - window_size):
        window = transitions[i:i+window_size]
        sequential_count = sum(1 for t in window if t['transition_type'] == 'sequential')
        fitness_proxy = sequential_count / window_size
        fitness_over_time.append({
            'cycle': window[0]['cycle_number'],
            'fitness': fitness_proxy
        })
    
    # Plot
    cycles = [f['cycle'] for f in fitness_over_time]
    fitness = [f['fitness'] for f in fitness_over_time]
    
    plt.figure(figsize=(12, 6))
    plt.plot(cycles, fitness, linewidth=2)
    plt.axvline(x=lock_in_cycle, color='red', linestyle='--', label='Lock-In Event')
    plt.xlabel('Cycle Number')
    plt.ylabel('Fitness Proxy (% Sequential Transitions)')
    plt.title('Recovery from Genetic Lock-In')
    plt.legend()
    plt.grid(alpha=0.3)
    
    # Calculate recovery metrics
    pre_lock_in_fitness = np.mean(fitness[max(0, lock_in_cycle-20):lock_in_cycle])
    post_lock_in_min = np.min(fitness[lock_in_cycle:lock_in_cycle+10])
    recovery_fitness = np.mean(fitness[-20:])
    
    fitness_drop = ((pre_lock_in_fitness - post_lock_in_min) / pre_lock_in_fitness) * 100
    recovery_percent = ((recovery_fitness - post_lock_in_min) / 
                        (pre_lock_in_fitness - post_lock_in_min)) * 100
    
    print(f"Pre-lock-in fitness: {pre_lock_in_fitness:.2f}")
    print(f"Fitness drop: {fitness_drop:.1f}%")
    print(f"Final fitness: {recovery_fitness:.2f}")
    print(f"Recovery: {recovery_percent:.1f}%")
    
    plt.savefig('lock_in_recovery.png', dpi=300, bbox_inches='tight')
    plt.show()

# Run analysis
analyze_lock_in_experiment('hes_sequence.json')
```

### Key Hypotheses for Lock-In Experiments

**Hypothesis 1: MBA Show Rapid Recovery**
- Fitness drops immediately post-lock-in
- But recovers within 10-20 cycles
- Final fitness may exceed pre-lock-in (better optimization)

**Hypothesis 2: BA Show No Recovery**
- Fitness drops and stays low
- No adaptation without new mutations
- Demonstrates cost of genetic inflexibility

**Hypothesis 3: Recovery Speed Depends on Markovian_p**
- Deterministic (p=0): Fast recovery (clear new pattern)
- Moderate (p=0.2): Slower recovery (pattern ambiguous)
- High (p=0.8): No recovery (pattern unlearnable)

**Hypothesis 4: Asymmetric Learning Rates**
- Unlearning old sequence: Fast (1-2 cycles)
- Learning new sequence: Slower (10-20 cycles)
- Hysteresis effect (history dependence)

---

## Appendix D: Orchestrated Objective Reduction (Orch OR) Testing

### Background: Quantum Cognition in Single Cells

The **Orch OR theory** (Penrose & Hameroff, 2014) proposes:
1. Consciousness arises from quantum computations in microtubules
2. Anesthetics disrupt quantum coherence → loss of consciousness
3. Single-celled organisms with microtubules may exhibit proto-consciousness

**Key Insight**: If *Capsaspora* exhibits Bayesian learning via microtubule-based quantum processes, anesthetics should:
- ✅ Abolish learning (anticipatory behavior)
- ✅ Preserve reactive responses (non-quantum processes)
- ✅ Show reversibility upon washout

### Anesthetic Mechanisms

| Anesthetic | Primary Target | Microtubule Effect | Orch OR Prediction |
|------------|----------------|--------------------|--------------------|
| **Lidocaine** | Na⁺ channels | Binds tubulin β-subunit | Disrupts quantum coherence |
| **Propofol** | GABAA receptors | Binds microtubule luminal surface | Strong coherence disruption |
| **Sevoflurane** | Multiple receptors | Hydrophobic pocket binding | Moderate disruption |
| **Xenon** | NMDA receptors | Minimal microtubule binding | Weak/no effect (negative control) |
| **Ketamine** | NMDA receptors | Unknown microtubule effects | Unknown (exploratory) |

### Experimental Logic: Dissociating Learning from Stress Response

```
                    ┌─────────────────┐
                    │  Environmental  │
                    │      Cue        │
                    │   (HES 1)       │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Microtubule   │
                    │     Quantum     │
                    │   Coherence?    │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
       ┌──────▼──────┐              ┌──────▼──────┐
       │  Learning   │              │  Reactive   │
       │(Anticipate) │              │  (Respond)  │
       └──────┬──────┘              └──────┬──────┘
              │                             │
              │ Lidocaine inhibits?         │ Unaffected
              │                             │
       ┌──────▼──────┐              ┌──────▼──────┐
       │ No Pre-     │              │ Normal HSP  │
       │ Adaptation  │              │ Induction   │
       └─────────────┘              └─────────────┘
```

**Critical Prediction**: Lidocaine should create a **dissociation**:
- Learning abolished (no anticipatory gene expression in HES 1)
- But stress response intact (normal HSP induction in HES 2)

### Detailed Protocol: Three-Phase Experiment

#### Phase 1: Baseline Learning (Cycles 1-50)
**Markovian_p = 0.0 (deterministic)**

```json
"HES_0": {"name": "Basal", "temp": 23, "LED": 10, "vib": false, "drug": null},
"HES_1": {"name": "Cue", "temp": 23, "LED": 75, "vib": true, "drug": null},
"HES_2": {"name": "Stress", "temp": 32, "LED": 25, "vib": false, "drug": null},
"HES_3": {"name": "Recovery", "temp": 23, "LED": 10, "vib": false, "drug": null}
```

**Measurements**:
- **t0 (Cycle 1)**: No anticipation, organisms respond reactively to HES 2
- **t1 (Cycle 25)**: Learning emerges, anticipatory changes in HES 1
- **t2 (Cycle 50)**: Full learning, strong anticipation before stress

**Expected**: Response latency ↓ 50%, phenotypic variance ↓ 30%

#### Phase 2: Anesthetic Treatment (Cycles 51-100)
**Same sequence, +100 μM lidocaine**

```json
"HES_0": {"drug": "lidocaine_100uM"},
"HES_1": {"drug": "lidocaine_100uM"},
"HES_2": {"drug": "lidocaine_100uM"},
"HES_3": {"drug": null, "washout": true}
```

**Measurements**:
- **t3 (Cycle 51)**: Immediate post-drug, check baseline shift
- **t4 (Cycle 75)**: Mid-treatment, assess learning suppression
- **t5 (Cycle 100)**: End treatment, check persistence

**Expected (Orch OR Supported)**:
- Anticipatory behavior abolished (back to Cycle 1 baseline)
- Reactive stress response unchanged (HSPs still induced)
- No re-learning during treatment (stays at baseline)

**Expected (Orch OR Refuted)**:
- Learning persists despite lidocaine
- Or both learning AND reactive responses impaired (non-specific toxicity)

#### Phase 3: Washout & Recovery (Cycles 101-150)
**No drug, test reversibility**

```json
"HES_0-3": {"drug": null}
```

**Measurements**:
- **t6 (Cycle 105)**: Immediate post-washout
- **t7 (Cycle 125)**: Mid-recovery
- **t8 (Cycle 150)**: Full recovery?

**Expected (Reversible)**:
- Learning re-emerges within 10-20 cycles
- Full recovery to pre-drug performance
- Suggests quantum coherence restored

**Expected (Irreversible)**:
- Persistent learning deficit
- Suggests structural damage (not quantum disruption)
- May need lower dose

### Dose-Response Curve

Test multiple lidocaine concentrations to find EC₅₀:

| Concentration | Expected Effect on Learning | Expected Toxicity |
|---------------|------------------------------|-------------------|
| 0 μM | No effect (baseline) | None |
| 10 μM | Minimal/no effect | None |
| 50 μM | Partial inhibition (~30%) | Minimal |
| 100 μM | Strong inhibition (~70%) | <10% growth reduction |
| 250 μM | Near-complete inhibition | ~20% growth reduction |
| 500 μM | Complete inhibition | ~40% growth reduction |
| 1000 μM | Complete inhibition | >60% growth reduction |

**Target**: Find concentration where learning is inhibited but viability >90%

### Comparative Anesthetic Panel

Run same protocol with multiple anesthetics:

**Primary Test (Microtubule-Binding)**:
1. Lidocaine 100 μM → Predict strong learning inhibition
2. Propofol 50 μM → Predict strong learning inhibition
3. Sevoflurane 2% → Predict moderate learning inhibition

**Negative Control (Minimal Microtubule Binding)**:
4. Xenon (saturated) → Predict weak/no learning inhibition
5. TTX 1 μM → Predict no learning inhibition (pure Na⁺ channel blocker)

**Mechanistic Probe (Microtubule Stabilizer)**:
6. Taxol 10 nM + Lidocaine 100 μM → Predict rescue of learning

**Expected Result Pattern**:
```
Learning Inhibition:
Propofol ≈ Lidocaine > Sevoflurane >> Xenon ≈ TTX

If this pattern holds → Strong support for microtubule-based learning
```

### Mechanistic Follow-Up Experiments

If lidocaine abolishes learning:

#### Experiment 1: Temperature Dependence
Quantum coherence is temperature-sensitive. Test lidocaine at:
- 15°C (low temp, longer coherence times)
- 23°C (standard)
- 30°C (high temp, shorter coherence times)

**Orch OR Prediction**: Lidocaine effect should be **weaker at low temperature** (harder to disrupt coherence)

#### Experiment 2: Microtubule Polymerization State
Test whether learning requires dynamic vs. stable microtubules:
- **Nocodazole** (low dose, 10 nM): Increases dynamics
- **Taxol** (10 nM): Stabilizes microtubules
- **Colchicine** (50 nM): Depolymerizes microtubules

**Prediction**: 
- Nocodazole → Enhances learning (more quantum events)
- Taxol → No effect or mild inhibition (too stable)
- Colchicine → Abolishes learning (no substrate)

#### Experiment 3: Ultrafast Recovery Kinetics
Measure how quickly learning recovers after lidocaine washout:
- **Quantum coherence**: Recovery within 1-2 transitions (<2 hours)
- **Epigenetic changes**: Recovery over 5-10 cycles (~1-2 days)
- **Genetic adaptation**: Recovery over 20+ cycles (>3 days)

**Method**: Sample every 30 minutes post-washout, measure anticipatory gene expression

#### Experiment 4: Electromagnetic Field Exposure
Orch OR predicts sensitivity to electromagnetic fields:
- Expose to 500 MHz RF during learning phase
- Should mimic anesthetic effect (disrupt coherence)

### Molecular Validation

#### RNA-seq at Key Timepoints
Compare gene expression in HES 1 (cue phase):

**t0 (No learning, Cycle 1)**: Baseline expression
**t2 (Full learning, Cycle 50)**: Anticipatory gene program
**t4 (Lidocaine, Cycle 75)**: Should revert to t0 profile
**t8 (Recovery, Cycle 150)**: Should match t2 profile

**Key genes to monitor**:
- Heat shock proteins (HSP70, HSP90)
- Chaperones (GroEL, DnaJ)
- Stress response TFs
- Microtubule-associated proteins (MAPs)

#### Imaging: Microtubule Dynamics
Use fluorescent tubulin to track:
- Microtubule polymerization rate during learning
- Changes under lidocaine treatment
- Recovery of normal dynamics after washout

**Prediction**: Learning phase should show altered microtubule dynamics

#### Electrophysiology (if feasible)
Measure membrane potential oscillations:
- Orch OR predicts ~40 Hz gamma oscillations in neurons
- Single cells may show similar frequency coherence
- Lidocaine should disrupt oscillatory patterns

### Alternative Interpretations & Controls

**If lidocaine inhibits learning, could it be:**

**Alt 1: Membrane excitability (Na⁺ channels)**
- **Test**: Use TTX (pure Na⁺ blocker, no microtubule effect)
- **If TTX has no effect** → Rules out Na⁺ channel explanation

**Alt 2: General metabolic stress**
- **Test**: Measure ATP levels, growth rate, viability
- **If normal metabolism** → Rules out non-specific toxicity

**Alt 3: Disrupted signaling cascades**
- **Test**: Measure MAPK, calcium signaling under lidocaine
- **If signaling intact** → Rules out signaling explanation

**Alt 4: Impaired protein trafficking**
- **Test**: Track fluorescent cargo transport along microtubules
- **If transport normal** → Rules out trafficking explanation

### Expected Publication Impact

**If Orch OR Supported** (lidocaine specifically abolishes learning):
- First evidence of quantum cognition in protists
- Challenges classical view of consciousness evolution
- Suggests microtubule-based computation is ancient
- Opens new field: "Quantum Cell Biology"

**If Orch OR Refuted** (no learning inhibition):
- Narrows search for learning mechanisms
- Still valuable negative result
- Suggests learning is classical (genetic/epigenetic)

**Most Likely Outcome** (partial inhibition):
- Learning may involve both quantum AND classical processes
- Dose-dependent effects reveal mechanistic hierarchy
- Opens nuanced view of basal cognition

### Recommended Reading

1. **Penrose & Hameroff (2014)**: "Consciousness in the universe: A review of the 'Orch OR' theory" *Physics of Life Reviews*
2. **Hameroff & Tuszynski (2004)**: "Quantum states in proteins and protein assemblies" *European Biophysics Journal*
3. **Fischer (2015)**: "Quantum cognition: The possibility of processing with nuclear spins in the brain" *Annals of Physics*
4. **Lyon (2015)**: "The cognitive cell: bacterial behavior reconsidered" *Frontiers in Microbiology*
5. **Adamatzky (2019)**: "A brief history of liquid computers" *Philosophical Transactions of the Royal Society B*

### Implementation Checklist

- [ ] Order anesthetics: lidocaine HCl, propofol, xenon gas
- [ ] Prepare stock solutions (100 mM lidocaine in H₂O)
- [ ] Calibrate syringe pumps for precise drug delivery
- [ ] Validate washout efficiency with dye tracking
- [ ] Set up RNA extraction protocol for HES 1 sampling
- [ ] Configure OLED display to show "DRUG PHASE" indicator
- [ ] Create analysis script `analyze_anesthetic_learning_curve.py`
- [ ] Run toxicity test: 0-1000 μM lidocaine, 24h exposure
- [ ] Test vehicle control (DMSO, saline only)
- [ ] Document all drug lot numbers and expiration dates

---

**End of Document**
