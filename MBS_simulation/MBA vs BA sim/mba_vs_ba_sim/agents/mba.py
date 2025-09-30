from __future__ import annotations

import numpy as np
from scipy.special import kl_div

from .base import AgentBase, conditional_fitness
from .blind import GENOME_LENGTH, L_PHENO, N_PHENO_VECTORS, L_TRANS, L_SENS

# --- New Constants for the MBA ---
C_KL_PROB = 0.02    # Cost multiplier for KL divergence of transition probabilities
C_HAMMING = 0.01  # Cost per bit of difference in phenotype sequences
K_STABLE_MBA = 3  # Consecutive days of high fitness to trigger assimilation (reduced from 5)
FITNESS_THRESHOLD = 0.65 # Fitness threshold to be considered "high" (reduced from 0.8)

class MBAgent(AgentBase):
    """Memory Bayesian Agent with a dual-layer, probabilistic phenotype strategy."""

    def __init__(self, genome: np.ndarray, fitness_table: np.ndarray, learning_rate: float = 0.3):
        if genome.size != GENOME_LENGTH:
            raise ValueError(f"MBAgent genome must be of length {GENOME_LENGTH}")
        if genome.dtype != bool:
            genome = genome.astype(bool)

        super().__init__(genome=genome, phenotype=np.array([])) # Phenotype set below
        self._fitness_table = fitness_table
        self.learning_events = 0
        self.preparation_total_steps = 0
        self.preparation_successful_steps = 0

        # 1. Decode Genomic (Prior) Strategy
        self.geno_pheno_seq, self.geno_trans_prob, self.geno_sensitivity = self._decode_strategy(genome)

        # 2. Initialize Learned (Posterior) Strategy as a copy of the prior
        self.learned_pheno_seq = self.geno_pheno_seq.copy()
        self.learned_trans_prob = self.geno_trans_prob

        # Sensitivity is a fixed genetic trait, not learned within a lifetime
        self.sensitivity = self.geno_sensitivity

        # Set the agent's active phenotype sequence (from the learning layer)
        self.phenotype = self.learned_pheno_seq

        # Learning rate for daily performance updates
        self.learning_rate = learning_rate

        # Whole-genome assimilation tracking
        self.successful_days_counter = 0

    def _decode_strategy(self, genome_vector: np.ndarray) -> tuple[np.ndarray, float, float]:
        """Decodes a 452-bit vector into a phenotype sequence, transition probability, and sensitivity."""
        # Decode Phenotype Sequence
        pheno_vectors = np.split(genome_vector[:N_PHENO_VECTORS * L_PHENO], N_PHENO_VECTORS)
        
        # Use BlindAgent's cached centroids
        if L_PHENO not in BlindAgent._CENTROIDS:
            zeros, half, ones = np.zeros(L_PHENO, dtype=bool), np.concatenate([np.ones(L_PHENO // 2, dtype=bool), np.zeros(L_PHENO - L_PHENO // 2, dtype=bool)]), np.ones(L_PHENO, dtype=bool)
            BlindAgent._CENTROIDS[L_PHENO] = np.stack([zeros, half, ones])
        centroids = BlindAgent._CENTROIDS[L_PHENO]

        phenotype_sequence = [np.argmin(np.sum(np.logical_xor(vec, centroids), axis=1)) for vec in pheno_vectors]
        
        # Decode Transition Probability
        trans_vec = genome_vector[N_PHENO_VECTORS * L_PHENO : -L_SENS]
        transition_prob = np.sum(trans_vec) / L_TRANS
        
        # Decode Temperature Sensitivity
        sens_vec = genome_vector[-L_SENS:]
        sensitivity = (np.sum(sens_vec) - (L_SENS / 2)) / (L_SENS / 2)

        return np.array(phenotype_sequence), transition_prob, sensitivity

    def plasticity_cost(self) -> float:
        """Calculate cost based on divergence between learned and genomic strategies."""
        # 1. KL Divergence for baseline transition probabilities with ε-clamping
        p, q = self.learned_trans_prob, self.geno_trans_prob
        
        # ε-clamp probabilities for numerical stability
        epsilon = 1e-6
        p_clamped = np.clip(p, epsilon, 1 - epsilon)
        q_clamped = np.clip(q, epsilon, 1 - epsilon)
        
        # Compute Bernoulli KL divergence: KL(p||q) = p*log(p/q) + (1-p)*log((1-p)/(1-q))
        kl_prob = (p_clamped * np.log(p_clamped / q_clamped) + 
                   (1 - p_clamped) * np.log((1 - p_clamped) / (1 - q_clamped)))

        # 2. Hamming distance for phenotype sequences
        hamming_dist = np.sum(self.learned_pheno_seq != self.geno_pheno_seq)

        return (C_KL_PROB * kl_prob) + (C_HAMMING * hamming_dist)

    def daily_fitness(self, hes: int) -> float:
        """Calculate the raw fitness for the day based on the learned strategy."""
        current_phenotype = self.phenotype[self.phenotype_index]
        return float(self._fitness_table[hes, current_phenotype])

    def update_phenotype_history(self, rng: np.random.Generator, d_temp: float) -> None:
        """Probabilistically advance the *learned* phenotype sequence based on d(temp)."""
        self.previous_phenotype = self.phenotype[self.phenotype_index]
        
        # Normalize deltaT to [0, 1] range
        # Temperature range from Table 1: max(T) - min(T) = 2.87
        temp_range = 2.87
        normalized_delta = min(1.0, abs(d_temp) / temp_range)
        
        # Formula from paper: P_effective = p_base * (1 + C * norm(|ΔT|))
        # C=0: P_eff = p_base (baseline behavior)
        # C>0: P_eff increases with temperature change
        # C<0: P_eff decreases with temperature change
        effective_prob = self.learned_trans_prob * (1 + self.sensitivity * normalized_delta)
        effective_prob = np.clip(effective_prob, 0, 1)

        if rng.random() < effective_prob:
            self.phenotype_index = (self.phenotype_index + 1) % len(self.phenotype)

    def assimilate_genome(self) -> None:
        """
        Whole-genome assimilation: copy entire learned strategy to genome.
        
        This method implements the spec-aligned assimilation where the entire
        learned phenotype sequence and transition probability are written back
        to the genome after K consecutive successful days.
        """
        # Copy learned strategy to genomic strategy
        self.geno_pheno_seq = self.learned_pheno_seq.copy()
        self.geno_trans_prob = self.learned_trans_prob
        
        # Update genome bit-vector for phenotypes
        for i, phenotype in enumerate(self.learned_pheno_seq):
            centroid_vec = BlindAgent._CENTROIDS[L_PHENO][phenotype]
            start_index, end_index = i * L_PHENO, (i + 1) * L_PHENO
            self.genome[start_index:end_index] = centroid_vec
        
        # Update genome bit-vector for transition probability
        num_ones = int(round(self.learned_trans_prob * L_TRANS))
        trans_vec = np.concatenate([
            np.ones(num_ones, dtype=bool), 
            np.zeros(L_TRANS - num_ones, dtype=bool)
        ])
        np.random.default_rng().shuffle(trans_vec)
        self.genome[N_PHENO_VECTORS * L_PHENO : -L_SENS] = trans_vec
        
        # Reset learned layer to genome (drops plasticity cost to 0)
        self.learned_pheno_seq = self.geno_pheno_seq.copy()
        self.learned_trans_prob = self.geno_trans_prob
        self.phenotype = self.learned_pheno_seq
        
        # Reset counter
        self.successful_days_counter = 0

    def learn_from_daily_performance(self, daily_fitness_history: list[float], daily_hes_history: list[int], rng: np.random.Generator):
        """
        Update learned strategy based on daily performance and handle assimilation.
        
        This is where the main learning happens - based on daily regret calculation.
        """
        avg_daily_fitness = np.mean(daily_fitness_history)
        
        # Calculate theoretical optimal daily fitness
        # For each HES state in the day, find the maximum possible fitness
        # considering both prepared and unprepared states
        daily_optimal_fitness = []
        for hes in daily_hes_history:
            # Calculate optimal fitness for each phenotype at this HES
            max_fitness_for_hes = 0.0
            for phenotype in [0, 1, 2]:  # P1, P2, P3
                # Check both prepared and unprepared states
                for is_prepared in [True, False]:
                    fitness = conditional_fitness(self._fitness_table, hes, phenotype, is_prepared, 0.7)
                    max_fitness_for_hes = max(max_fitness_for_hes, fitness)
            daily_optimal_fitness.append(max_fitness_for_hes)
        
        avg_optimal_fitness = np.mean(daily_optimal_fitness)
        
        # Calculate daily regret
        daily_regret = avg_optimal_fitness - avg_daily_fitness
        
        # Learning parameters
        regret_threshold = 0.2
        eta_p = 0.05  # Transition probability learning rate
        
        # Daily learning decision based on regret
        random_roll = rng.random()
        should_learn = daily_regret > regret_threshold and random_roll < self.learning_rate
        
        # Debug output (remove in production)
        # print(f"DEBUG: daily_regret={daily_regret:.3f}, threshold={regret_threshold}, random_roll={random_roll:.3f}, learning_rate={learning_rate}, should_learn={should_learn}")
        
        if should_learn:
            # Randomly select a position in the phenotype sequence to modify
            position_to_modify = rng.integers(0, len(self.learned_pheno_seq))
            current_pheno = self.learned_pheno_seq[position_to_modify]
            possible_phenos = [p for p in [0, 1, 2] if p != current_pheno]
            if possible_phenos:  # Safety check
                new_pheno = rng.choice(possible_phenos)
                self.learned_pheno_seq[position_to_modify] = new_pheno
                # Update active phenotype sequence
                self.phenotype = self.learned_pheno_seq
            
            # Adjust transition probability toward higher values (0.9 target)
            self.learned_trans_prob += eta_p * (0.9 - self.learned_trans_prob)
            self.learned_trans_prob = np.clip(self.learned_trans_prob, 0.0, 1.0)

        # --- Whole-Genome Assimilation Check ---
        if avg_daily_fitness > FITNESS_THRESHOLD:
            self.successful_days_counter += 1
        else:
            self.successful_days_counter = 0
        
        # Trigger assimilation if threshold reached
        if self.successful_days_counter >= K_STABLE_MBA:
            self.assimilate_genome()

    def learn_step(self, realized_fitness: float, hes: int, is_prepared: bool, rng: np.random.Generator) -> None:
        """
        Per-step learning with conditional optimum regret.
        
        Args:
            realized_fitness: Actual fitness achieved this step (before plasticity cost)
            hes: Current HES state (0-4)
            is_prepared: Whether agent is in prepared state from P3@HES3
            rng: Random number generator
        """
        # Compute conditional optimum: maximum fitness attainable given current preparation status
        f_opt_candidates = []
        for phenotype in [0, 1, 2]:  # P1, P2, P3
            f_opt_candidates.append(conditional_fitness(self._fitness_table, hes, phenotype, is_prepared, 0.7))
        f_opt = max(f_opt_candidates)
        
        # Calculate regret
        regret = f_opt - realized_fitness
        
        # Learning threshold and rate
        regret_threshold = 0.2
        eta_p = 0.05  # Transition probability learning rate
        
        self.preparation_total_steps += 1
        if is_prepared:
            self.preparation_successful_steps += 1
        
        if regret > regret_threshold and rng.random() < self.learning_rate:
            self.learning_events += 1
            # Update phenotype at current sequence position
            current_pheno = self.learned_pheno_seq[self.phenotype_index]
            possible_phenos = [p for p in [0, 1, 2] if p != current_pheno]
            if possible_phenos:  # Safety check
                new_pheno = rng.choice(possible_phenos)
                self.learned_pheno_seq[self.phenotype_index] = new_pheno
                # Update active phenotype sequence
                self.phenotype = self.learned_pheno_seq
            
            # Adjust transition probability toward higher values (0.9 target)
            self.learned_trans_prob += eta_p * (0.9 - self.learned_trans_prob)
            self.learned_trans_prob = np.clip(self.learned_trans_prob, 0.0, 1.0)

    def step(self, hes: int, d_temp: float, is_prepared: bool, penalty_size: float = 0.7, cost_multiplier: float = 1.0, rng: np.random.Generator = np.random.default_rng()):
        """
        A single step of the agent's life cycle: calculate fitness and update state.
        
        Args:
            hes: Current HES state (0-4)
            d_temp: Temperature change from previous step
            is_prepared: Whether agent is in prepared state from P3@HES3
            penalty_size: Penalty applied to unprepared P1 at HES 0/4
            cost_multiplier: Multiplier for plasticity cost
            rng: Random number generator
        """
        # 1. Calculate fitness using centralized conditional fitness function, including plasticity cost
        current_phenotype = self.phenotype[self.phenotype_index]
        realized_fitness = conditional_fitness(self._fitness_table, hes, current_phenotype, is_prepared, penalty_size)
        self.fitness = realized_fitness - (cost_multiplier * self.plasticity_cost())

        # 2. Update phenotype history (and maybe transition)
        self.update_phenotype_history(rng, d_temp)

# Need to import BlindAgent for the centroid cache to work
from .blind import BlindAgent
