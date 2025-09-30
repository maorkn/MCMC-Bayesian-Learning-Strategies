from __future__ import annotations

import numpy as np
from sklearn.metrics import mutual_info_score

from .agents.blind import BlindAgent
from .agents.mba import MBAgent
from .env.environment import Environment
from .population.moran import MoranPopulation

def build_fitness_table(penalty_size: float = 0.7, gamma: float = None) -> np.ndarray:
    """
    Build the fitness table with maximum achievable values for penalty model.
    
    Updated semantics for penalty model:
      - P1 is 1.0 at HES 0,4 (prepared maximum); penalty applied at runtime for unprepared
      - P2 is 0.8 at HES 1,2,3; 0.1 at HES 0,4
      - P3 is 1.2 at HES 3; 0.6 elsewhere
    
    Args:
        penalty_size: Penalty applied to unprepared P1 at HES 0/4 (for reference only)
        gamma: Backward compatibility parameter (ignored)
    
    Returns:
        Fitness table with maximum achievable values
    """
    # Ignore gamma parameter for backward compatibility
    base_fitness = np.array([
        #   P1   P2   P3
        [ 1.0, 0.1, 0.6],  # HES 0 (P1 max when prepared)
        [ 0.3, 0.8, 0.6],  # HES 1
        [ 0.3, 0.8, 0.6],  # HES 2
        [ 0.3, 0.8, 1.2],  # HES 3
        [ 1.0, 0.1, 0.6],  # HES 4 (P1 max when prepared)
    ], dtype=float)
    return base_fitness

def run_cell(eps: float, rho: float, gamma: float, seed: int, T: int = 1000, N0: int = 1000, mu: float = 1e-4, cost_off: bool = False, good_ba_seed: bool = False, cost_multiplier: float = 1.0) -> dict:
    """
    Runs a single simulation for a given parameter cell.
    """
    rng = np.random.default_rng(seed)
    
    # 1. Generate environment
    env = Environment(T, eps, rho, rng)
    hes_seq = env.hes_seq
    
    # 2. Compute mutual information
    mi = mutual_info_score(hes_seq[:, 1][:-1], hes_seq[:, 0][1:])
    
    # 3. Build fitness table
    fit_tbl = build_fitness_table(gamma)
    
    # 4. Initialize population
    genomes = [rng.choice([True, False], size=452) for _ in range(N0)]
    if good_ba_seed:
        # P2 is optimal for HES=2
        p2_vec = np.concatenate([np.ones(32, dtype=bool), np.zeros(32, dtype=bool)])
        for i in range(N0 // 2, N0):
            genomes[i][64:128] = p2_vec

    agents = [MBAgent(genomes[i], fit_tbl) if i < N0 / 2 else BlindAgent(genomes[i], fit_tbl) for i in range(N0)]
    if cost_off:
        for agent in agents:
            if isinstance(agent, MBAgent):
                agent.plasticity_cost = lambda: 0.0
    if cost_multiplier != 1.0:
        for agent in agents:
            if isinstance(agent, MBAgent):
                original_cost = agent.plasticity_cost
                agent.plasticity_cost = lambda: original_cost() * cost_multiplier
    pop = MoranPopulation(agents, mu, rng)
    
    # 5. Run simulation
    mba_pop_size = []
    ba_pop_size = []
    mba_fitness_over_time = []
    ba_fitness_over_time = []
    for day in range(T):
        daily_hes_seq = hes_seq[day*5:(day+1)*5]
        pop.run_daily_cycle(daily_hes_seq)
        pop.moran_step()
        
        mba_agents = [a for a in pop.agents if isinstance(a, MBAgent)]
        ba_agents = [a for a in pop.agents if isinstance(a, BlindAgent)]
        
        mba_pop_size.append(len(mba_agents))
        ba_pop_size.append(len(ba_agents))
        
        mba_fitness_over_time.append(sum(a.fitness for a in mba_agents))
        ba_fitness_over_time.append(sum(a.fitness for a in ba_agents))
        
    # 6. Calculate population-normalized end-score
    mba_score = sum(a.fitness for a in pop.agents if isinstance(a, MBAgent)) / (N0 / 2)
    ba_score = sum(a.fitness for a in pop.agents if isinstance(a, BlindAgent)) / (N0 / 2)
    
    delta_score = mba_score / ba_score if ba_score > 0 else np.inf
    
    final_ba_population = ba_pop_size[-1]
    final_mba_population = mba_pop_size[-1]
    
    # Time-integrated scores
    auc_mba = np.sum(mba_fitness_over_time) / (N0 / 2)
    auc_ba = np.sum(ba_fitness_over_time) / (N0 / 2)
    
    return {
        "eps": eps,
        "rho": rho,
        "gamma": gamma,
        "mi": mi,
        "delta_score": delta_score,
        "mba_score": mba_score,
        "ba_score": ba_score,
        "final_ba_population": final_ba_population,
        "final_mba_population": final_mba_population,
        "auc_mba": auc_mba,
        "auc_ba": auc_ba,
        "seed": seed,
        "T": T,
        "N0": N0,
        "hes_seq": hes_seq.tolist(),  # Convert to list for JSON serialization
        "mba_pop_size": mba_pop_size,
        "ba_pop_size": ba_pop_size,
    }

# HES temperatures from simulation_explained.md
HES_TEMPS = np.array([-0.34, 1.38, -0.34, 0.80, -1.49])

def run_topology_scan(perm: list, gamma: float, seed: int, T: int = 1000, N: int = 100, mu: float = 1e-4) -> dict:
    """
    Runs a simulation with a permuted HES order for both MBA and BA populations.
    """
    # --- Shared Setup ---
    fit_tbl = build_fitness_table(gamma)
    
    # --- MBA Population ---
    rng_mba = np.random.default_rng((seed, 0))
    mba_genomes = [rng_mba.choice([True, False], size=452) for _ in range(N)]
    mba_agents = [MBAgent(g, fit_tbl) for g in mba_genomes]
    mba_pop = MoranPopulation(mba_agents, mu, rng_mba)

    # --- BA Population ---
    rng_ba = np.random.default_rng((seed, 1))
    ba_genomes = [rng_ba.choice([True, False], size=452) for _ in range(N)]
    ba_agents = [BlindAgent(g, fit_tbl) for g in ba_genomes]
    ba_pop = MoranPopulation(ba_agents, mu, rng_ba)

    # --- Bonus Rule Setup ---
    perm_arr = np.array(perm)
    prep_slot = np.where(perm_arr == 3)[0][0]
    unlock_slots = {(prep_slot + 1) % 5, (prep_slot + 2) % 5}

    # --- Simulation Loop ---
    for day in range(T):
        for slot in range(5):
            current_state = perm_arr[slot]
            prev_state = perm_arr[(slot - 1 + 5) % 5]
            
            # Calculate noisy temperature cue
            delta_T = HES_TEMPS[current_state] - HES_TEMPS[prev_state]
            # Assuming a fixed noise level for the cue, as it's not specified in the doc
            # Using a small noise value, e.g., from a normal distribution
            noisy_delta_T = delta_T + rng_mba.normal(0, 0.1) 

            # Determine if the bonus is active for this slot
            is_unlock_slot = slot in unlock_slots

            # Step MBA population
            for agent in mba_pop.agents:
                agent.step(current_state, noisy_delta_T, is_unlock_slot, gamma)
            
            # Step BA population
            for agent in ba_pop.agents:
                agent.step(current_state, noisy_delta_T, is_unlock_slot, gamma)

        mba_pop.moran_step()
        ba_pop.moran_step()

    # --- Calculate final metrics ---
    final_mba_fitness = np.mean([a.fitness for a in mba_pop.agents])
    final_ba_fitness = np.mean([a.fitness for a in ba_pop.agents])
    delta_fitness = final_mba_fitness - final_ba_fitness

    return {
        "perm_id": seed,
        "hamming": sum(a != b for a, b in zip(perm, [0, 1, 2, 3, 4])),
        "delta_fit": delta_fitness,
        "gamma": gamma
    }
