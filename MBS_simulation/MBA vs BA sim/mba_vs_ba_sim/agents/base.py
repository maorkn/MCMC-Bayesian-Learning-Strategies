from __future__ import annotations

import numpy as np
from abc import ABC, abstractmethod


def conditional_fitness(fitness_table: np.ndarray, hes: int, phenotype: int, is_prepared: bool, 
                       penalty_size: float = 0.7) -> float:
    """
    Calculate fitness with preparation-dependent penalty model.
    
    This centralized function implements the penalty model approach where:
    - Base fitness table stores maximum achievable values
    - P1 at HES 0/4 gets penalty when unprepared
    - All other phenotype/HES combinations use base fitness directly
    
    Args:
        fitness_table: Base fitness lookup table with maximum values
        hes: Current HES state (0-4)
        phenotype: Current phenotype (0=P1, 1=P2, 2=P3)
        is_prepared: Whether agent is in prepared state from P3@HES3
        penalty_size: Penalty applied to unprepared P1 at HES 0/4 (0.0-1.0)
    
    Returns:
        Adjusted fitness value
    """
    base_fitness = float(fitness_table[hes, phenotype])
    
    # Apply penalty model for P1 at nitrogen-rich states (HES 0/4)
    if hes in {0, 4} and phenotype == 0:  # P1 at HES 0/4
        if not is_prepared:
            return max(0.0, base_fitness - penalty_size)
    
    return base_fitness


class AgentBase(ABC):
    """Base class for all agents in the simulation."""
    
    def __init__(self, genome: np.ndarray, phenotype: np.ndarray):
        self.genome = genome.copy()
        self.phenotype = phenotype.copy()
        self.phenotype_index = 0
        self.fitness = 0.0
        self.age = 0
        self.lifespan = 20
        self.previous_phenotype = None
        
        # Preparation state tracking
        self.preparation_countdown = 0  # For canonical HES sequences
        self.prep_timers = []  # For permutation sequences
    
    @abstractmethod
    def daily_fitness(self, hes: int) -> float:
        """Calculate the base fitness for the current phenotype at given HES."""
        pass
    
    @abstractmethod
    def update_phenotype_history(self, rng: np.random.Generator, d_temp: float) -> None:
        """Update phenotype history and potentially transition."""
        pass
    
    def mutate_genome(self, mu: float, rng: np.random.Generator) -> None:
        """Apply bitwise mutation to the genome."""
        mutation_mask = rng.random(len(self.genome)) < mu
        self.genome[mutation_mask] = ~self.genome[mutation_mask]
