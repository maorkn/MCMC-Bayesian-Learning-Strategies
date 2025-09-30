import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import numpy as np
import sys
from scipy.stats import entropy
from tqdm import tqdm
from collections import defaultdict

"""
Figure 2 (Independent Runs) — Spec-aligned gating and cost handling

Changes vs original:
- Fitness table uses unprepared/base values (P1=0.3 everywhere; P3@HES3=1.2; P2=0.8 at HES 1-3 else 0.1).
- Prepared bonus is applied at runtime by the engine with gamma=10/3 (so prepared P1@HES{0,4} hits 1.0 with clamping).
- Do NOT subtract MBA plasticity cost again outside the engine (the engine already accounts for cost per sub-step).
- Produces the same plot panels and saves to Figure2_IndependentRuns_FIXED.png.
"""

# --- Corrected Project Path Setup ---
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# --- Imports from the refactored codebase ---
from mba_vs_ba_sim.agents.blind import BlindAgent, GENOME_LENGTH
from mba_vs_ba_sim.agents.mba import MBAgent
from mba_vs_ba_sim.population.moran import MoranPopulation
from mba_vs_ba_sim.topology import make_daily_from_perm_with_epsilon

# --- Spec-aligned base (unprepared) fitness table ---
# Columns: [P1, P2, P3], Rows: HES 0..4
FITNESS_TABLE = np.array(
    [
        [0.3, 0.1, 0.6],  # HES 0
        [0.3, 0.8, 0.6],  # HES 1
        [0.3, 0.8, 0.6],  # HES 2
        [0.3, 0.8, 1.2],  # HES 3
        [0.3, 0.1, 0.6],  # HES 4
    ],
    dtype=float,
)

GAMMA_SPEC = 10.0 / 3.0  # multiplicative prepared bonus; min(1.0, gamma * 0.3) = 1.0

def simulate_mixed(
    *,
    replicates: int,
    days: int,
    n_ba: int,
    n_mba: int,
    mu: float = 1e-4,
    stochasticity: float = 0.0,
    seed: int = 0,
):
    rng_global = np.random.default_rng(seed)
    fit_ba = np.full((replicates, days), np.nan)
    fit_mba = np.full((replicates, days), np.nan)
    cost_mba = np.full((replicates, days), np.nan)
    entropy_ba = np.full((replicates, days), np.nan)
    entropy_mba = np.full((replicates, days), np.nan)
    seq_counts_ba = [[] for _ in range(replicates)]
    seq_counts_mba = [[] for _ in range(replicates)]
    all_records = []

    # Canonical 5-stage permutation
    CANONICAL_PERM = [0, 1, 2, 3, 4]

    for r in tqdm(range(replicates), desc="Replicates", unit="rep"):
        rng = np.random.default_rng(rng_global.integers(2**63))
        
        agents = []
        for _ in range(n_ba):
            genome = rng.random(GENOME_LENGTH) < 0.5
            agents.append(BlindAgent(genome, FITNESS_TABLE))
        for _ in range(n_mba):
            genome = rng.random(GENOME_LENGTH) < 0.5
            agents.append(MBAgent(genome, FITNESS_TABLE))
        pop = MoranPopulation(agents, mu=mu, rng=rng)

        for day in range(days):
            # Build the day's cycle with noisy temperature observations
            daily_cycle = make_daily_from_perm_with_epsilon(CANONICAL_PERM, rng, eps=stochasticity)

            # Run daily cycle with prepared bonus enabled at runtime (gamma=10/3)
            # Pass cost_multiplier=0 to prevent the engine from applying cost
            pop.run_daily_cycle(daily_cycle, gamma=GAMMA_SPEC, cost_multiplier=0)

            # Collect metrics and manually apply cost before selection
            ba_agents = [a for a in pop.agents if isinstance(a, BlindAgent)]
            mba_agents = [a for a in pop.agents if isinstance(a, MBAgent)]
            
            # Manually subtract plasticity cost for MBAs
            if mba_agents:
                for agent in mba_agents:
                    agent.fitness = max(0, agent.fitness - agent.plasticity_cost())

            if ba_agents:
                fit_ba[r, day] = np.mean([a.fitness for a in ba_agents])
                sequences = ["".join(map(str, a.phenotype)) for a in ba_agents]
                _, counts = np.unique(sequences, return_counts=True)
                entropy_ba[r, day] = entropy(counts, base=2)
                seq_counts_ba[r].append(dict(zip(*np.unique(sequences, return_counts=True))))

            if mba_agents:
                fit_mba[r, day] = np.mean([a.fitness for a in mba_agents])
                cost_mba[r, day] = np.mean([a.plasticity_cost() for a in mba_agents])
                sequences = ["".join(map(str, a.phenotype)) for a in mba_agents]
                _, counts = np.unique(sequences, return_counts=True)
                entropy_mba[r, day] = entropy(counts, base=2)
                seq_counts_mba[r].append(dict(zip(*np.unique(sequences, return_counts=True))))
            
            pop.moran_step()

    records_df = pd.DataFrame(all_records)
    return fit_ba, fit_mba, cost_mba, seq_counts_ba, seq_counts_mba, entropy_ba, entropy_mba, records_df

# --- Plotting helper (unchanged) ---
def plot_muller_sequences_on_ax(
    ax,
    counts_per_replicate: list[list[dict[str, int]]],
    title: str,
    n_top: int = 9,
    show_xlabel: bool = True,
    show_ylabel: bool = True,
):
    if not any(any(day_counts for day_counts in rep) for rep in counts_per_replicate):
        ax.text(0.5, 0.5, 'No data', ha='center', va='center')
        return

    global_counts = defaultdict(int)
    for rep_counts in counts_per_replicate:
        for day_counts in rep_counts:
            for seq, count in day_counts.items():
                global_counts[seq] += count
    
    top_sequences = [
        item[0] for item in sorted(global_counts.items(), key=lambda x: x[1], reverse=True)[:n_top]
    ]

    records = []
    for r, rep_counts in enumerate(counts_per_replicate):
        for d, day_counts in enumerate(rep_counts):
            total_agents = sum(day_counts.values())
            if total_agents == 0: continue
            record = {'replicate': r, 'day': d}
            other_count = total_agents
            for seq in top_sequences:
                count = day_counts.get(seq, 0)
                record[seq] = count
                other_count -= count
            record['Other'] = other_count
            records.append(record)

    df = pd.DataFrame(records)
    if df.empty:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center')
        return

    df_mean = df.groupby('day').mean().drop(columns='replicate')
    total_per_day = df_mean.sum(axis=1)
    total_per_day[total_per_day == 0] = 1
    props_df = df_mean.div(total_per_day, axis=0)
    
    labels = top_sequences + ['Other']
    colors = plt.get_cmap('tab10').colors if len(labels) <= 10 else plt.get_cmap('tab20').colors
    
    ax.stackplot(props_df.index, props_df.T, labels=labels, colors=colors)

    if show_xlabel: ax.set_xlabel("Day")
    if show_ylabel: ax.set_ylabel("Proportion")
    ax.set_title(title)

# --- Configuration ---
OUT_FILE = Path(__file__).resolve().parent.parent / 'Figure2_IndependentRuns_FIXED.png'
SIM_PARAMS_BASE = {
    "replicates": 10,
    "days": 500,
}

# --- Run Simulations to Get Fresh Data ---
print("Running BA-only simulation (spec-aligned gating)...")
ba_fit, _, _, seq_counts_ba, _, ba_entropy, _, _ = simulate_mixed(
    n_ba=100, n_mba=0, **SIM_PARAMS_BASE
)

print("Running MBA-only simulation (spec-aligned gating)...")
_, mba_fit, mba_cost, _, seq_counts_mba, _, mba_entropy, _ = simulate_mixed(
    n_ba=0, n_mba=100, **SIM_PARAMS_BASE
)
print("Simulations complete.")

# --- Process Data for Plotting ---
def process_metric(data):
    mean = np.nanmean(data, axis=0)
    sem = np.nanstd(data, axis=0) / np.sqrt(np.sum(~np.isnan(data), axis=0))
    return mean, sem

days = np.arange(SIM_PARAMS_BASE['days'])
ba_fitness_mean, ba_fitness_sem = process_metric(ba_fit)
mba_fitness_mean, mba_fitness_sem = process_metric(mba_fit)

ba_entropy_mean, ba_entropy_sem = process_metric(ba_entropy)
mba_entropy_mean, mba_entropy_sem = process_metric(mba_entropy)

mba_cost_mean, mba_cost_sem = process_metric(mba_cost)

# --- Plotting ---
fig = plt.figure(figsize=(12, 8))
gs_main = fig.add_gridspec(2, 2, height_ratios=[1, 1.2], hspace=0.1, wspace=0.25)

# Fitness Plot
ax1 = fig.add_subplot(gs_main[0, 0])
ax1.plot(days, ba_fitness_mean, color='blue', label='BA (Independent)')
ax1.fill_between(days, ba_fitness_mean - ba_fitness_sem, ba_fitness_mean + ba_fitness_sem, color='blue', alpha=0.2)
ax1.plot(days, mba_fitness_mean, color='orange', label='MBA (Independent)')
ax1.fill_between(days, mba_fitness_mean - mba_fitness_sem, mba_fitness_mean + mba_fitness_sem, color='orange', alpha=0.2)
ax1.set_title('A. Mean Fitness ± SEM (Independent Runs)')
ax1.set_ylabel('Fitness')
ax1.legend()
ax1.grid(True, alpha=0.3)
ax1.tick_params(axis='x', labelbottom=False)

# Entropy Plot
ax2 = fig.add_subplot(gs_main[0, 1])
ax2.plot(days, ba_entropy_mean, color='blue', label='BA')
ax2.fill_between(days, ba_entropy_mean - ba_entropy_sem, ba_entropy_mean + ba_entropy_sem, color='blue', alpha=0.2)
ax2.plot(days, mba_entropy_mean, color='orange', label='MBA')
ax2.fill_between(days, mba_entropy_mean - mba_entropy_sem, mba_entropy_mean + mba_entropy_sem, color='orange', alpha=0.2)
ax2.set_title('B. Population Entropy ± SEM')
ax2.set_ylabel('Entropy (bits)')
ax2.legend()
ax2.grid(True, alpha=0.3)
ax2.tick_params(axis='x', labelbottom=False)

# Cost Plot
ax3 = fig.add_subplot(gs_main[1, 0], sharex=ax1)
ax3.plot(days, mba_cost_mean, color='orange', label='MBA Plasticity Cost')
ax3.fill_between(days, mba_cost_mean - mba_cost_sem, mba_cost_mean + mba_cost_sem, color='orange', alpha=0.2)
ax3.set_title('C. Mean Plasticity Cost ± SEM')
ax3.set_xlabel('Day')
ax3.set_ylabel('Cost')
ax3.legend()
ax3.grid(True, alpha=0.3)

# Muller Plots
gs_nested = gs_main[1, 1].subgridspec(2, 1, hspace=0.0)
ax4_top = fig.add_subplot(gs_nested[0], sharex=ax1)
ax4_bottom = fig.add_subplot(gs_nested[1], sharex=ax1)

plot_muller_sequences_on_ax(ax4_top, seq_counts_ba, title='D. Dominant Genotype Evolution', show_xlabel=False, show_ylabel=False)
ax4_top.set_ylabel('BA', rotation=0, size='large', ha='right', va='center', labelpad=10)
ax4_top.tick_params(axis='x', labelbottom=False)
ax4_top.set_yticks([0, 0.5])
ax4_top.set_yticklabels(['0.0', '0.5'])

plot_muller_sequences_on_ax(ax4_bottom, seq_counts_mba, title='', show_xlabel=True, show_ylabel=False)
ax4_bottom.set_ylabel('MBA', rotation=0, size='large', ha='right', va='center', labelpad=10)
ax4_bottom.set_yticks([0, 0.5])
ax4_bottom.set_yticklabels(['0.0', '0.5'])

fig.suptitle('Figure 2: Independent BA vs. MBA Runs (Spec-Aligned Gating)', fontsize=16, y=0.99)
fig.tight_layout(rect=[0, 0, 1, 0.96])
plt.savefig(OUT_FILE, dpi=300)
print(f"Figure saved to {OUT_FILE.resolve()}")
