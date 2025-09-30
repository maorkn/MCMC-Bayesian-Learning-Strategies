import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path
import sys
from scipy.stats import entropy
from tqdm import tqdm
from collections import defaultdict

# --- Corrected Project Path Setup ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# --- Corrected Imports from the Refactored Codebase ---
from mba_vs_ba_sim.agents.blind import BlindAgent, GENOME_LENGTH
from mba_vs_ba_sim.agents.mba import MBAgent
from mba_vs_ba_sim.population.moran import MoranPopulation
from mba_vs_ba_sim.topology_FIXED import make_daily_from_perm_with_epsilon_FIXED, ticket_factory

# --- FIXED: Correct Fitness Table with Maximum Values ---
FITNESS_TABLE = np.array([
    #   P1   P2   P3
    [ 1.0, 0.1, 0.6],  # HES 0 (P1 max when prepared)
    [ 0.3, 0.8, 0.6],  # HES 1
    [ 0.3, 0.8, 0.6],  # HES 2
    [ 0.3, 0.8, 1.2],  # HES 3
    [ 1.0, 0.1, 0.6],  # HES 4 (P1 max when prepared)
], dtype=float)

# --- FIXED: Use penalty_size instead of gamma ---
PENALTY_SIZE = 0.7  # This gives 0.3 unprepared fitness (1.0 - 0.7 = 0.3)
STOCHASTICITY_LEVELS = [0.0, 0.05, 0.1, 0.15, 0.25, 0.5, 0.75, 1.0]
PERM_NORMAL = [0, 1, 2, 3, 4]
PERM_SHIFTED = [1, 3, 0, 4, 2]

# --- PROPERLY FIXED: Stress Test Logic with Correct Epsilon Implementation ---
def run_stress_test_logic(replicates, days, n_ba, n_mba, mu, seed, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    all_records = []
    seq_counts_ba_agg = [[] for _ in STOCHASTICITY_LEVELS]
    seq_counts_mba_agg = [[] for _ in STOCHASTICITY_LEVELS]
    rng_global = np.random.default_rng(seed)

    for eps_idx, eps in enumerate(tqdm(STOCHASTICITY_LEVELS, desc="Stress Test (Epsilon)")):
        fit_ba = np.full((replicates, days), np.nan)
        fit_mba = np.full((replicates, days), np.nan)
        
        for r in range(replicates):
            rng = np.random.default_rng(rng_global.integers(2**63))
            
            agents = [BlindAgent(rng.random(GENOME_LENGTH) < 0.5, FITNESS_TABLE) for _ in range(n_ba)] + \
                     [MBAgent(rng.random(GENOME_LENGTH) < 0.5, FITNESS_TABLE) for _ in range(n_mba)]
            pop = MoranPopulation(agents, mu=mu, rng=rng)

            # FIXED: Create ticket for canonical permutation
            ticket = ticket_factory(PERM_NORMAL)

            for day in range(days):
                # CRITICAL FIX: Use the corrected epsilon implementation that breaks cue-state correlation
                daily_hes_seq = make_daily_from_perm_with_epsilon_FIXED(PERM_NORMAL, rng, eps=eps)

                # FIXED: Use penalty_size and ticket system
                pop.run_daily_cycle(daily_hes_seq, ticket=ticket, penalty_size=PENALTY_SIZE)
                
                ba_agents = [a for a in pop.agents if isinstance(a, BlindAgent)]
                mba_agents = [a for a in pop.agents if isinstance(a, MBAgent)]

                # Record final fitness (cost is already applied by the engine)
                if ba_agents: fit_ba[r, day] = np.mean([a.fitness for a in ba_agents])
                if mba_agents: fit_mba[r, day] = np.mean([a.fitness for a in mba_agents])
                
                pop.moran_step()

            # Record final fitness values for this replicate
            if ba_agents:
                all_records.append({'epsilon': eps, 'agent_type': 'BA', 'fitness': np.mean(fit_ba[r, -50:])})
                sequences = ["".join(map(str, a.phenotype)) for a in ba_agents]
                unique, counts = np.unique(sequences, return_counts=True)
                seq_counts_ba_agg[eps_idx].append(dict(zip(unique, counts)))
            if mba_agents:
                all_records.append({'epsilon': eps, 'agent_type': 'MBA', 'fitness': np.mean(fit_mba[r, -50:])})
                sequences = ["".join(map(str, a.phenotype)) for a in mba_agents]
                unique, counts = np.unique(sequences, return_counts=True)
                seq_counts_mba_agg[eps_idx].append(dict(zip(unique, counts)))

    return pd.DataFrame(all_records), seq_counts_ba_agg, seq_counts_mba_agg

# --- PROPERLY FIXED: Lock-in Test Logic with Dramatic Environmental Change ---
def run_lock_in_logic(replicates, days_pre, days_post, n_ba, n_mba, mu, seed, outdir):
    outdir.mkdir(parents=True, exist_ok=True)
    total_days = days_pre + days_post
    all_records = []
    seq_counts_ba = [[] for _ in range(replicates)]
    seq_counts_mba = [[] for _ in range(replicates)]
    rng_global = np.random.default_rng(seed)

    for r in tqdm(range(replicates), desc="Lock-in Test"):
        rng = np.random.default_rng(rng_global.integers(2**63))
        agents = [BlindAgent(rng.random(GENOME_LENGTH) < 0.5, FITNESS_TABLE) for _ in range(n_ba)] + \
                 [MBAgent(rng.random(GENOME_LENGTH) < 0.5, FITNESS_TABLE) for _ in range(n_mba)]
        pop = MoranPopulation(agents, mu=mu, rng=rng)

        for day in range(total_days):
            # CRITICAL FIX: Use dramatically different permutations to create a real environmental shift
            if day < days_pre:
                perm = PERM_NORMAL  # [0,1,2,3,4] - canonical sequence
            else:
                perm = PERM_SHIFTED  # [1,3,0,4,2] - completely different sequence
            
            ticket = ticket_factory(perm)
            
            # Generate daily sequence with no epsilon noise for lock-in test
            # BUT use the corrected function to ensure proper implementation
            daily_hes_seq = make_daily_from_perm_with_epsilon_FIXED(perm, rng, eps=0.0)
            
            # FIXED: Use penalty_size and ticket system
            pop.run_daily_cycle(daily_hes_seq, ticket=ticket, penalty_size=PENALTY_SIZE)
            
            ba_agents = [a for a in pop.agents if isinstance(a, BlindAgent)]
            mba_agents = [a for a in pop.agents if isinstance(a, MBAgent)]

            phase = 'pre_shift' if day < days_pre else 'post_shift'
            if ba_agents:
                fitness = np.mean([a.fitness for a in ba_agents])
                all_records.append({'replicate': r, 'day': day, 'phase': phase, 'agent_type': 'BA', 'fitness': fitness})
                sequences = ["".join(map(str, a.phenotype)) for a in ba_agents]
                unique, counts = np.unique(sequences, return_counts=True)
                seq_counts_ba[r].append(dict(zip(unique, counts)))
            if mba_agents:
                fitness = np.mean([a.fitness for a in mba_agents])
                all_records.append({'replicate': r, 'day': day, 'phase': phase, 'agent_type': 'MBA', 'fitness': fitness})
                sequences = ["".join(map(str, a.phenotype)) for a in mba_agents]
                unique, counts = np.unique(sequences, return_counts=True)
                seq_counts_mba[r].append(dict(zip(unique, counts)))

            pop.moran_step()
            
    return None, None, None, seq_counts_ba, seq_counts_mba, all_records

# --- Re-integrated Plotting Helper ---
def plot_muller_stress_test(ax, counts_per_epsilon, title, n_top=9, show_xlabel=True, show_ylabel=True):
    if not any(any(rep for rep in eps_level) for eps_level in counts_per_epsilon):
        ax.text(0.5, 0.5, 'No data', ha='center', va='center'); return None, None

    global_counts = defaultdict(int)
    for eps_level_counts in counts_per_epsilon:
        for rep_counts in eps_level_counts:
            for seq, count in rep_counts.items():
                global_counts[seq] += count
    
    top_sequences = [item[0] for item in sorted(global_counts.items(), key=lambda x: x[1], reverse=True)[:n_top]]
    
    records = []
    for i, eps_level_counts in enumerate(counts_per_epsilon):
        record = {'epsilon': STOCHASTICITY_LEVELS[i]}
        total_agents = sum(sum(rep.values()) for rep in eps_level_counts)
        if total_agents == 0: continue
        
        other_count = total_agents
        proportions = {}
        for seq in top_sequences:
            count = sum(rep.get(seq, 0) for rep in eps_level_counts)
            proportions[seq] = count / total_agents
            other_count -= count
        proportions['Other'] = other_count / total_agents
        record.update(proportions)
        records.append(record)

    df = pd.DataFrame(records).set_index('epsilon')
    if df.empty:
        ax.text(0.5, 0.5, 'No data', ha='center', va='center'); return None, None

    labels = top_sequences + ['Other']
    colors = plt.get_cmap('tab10').colors if len(labels) <= 10 else plt.get_cmap('tab20').colors
    
    df[labels].plot(kind='bar', stacked=True, ax=ax, color=colors, width=0.8)
    
    if show_xlabel: ax.set_xlabel("Stochasticity (ε)")
    if show_ylabel: ax.set_ylabel("Proportion")
    ax.set_title(title)
    ax.legend().set_visible(False)
    ax.tick_params(axis='x', rotation=45)
    
    legend_handles = [plt.Rectangle((0,0),1,1, color=color) for color in colors[:len(labels)]]
    return legend_handles, labels

def plot_muller_sequences_on_ax(ax, counts_per_replicate, title, n_top=9, show_xlabel=True, show_ylabel=True):
    if not any(any(day_counts for day_counts in rep) for rep in counts_per_replicate):
        ax.text(0.5, 0.5, 'No data', ha='center', va='center'); return None, None
    global_counts = defaultdict(int)
    for rep_counts in counts_per_replicate:
        for day_counts in rep_counts:
            for seq, count in day_counts.items(): global_counts[seq] += count
    top_sequences = [item[0] for item in sorted(global_counts.items(), key=lambda x: x[1], reverse=True)[:n_top]]
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
        ax.text(0.5, 0.5, 'No data', ha='center', va='center'); return None, None
    df_mean = df.groupby('day').mean().drop(columns='replicate')
    total_per_day = df_mean.sum(axis=1)
    total_per_day[total_per_day == 0] = 1
    props_df = df_mean.div(total_per_day, axis=0)
    labels = top_sequences + ['Other']
    colors = plt.get_cmap('tab10').colors if len(labels) <= 10 else plt.get_cmap('tab20').colors
    handles = ax.stackplot(props_df.index, props_df.T, labels=labels, colors=colors)
    if show_xlabel: ax.set_xlabel("Day")
    if show_ylabel: ax.set_ylabel("Proportion")
    ax.set_title(title)
    ax.legend().set_visible(False)
    return handles, labels

# --- Main Execution ---
OUT_DIR = Path(__file__).resolve().parent
STRESS_DATA_DIR = OUT_DIR / 'stress_test_data'
LOCKIN_DATA_DIR = OUT_DIR / 'lock_in_data'
OUT_FILE = OUT_DIR / 'Figure3_StressAndLockIn_PROPERLY_FIXED.png'
STRESS_DATA_DIR.mkdir(exist_ok=True)
LOCKIN_DATA_DIR.mkdir(exist_ok=True)

print("Running PROPERLY FIXED simulations for Figure 3...")
print("Key fixes:")
print("- Using correct fitness table with max values for P1 at HES 0/4")
print("- Using penalty_size instead of gamma parameter")
print("- Using ticket system for proper preparation tracking")
print("- CRITICAL: Using corrected epsilon implementation that breaks cue-state correlation")
print("- CRITICAL: Using dramatically different permutations in lock-in test")
print("- Proper permutation switching in lock-in test")

stress_df, seq_counts_ba_stress, seq_counts_mba_stress = run_stress_test_logic(
    replicates=10, days=200, n_ba=50, n_mba=50, mu=1e-4, seed=0, outdir=STRESS_DATA_DIR
)
_, _, _, seq_counts_ba_lockin, seq_counts_mba_lockin, lockin_records = run_lock_in_logic(
    replicates=5, days_pre=300, days_post=100, n_ba=50, n_mba=50, mu=1e-4, seed=0, outdir=LOCKIN_DATA_DIR
)
print("Simulations complete.")

lockin_df = pd.DataFrame(lockin_records)

fig = plt.figure(figsize=(12, 10))
gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.2], wspace=0.3, hspace=0.35)
fig.suptitle('Figure 3: Environmental Stress & Genetic Lock-in Tests (PROPERLY FIXED)', fontsize=16, y=0.99)

# A. Stochasticity Stress Test
ax1 = fig.add_subplot(gs[0, 0])
stress_summary = stress_df.groupby(['epsilon', 'agent_type'])['fitness'].mean().unstack()
ax1.plot(stress_summary.index, stress_summary['BA'], 'o-', label="BA")
ax1.plot(stress_summary.index, stress_summary['MBA'], 'o-', label="MBA")
ax1.set_title('A. Fitness vs. Environmental Stochasticity (ε)')
ax1.set_xlabel('Stochasticity (ε)')
ax1.set_ylabel('Final Mean Fitness')
ax1.legend()
ax1.grid(True, alpha=0.3)

# B. Genetic Lock-in Test
ax2 = fig.add_subplot(gs[0, 1])
lockin_summary = lockin_df.groupby(['day', 'agent_type'])['fitness'].mean().unstack()
shift_day = lockin_df[lockin_df['phase'] == 'post_shift']['day'].min()
ax2.plot(lockin_summary.index, lockin_summary['BA'], label='BA')
ax2.plot(lockin_summary.index, lockin_summary['MBA'], label='MBA')
ax2.axvline(x=shift_day, color='r', linestyle='--', label='Environmental Shift')
ax2.set_title('B. Genetic Lock-in and Recovery')
ax2.set_xlabel('Day')
ax2.set_ylabel('Mean Fitness')
ax2.legend()
ax2.grid(True, alpha=0.3)

# C. Muller Plot for Stress Test (MBA)
ax3 = fig.add_subplot(gs[1, 0])
plot_muller_stress_test(ax3, seq_counts_mba_stress, title="C. MBA Genotype Proportion vs. Stochasticity")

# D. Muller Plot for Lock-in Test (MBA)
ax4 = fig.add_subplot(gs[1, 1])
handles, labels = plot_muller_sequences_on_ax(ax4, seq_counts_mba_lockin, title="D. MBA Genotype Evolution (Lock-in Test)", show_ylabel=False)

# Create a single legend for the Muller plots
if handles and labels:
    fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(0.5, 0.01), ncol=5, title="Dominant Genotypes", fontsize='small')

plt.tight_layout(rect=[0, 0.05, 1, 0.96])
plt.savefig(OUT_FILE, dpi=300, bbox_inches='tight')
print(f"Figure 3 PROPERLY FIXED saved to {OUT_FILE.resolve()}")
