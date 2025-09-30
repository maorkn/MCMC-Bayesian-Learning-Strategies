from __future__ import annotations

import numpy as np

from .base import AgentBase, conditional_fitness

# Define constants for the new genome structure
L_PHENO = 64  # Length of a single phenotype-encoding vector
N_PHENO_VECTORS = 5  # Number of phenotype vectors
L_TRANS = 100  # Length of the transition probability vector
L_SENS = 32 # Length of the temperature sensitivity vector
GENOME_LENGTH = (N_PHENO_VECTORS * L_PHENO) + L_TRANS + L_SENS
SENSITIVITY_THRESHOLD = 0.5 # The d(temp) threshold to trigger a transition


class BlindAgent(AgentBase):
    """Blind Agent with a genetically-encoded probabilistic phenotype sequence."""

    # Cache centroids per genome length
    _CENTROIDS: dict[int, np.ndarray] = {}

    def __init__(self, genome: np.ndarray, fitness_table: np.ndarray):
        if genome.dtype != bool:
            genome = genome.astype(bool)
        
        if genome.size != GENOME_LENGTH:
            raise ValueError(f"BlindAgent genome must be of length {GENOME_LENGTH}")

        # --- Decode Phenotype Sequence ---
        pheno_vectors = np.split(genome[:N_PHENO_VECTORS * L_PHENO], N_PHENO_VECTORS)
        
        if L_PHENO not in self._CENTROIDS:
            zeros = np.zeros(L_PHENO, dtype=bool)
            ones = np.ones(L_PHENO, dtype=bool)
            half = np.concatenate([np.ones(L_PHENO // 2, dtype=bool), np.zeros(L_PHENO - L_PHENO // 2, dtype=bool)])
            self._CENTROIDS[L_PHENO] = np.stack([zeros, half, ones])
        centroids = self._CENTROIDS[L_PHENO]

        phenotype_sequence = []
        for vec in pheno_vectors:
            dists = np.sum(np.logical_xor(vec, centroids), axis=1)
            phenotype_sequence.append(int(np.argmin(dists)))

        # --- Decode Transition Probability ---
        trans_vec = genome[N_PHENO_VECTORS * L_PHENO : -L_SENS]
        self.transition_prob = np.sum(trans_vec) / L_TRANS

        # --- Decode Temperature Sensitivity ---
        sens_vec = genome[-L_SENS:]
        # Normalize to [-1, 1]
        self.sensitivity = (np.sum(sens_vec) - (L_SENS / 2)) / (L_SENS / 2)

        super().__init__(genome=genome, phenotype=np.array(phenotype_sequence))
        self._fitness_table = fitness_table

    def daily_fitness(self, hes: int) -> float:
        """Lookup environment multiplier for the current phenotype in the sequence."""
        current_phenotype = self.phenotype[self.phenotype_index]
        return float(self._fitness_table[hes, current_phenotype])

    def _maybe_transition(self, rng: np.random.Generator, d_temp: float) -> None:
        """With probability `P_effective`, advance to the next phenotype."""
        # Normalize deltaT to [0, 1] range
        # Temperature range from Table 1: max(T) - min(T) = 2.87
        temp_range = 2.87
        normalized_delta = min(1.0, abs(d_temp) / temp_range)
        
        # Formula from paper: P_effective = p_base * (1 + C * norm(|ΔT|))
        # C=0: P_eff = p_base (baseline behavior)
        # C>0: P_eff increases with temperature change
        # C<0: P_eff decreases with temperature change
        effective_prob = self.transition_prob * (1 + self.sensitivity * normalized_delta)
        effective_prob = np.clip(effective_prob, 0, 1) # Clamp to valid probability range

        if rng.random() < effective_prob:
            self.phenotype_index = (self.phenotype_index + 1) % len(self.phenotype)

    def update_phenotype_history(self, rng: np.random.Generator, d_temp: float) -> None:
        """Store current phenotype, then check for a temperature-cued transition."""
        self.previous_phenotype = self.phenotype[self.phenotype_index]
        self._maybe_transition(rng, d_temp)

    def step(self, hes: int, d_temp: float, is_prepared: bool, penalty_size: float = 0.7, cost_multiplier: float = 1.0, rng: np.random.Generator = np.random.default_rng()):
        """
        A single step of the agent's life cycle: calculate fitness, then update state.
        
        Args:
            hes: Current HES state (0-4)
            d_temp: Temperature change from previous step
            is_prepared: Whether agent is in prepared state from P3@HES3
            penalty_size: Penalty applied to unprepared P1 at HES 0/4
            cost_multiplier: Not used for BlindAgent (no plasticity cost)
            rng: Random number generator
        """
        # 1. Calculate fitness using centralized conditional fitness function
        current_phenotype = self.phenotype[self.phenotype_index]
        self.fitness = conditional_fitness(self._fitness_table, hes, current_phenotype, is_prepared, penalty_size)
        # Note: BlindAgent has no plasticity cost, so cost_multiplier is ignored

        # 2. Update phenotype history and maybe transition
        self.update_phenotype_history(rng, d_temp)
