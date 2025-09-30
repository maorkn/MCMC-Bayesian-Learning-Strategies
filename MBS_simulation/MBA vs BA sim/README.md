# MBA vs BA Simulation - Running Guide

This repository contains the simulation code for the manuscript "Beyond Diffusion: Bayesian Learning Strategies in Single-Cell Life". The code implements agent-based models comparing Markovian-Bayesian Agents (MBAs) with Blind Agents (BAs) across various environmental conditions.

## Quick Start

```bash
# Navigate to wrappers directory
cd "MBS_simulation/MBA vs BA sim/wrappers"

# Run baseline experiment
python vanilla.py
```

## Repository Structure

```
MBA vs BA sim/
├── mba_vs_ba_sim/          # Core simulation engine
│   ├── agents/             # Agent implementations (BA, MBA)
│   ├── env/                # Environment management
│   ├── population/         # Population dynamics (Moran process)
│   ├── core.py             # Core simulation logic
│   ├── preparatory_rule.py # Preparatory phenotype mechanism
│   └── topology_FIXED.py   # Environmental topology
├── wrappers/               # Experiment wrappers
│   ├── vanilla.py          # Baseline comparison
│   ├── stress.py           # Stochasticity testing
│   ├── topology.py         # Topology robustness
│   ├── grid_sweep.py       # Parameter sweep
│   ├── continuous_sweep.py # ML sampling
│   ├── lock_in.py          # Genetic lock-in
│   └── common.py           # Shared utilities
└── Fig_pub/                # Figure generation scripts
    ├── create_fig1.py
    ├── create_fig2_independent_runs_PREP_FIXED.py
    └── create_fig3_stress_and_lockin_PROPERLY_FIXED.py
```

## Requirements

### Python Dependencies
```bash
pip install numpy scipy pandas matplotlib seaborn
```

**Required packages:**
- `numpy` - Numerical computing
- `scipy` - Statistical functions
- `pandas` - Data manipulation
- `matplotlib` - Plotting
- `seaborn` - Statistical visualization

**Optional (for ML analysis):**
- `catboost` - Gradient boosting (for continuous_sweep analysis)
- `shap` - Feature importance analysis

### Python Version
- Python 3.7 or higher

## Running Experiments

All experiments are run via wrapper scripts in the `wrappers/` directory. Each wrapper orchestrates a specific experimental setup described in the manuscript.

### 1. Vanilla Experiment (Baseline)

**Purpose:** Validates basic MBA fitness advantage over BA in predictable environment.

```bash
cd wrappers
python vanilla.py
```

**Parameters:**
- Duration: 1000 days
- Replicates: 10
- Population size: 100 agents per type
- Environment: Deterministic (ε = 0.0)

**Output:** Creates `vanilla/` directory with:
- `mba/` - MBA-only population data
- `ba/` - BA-only population data
- `delta.csv` - Fitness comparison analysis
- `plots/` - Visualization figures

**Expected result:** MBA achieves ~31.8% higher fitness than BA.

---

### 2. Stress Test (Environmental Stochasticity)

**Purpose:** Identifies the stochasticity threshold where MBA advantage disappears.

```bash
cd wrappers
python stress.py
```

**Parameters:**
- Duration: 1000 days per epsilon level
- Replicates: 10 per level
- Epsilon values: [0.01, 0.1, 0.2, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

**Output:** Creates `stress/` directory with epsilon-specific subdirectories.

**Expected result:** MBA advantage decreases with increasing ε, crossing zero at ε ≈ 0.2.

---

### 3. Topology Scan (Robustness)

**Purpose:** Tests MBA advantage across all 120 permutations of the 5-stage environmental cycle.

```bash
cd wrappers
python topology.py
```

**Parameters:**
- Duration: 600 days per permutation
- Replicates: 5
- Permutations: All 120 possible orderings of HES 0-4

**Output:** Creates `topology/` directory with permutation-specific results.

**Expected result:** MBA maintains positive advantage across all topologies (no topology-dependent failure).

---

### 4. Grid Sweep (Parameter Space)

**Purpose:** Multi-dimensional parameter exploration for heatmap analysis.

```bash
cd wrappers
python grid_sweep.py
```

**Parameters:**
- Epsilon: [0.0, 0.1, 0.2, 0.25]
- Learning rate: [0.1, 0.3, 0.5, 0.7]
- Cost multiplier: [0.5, 1.0, 1.5, 2.0]
- Penalty: [0.2, 0.5, 0.7, 0.8]
- Total combinations: 320

**Output:** Creates `grid_sweep/` directory with `grid_summary.csv` containing all parameter combinations and results.

**Runtime:** Can take several hours. Consider using parallelization (see Advanced Usage).

---

### 5. Continuous Sweep (ML Training Data)

**Purpose:** High-density random sampling for CatBoost/SHAP analysis.

```bash
cd wrappers
python continuous_sweep.py
```

**Parameters:**
- Samples: 5000+ randomized parameter combinations
- Continuous ranges for all parameters
- Random permutation selection

**Output:** Creates `continuous_sweep/` directory with `continuous_summary.csv`.

**Note:** This generates training data for the machine learning analysis in the manuscript.

---

### 6. Lock-in Experiment (Environmental Shift)

**Purpose:** Tests response to abrupt, permanent environmental change.

```bash
cd wrappers
python lock_in.py
```

**Parameters:**
- Initial adaptation: 300 days
- Post-shift observation: 200+ days
- Shift type: Permanent permutation of environmental cycle

**Output:** Creates `lock_in/` directory with pre/post-shift data.

**Expected result:** MBA shows initial fitness collapse followed by rapid recovery; BA remains static.

---


## Output Format

### Standard Output Structure

Each wrapper creates a structured output directory:

```
wrapper_name/
├── manifest.json           # Experiment metadata
├── logs/                   # Execution logs
├── plots/                  # Visualization figures
├── mba/                    # MBA population data (if applicable)
│   └── rep_*.csv          # Per-replicate CSV files
├── ba/                     # BA population data (if applicable)
│   └── rep_*.csv
└── delta.csv              # MBA-BA comparison (if applicable)
```

### CSV Data Format

**Agent-level records** (per day, per agent):
```csv
rep_id,day,agent_id,agent_type,phenotype_sequence,daily_fitness,plasticity_cost,genome_hash,age,learning_events
```

**Population-level metrics:**
```csv
rep_id,day,agent_type,mean_fitness,fitness_variance,entropy,num_unique_genotypes
```

---

## Advanced Usage

### Parallel Execution

For faster grid sweeps, use multiple cores:

```python
# Edit grid_sweep.py
# Change: n_jobs = 1
# To: n_jobs = 4  # Use 4 CPU cores
```

### Custom Parameters

Modify parameters in individual wrapper scripts:

```python
# Example: Longer simulation in vanilla.py
config = {
    'n_days': 2000,        # Increase from 1000
    'n_replicates': 20,    # Increase from 10
    'n_mba': 100,
    'n_ba': 100,
    # ... other parameters
}
```

### Resuming Interrupted Runs

Most wrappers support incremental execution:

```bash
# If continuous_sweep.py is interrupted, rerun:
python continuous_sweep.py
# It will skip completed experiments and continue
```

---

## Troubleshooting

### Common Issues

**1. Import errors:**
```bash
ModuleNotFoundError: No module named 'mba_vs_ba_sim'
```
**Solution:** Ensure you're running from the correct directory or add parent to PYTHONPATH:
```bash
export PYTHONPATH="${PYTHONPATH}:/path/to/MBA vs BA sim"
```

**2. Memory issues on large sweeps:**
```python
# Reduce memory usage by processing in smaller batches
# In grid_sweep.py, reduce chunk_size parameter
```

**3. Slow execution:**
- Use parallel execution (set `n_jobs > 1`)
- Reduce `n_days` or `n_replicates` for testing
- Use smaller parameter grids

**4. Missing output directories:**
```bash
# Wrappers create directories automatically
# If issues occur, manually create:
mkdir -p wrappers/vanilla wrappers/stress wrappers/topology
```

---

## Default Parameters

All experiments use these core parameters unless specified:

| Parameter | Value | Description |
|-----------|-------|-------------|
| Mutation rate (μ) | 10⁻⁴ | Per-bit mutation probability |
| Genome length | 452 bits | Boolean genome encoding |
| Population size | 100 | Agents per population |
| Learning rate (η) | 0.3 | MBA learning rate |
| Cost multiplier | 1.0 | Plasticity cost scaling |
| Penalty (γ) | 0.7 | Preparation penalty |
| Base fitness | See Table 1 | HES-dependent fitness values |

---

## Validation

To verify installation and setup:

```bash
# Quick test (< 1 minute)
cd wrappers
python vanilla.py  # Should complete without errors

# Check output
ls -la vanilla/
# Should show: mba/, ba/, delta.csv, plots/, logs/

# Verify delta
head vanilla/delta.csv
# Should show positive delta values
```

---

## Citation

If you use this code, please cite:

```
Knafo, M., Casacuberta, E., Solé, R., & Ruiz-Trillo, I. (2025). 
Beyond Diffusion: Bayesian Learning Strategies in Single-Cell Life. 
[Manuscript in preparation]
```

---

## Support

- **Detailed cleanup info:** See `CLEANED_REPOSITORY_SUMMARY.md`
- **Manuscript:** `../../Manuscript/Draft_18_09_25.tex`
- **Issues:** Check execution logs in `wrappers/*/logs/`

---

## File Permissions

Ensure scripts are executable:
```bash
chmod +x wrappers/*.py
chmod +x Fig_pub/*.py
```

---

## Reproducibility

All experiments use deterministic seeding for reproducibility:
- Random seeds are explicitly managed in each wrapper
- Results should be identical across runs with same parameters
- Small variations (<1%) may occur due to floating-point arithmetic

---

**Last updated:** September 30, 2025  
**Repository version:** Post-cleanup (essential files only)  
**Compatible with:** Python 3.7+, NumPy 1.19+, Matplotlib 3.3+
