from __future__ import annotations
import itertools, math
from typing import Dict, List, Tuple
import numpy as np
from scipy.stats import entropy

from .agents.blind import BlindAgent, GENOME_LENGTH
from .agents.mba import MBAgent
from .population.moran import MoranPopulation
from .core import HES_TEMPS

CANON = [0,1,2,3,4]

def make_daily_from_perm_with_epsilon_FIXED(perm, rng, eps: float):
    """
    FIXED VERSION: Build one-day sequence following permutation `perm` over 5 substeps.
    
    CRITICAL FIX: Epsilon now implements proper state stochasticity as per spec:
    - With probability ε, BOTH the true HES state AND the observed cue are independently randomized
    - This breaks the learnable correlation between cue and state, making the environment unpredictable
    - With probability (1-ε), follow the normal permutation sequence with noisy temperature observations
    
    Args:
        perm: Permutation of [0,1,2,3,4] defining the daily cycle
        rng: Random number generator
        eps: Stochasticity level (0.0 = deterministic, 1.0 = completely random)
    
    Returns:
        Array of shape (5, 3): [hes, noisy_temp_obs, slot_idx]
    """
    TEMP_NOISE_SIGMA = 0.2  # From paper specification
    rows = []
    
    for step in range(5):
        if rng.random() < eps:
            # STOCHASTIC STEP: Both true state and cue are independently randomized
            # This breaks any learnable correlation between cue and state
            true_hes = int(rng.integers(0, 5))  # Random true state
            observed_hes = int(rng.integers(0, 5))  # Random observed state (for cue)
            observed_temp = float(HES_TEMPS[observed_hes]) + rng.normal(0.0, TEMP_NOISE_SIGMA)
            slot_idx = step  # Keep track of position in sequence
        else:
            # DETERMINISTIC STEP: Follow permutation with noisy temperature observation
            slot_idx = step
            true_hes = int(perm[slot_idx])
            true_temp = float(HES_TEMPS[true_hes])
            observed_temp = true_temp + rng.normal(0.0, TEMP_NOISE_SIGMA)
        
        rows.append([true_hes, observed_temp, slot_idx])
    
    return np.array(rows, dtype=float)

def make_daily_from_perm_with_epsilon(perm, rng, eps: float):
    """
    ORIGINAL VERSION (INCORRECT): Build one-day sequence following permutation `perm` over 5 substeps.
    With prob 1-ε, advance to next slot (circular). With prob ε, jump to a random slot.
    Adds Gaussian noise (σ=0.2) to temperature observations as per paper spec.
    Returns array of shape (5, 3): [hes, noisy_temp_obs, slot_idx].
    
    NOTE: This implementation is INCORRECT for the stress test because it implements
    slot-jumping noise rather than state stochasticity. Use make_daily_from_perm_with_epsilon_FIXED instead.
    """
    TEMP_NOISE_SIGMA = 0.2  # From paper specification
    slot = int(rng.integers(0, 5))
    rows = []
    for _ in range(5):
        hes = int(perm[slot])
        true_temp = float(HES_TEMPS[hes])
        # Add Gaussian noise to temperature observation
        noisy_temp = true_temp + rng.normal(0.0, TEMP_NOISE_SIGMA)
        rows.append([hes, noisy_temp, slot])
        if rng.random() < (1.0 - eps):
            slot = (slot + 1) % 5
        else:
            slot = int(rng.integers(0, 5))  # uniform jump
    return np.array(rows, dtype=float)  # third col integer content; float is fine for ndarray

def ticket_factory(perm: List[int]) -> Dict:
    """Build a ticket encoding the permutation rule.
    Unlock slot is where HES==3; targets are slots where HES in {0,4} (dusk and dawn)."""
    p3_slot = perm.index(3)
    p1_slots = [i for i, v in enumerate(perm) if v in {0, 4}]
    dists = [(s - p3_slot) % 5 for s in p1_slots]
    return {"perm": perm, "p3_slot": p3_slot, "p1_slots": p1_slots, "distances": dists}

def hamming_to_canon(perm: List[int]) -> int:
    return sum(int(v != i) for i,v in enumerate(perm))

def _count_switches_circular(seq: List[int]) -> int:
    return sum(int(seq[i] != seq[(i+1)%5]) for i in range(5))

def rule_complexity_min_switches(perm: List[int]) -> int:
    """Min switches to satisfy: P3 at p3_slot and P1 at both p1_slots."""
    p3_slot = perm.index(3)
    p1_slots = [i for i,v in enumerate(perm) if v in {0,4}]
    best = math.inf
    for assign in itertools.product([0,1,2], repeat=5):
        if assign[p3_slot] != 2:   # P3
            continue
        if any(assign[s] != 0 for s in p1_slots):  # P1
            continue
        best = min(best, _count_switches_circular(list(assign)))
    return int(best if best < math.inf else 5)

def _run_one_pop(
    agent_cls,
    fitness_table: np.ndarray,
    days: int,
    n_agents: int,
    rng_seed: int,
    ticket: Dict,
    eps: float,
    gamma: float,
    cost_mult: float
) -> tuple[float, float]:
    rng = np.random.default_rng(rng_seed)
    genomes = [rng.random(GENOME_LENGTH) < 0.5 for _ in range(n_agents)]
    agents = [agent_cls(g, fitness_table) for g in genomes]
    pop = MoranPopulation(agents, mu=1e-4, rng=rng)
    ent = []
    for _ in range(days):
        daily = make_daily_from_perm_with_epsilon_FIXED(ticket['perm'], rng, eps)  # Use FIXED version
        pop.run_daily_cycle(daily, ticket=ticket, gamma=gamma, cost_multiplier=cost_mult)
        pop.moran_step()
        # simple genotype-phenotype sequence entropy
        seqs = ["".join(map(str, a.phenotype)) for a in pop.agents]
        if seqs:
            _, counts = np.unique(seqs, return_counts=True)
            p = counts / counts.sum()
            ent.append(-np.sum(p*np.log2(p)))

    mean_fit = float(np.mean([a.fitness for a in pop.agents]))
    mean_ent = float(np.mean(ent[-50:] if len(ent) >= 50 else ent)) if ent else 0.0
    return mean_fit, mean_ent

def topology_scan(
    n_perm: int, days: int, reps: int, n_agents: int, fitness_table: np.ndarray, seed: int = 0
) -> list[dict]:
    rng = np.random.default_rng(seed)
    out: list[dict] = []
    for i in range(n_perm):
        print(f"--- Starting permutation {i+1}/{n_perm} (seed: {seed}) ---", flush=True)
        perm = list(rng.permutation(5))
        T = ticket_factory(perm)
        ham = hamming_to_canon(perm)
        cx  = rule_complexity_min_switches(perm)

        mba_runs, ba_runs, Hb_runs, Hm_runs = [], [], [], []
        for r in range(reps):
            print(f"  Rep {r+1}/{reps}...", flush=True)
            mba_fit, Hm = _run_one_pop(MBAgent,  fitness_table, days, n_agents, rng.integers(2**63), T)
            ba_fit,  Hb = _run_one_pop(BlindAgent, fitness_table, days, n_agents, rng.integers(2**63), T)
            mba_runs.append(mba_fit); ba_runs.append(ba_fit)
            Hm_runs.append(Hm); Hb_runs.append(Hb)

        mba_mean = float(np.mean(mba_runs)); ba_mean = float(np.mean(ba_runs))
        delta_ratio = (mba_mean / ba_mean) if ba_mean > 0 else float("inf")
        out.append({
            "perm": perm,
            "p3_slot": T["p3_slot"],
            "p1_slots": T["p1_slots"],
            "hamming": ham,
            "complexity_min_switches": cx,
            "mba_mean": mba_mean,
            "ba_mean": ba_mean,
            "delta_ratio": delta_ratio,
            "entropy_mba": float(np.mean(Hm_runs)),
            "entropy_ba": float(np.mean(Hb_runs)),
            "days": days, "reps": reps, "n_agents": n_agents,
        })
    return out
