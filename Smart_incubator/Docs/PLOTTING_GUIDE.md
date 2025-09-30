# Smart Incubator Data Analysis Guide

## Overview

After completing your comprehensive analysis of your Smart Incubator codebase, I've created a powerful data analysis and plotting script that understands your specific data structure and experimental protocols.

## Your System Architecture (Summary)

Your Smart Incubator is a **sophisticated biological experimentation platform** featuring:

### Core Components:
- **PID Temperature Control**: Precise dual-actuator system (PTC heater + TEC cooler)
- **Multi-Modal Stimuli**: LED and vibration with configurable timing (20s ON, 60s OFF)
- **Advanced Data Logging**: JSON-based with SHA-256 checksums and manifests
- **Correlation-Based Protocols**: 4 different stimulus-heat shock timing relationships
- **Noise-Filtered Sensing**: Median filtering and validation for temperature readings
- **Failsafe Systems**: Temperature limits, sensor recovery, emergency shutdown

### Data Structure Understanding:
- **Experiments**: Stored in `/sd/data/[DDMMYYYY_correlation]/`
- **Snapshots**: Every 10 seconds with temp, setpoint, power, US activity, phase
- **Cycles**: 200-400 minute random duration with basal→heat shock phases
- **Correlation Modes**:
  - **0**: Random independent timing
  - **1**: US precedes heat shock (DEFAULT)
  - **2**: US follows heat shock  
  - **3**: Testing mode (early stimuli)

## Installation

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements_plotting.txt
   ```

2. **Copy your SD card data** to your computer:
   ```bash
   # Example: copy from SD card to local directory
   cp -r /Volumes/INCUBATOR/data ./incubator_data/
   ```

## Usage Examples

### Basic Usage (Auto-select most recent experiment):
```bash
python plot_experiment_data.py ./incubator_data/
```

### Analyze specific experiment:
```bash
python plot_experiment_data.py ./incubator_data/ --experiment 9298_1
```

### Analyze specific cycles only:
```bash
python plot_experiment_data.py ./incubator_data/ --experiment 9298_1 --cycles 1-5
```

### Generate comprehensive report:
```bash
python plot_experiment_data.py ./incubator_data/ --experiment 9298_1 --report --output ./analysis_results/
```

## Plot Types Generated

### 1. **Temperature Overview**
**What it shows**: Complete thermal profile with correlation to baseline and heat shock
- **Top panel**: Temperature vs time with basal (23°C) and heat shock (32°C) reference lines
- **Middle panel**: Power output (heating/cooling) and US stimulus activity
- **Bottom panel**: Experiment phases (basal vs heat shock)

**Key Insights**:
- Temperature regulation precision
- Heat shock timing and effectiveness
- US stimulus patterns in relation to thermal phases

### 2. **Correlation Analysis** 
**What it shows**: Statistical relationship between temperature, US activity, and baseline
- **Temperature deviation histograms**: US active vs inactive periods
- **Scatter plot**: Temperature over time colored by US activity
- **Power distribution**: Heating vs cooling effort analysis
- **Phase analysis**: Average temperatures by experiment phase and US state

**Key Insights**:
- Quantitative effect of US stimulation on temperature
- Control system performance during different phases
- Statistical significance of stimulus-temperature correlations

### 3. **Cycle Comparison**
**What it shows**: Side-by-side comparison of multiple experimental cycles
- **Temperature profiles**: Overlay of all cycle temperature traces
- **US activity patterns**: Stacked visualization of stimulus timing

**Key Insights**:
- Experimental consistency across cycles
- Variation in thermal responses
- US timing pattern reliability

## Data Analysis Features

### Automatic Discovery
The script automatically:
- Finds all experiments in your data directory
- Counts cycles per experiment
- Loads experimental parameters from meta.json files

### Statistical Analysis
Provides quantitative metrics:
- **Temperature Statistics**: Mean temps during US active/inactive periods
- **Correlation Strength**: Temperature difference with/without US
- **Control Performance**: Power distribution, regulation precision
- **Experimental Coverage**: Data point counts, error rates

### Flexible Data Handling
- **Missing Data**: Gracefully handles incomplete datasets
- **Time Alignment**: Works with both elapsed_minutes and timestamp data
- **Multi-Cycle**: Supports single cycle or cycle range analysis
- **Export Options**: High-resolution PNG output for publications

## Understanding Your Experimental Data

### Temperature Fields:
- **`temp`**: Actual measured temperature (°C)
- **`set_temp`**: Target temperature (basal or heat shock)
- **`temp_deviation_basal`**: Difference from basal temperature

### Control Fields:
- **`power`**: PID output (-100 to +100%, negative = cooling)
- **`mode`**: "Heating", "Cooling", or "Idle"
- **`phase`**: "basal" or "heat_shock"

### Stimulus Fields:
- **`us_active`**: 1 if US active, 0 if inactive
- **`us_type`**: "LED", "VIB", or "BOTH"

### Timing Fields:
- **`elapsed_minutes`**: Time from cycle start
- **`cycle_length`**: Total cycle duration (200-400 min)

## Correlation Mode Analysis

Your system supports 4 correlation modes that define stimulus-heat shock timing:

### Mode 0: Random Independent
- US and heat shock occur at random times
- Tests independence of thermal and stimulus effects

### Mode 1: US Precedes Heat Shock (DEFAULT)
- US activates just before heat shock at cycle end
- Tests preparatory/priming effects

### Mode 2: US Follows Heat Shock  
- US activates immediately after heat shock
- Tests recovery/response modulation effects

### Mode 3: Testing Mode
- Early timing (heat at 1min, US at 0.5min)
- For system validation and rapid testing

## Troubleshooting

### Common Issues:

1. **"No experiments found"**
   - Check data directory path
   - Ensure meta.json files exist in experiment directories

2. **"Experiment not found"**  
   - List available experiments first: `python plot_experiment_data.py ./data/ --help`
   - Use exact experiment ID format: `DDMMYYYY_correlation`

3. **Missing data fields**
   - Script gracefully handles missing fields
   - Check your JSON data structure matches expected format

4. **Empty plots**
   - Ensure cycle data files exist (cycle_N_TIMESTAMP.json)
   - Check that cycle range matches available data

### Data Validation:
Before running analysis, you can validate your data structure:
```bash
# Check experiment structure
ls -la ./incubator_data/9298_1/
# Should show: meta.json, manifest.json, cycle_*.json files

# Verify JSON format
python -m json.tool ./incubator_data/9298_1/meta.json
```

## Advanced Usage

### Custom Analysis Scripts
The `IncubatorDataAnalyzer` class can be imported for custom analysis:

```python
from plot_experiment_data import IncubatorDataAnalyzer

# Initialize analyzer
analyzer = IncubatorDataAnalyzer('./incubator_data')

# Load experiment
analyzer.load_experiment('9298_1')

# Get raw cycle data for custom analysis
cycle_data, meta = analyzer.load_cycle_data('9298_1', '1-3')

# Your custom analysis here...
```

### Publication-Ready Plots
For publication-quality figures:
- Use `--report` flag for comprehensive analysis
- Plots saved as 300 DPI PNG files
- Professional styling with seaborn themes
- Clear legends and axis labels

### Batch Analysis
To analyze multiple experiments:
```bash
# Create analysis script for all experiments
for exp in $(ls incubator_data/); do
    python plot_experiment_data.py ./incubator_data/ --experiment $exp --report --output ./results/$exp/
done
```

## Scientific Interpretation

### Expected Results by Correlation Mode:

**Mode 1 (US Precedes Heat Shock)**:
- Should show US activation just before temperature ramp
- Look for potential pre-conditioning effects
- Temperature may show different kinetics compared to no-US periods

**Mode 0 (Random)**:
- Independent US and heat shock timing
- Provides baseline for comparison
- Tests system performance under various conditions

**Modes 2 & 3**:
- Different temporal relationships for mechanistic studies
- Compare response patterns across correlation modes

### Key Metrics to Look For:
1. **Temperature Regulation Precision**: Standard deviation during basal periods
2. **Heat Shock Effectiveness**: Rate and magnitude of temperature increase
3. **US Correlation Effects**: Statistical difference in temperature when US is active
4. **System Stability**: Consistent performance across multiple cycles
5. **Control Effort**: Power distribution patterns during different phases

This analysis framework will help you understand the biological and technical aspects of your Smart Incubator experiments, providing both visual insights and quantitative metrics for scientific interpretation.
