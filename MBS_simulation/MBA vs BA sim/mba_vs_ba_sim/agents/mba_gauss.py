from __future__ import annotations

import numpy as np
from scipy.stats import norm

from .base import AgentBase

C_MEM = 0.02
C_LT = 0.0
SIGMA_FIXED = 0.3  # fixed sensing noise width


def decode_genome(genome: np.ndarray) -> np.ndarray:  # returns mu_k array length 3
    """Map 30-bit genome → three optimal temperatures.

    10 bits per phenotype, interpreted as unsigned int 0..1023 mapped
    linearly to range [-2, 4].
    """
    if genome.size != 30:
        raise ValueError("Gaussian MBA genome must be 30 bits long")
    mus = []
    for i in range(3):
        bits = genome[i * 10 : (i + 1) * 10]
        val = int("".join("1" if b else "0" for b in bits), 2)
        mu = -2 + (val / 1023) * 6  # map
        mus.append(mu)
    return np.array(mus, dtype=float)


class GaussianMBAgent(AgentBase):
    """MBA variant that maps temperature cue directly to phenotype via Gaussian filters."""

    def __init__(self, genome: np.ndarray, fitness_table: np.ndarray):
        if genome.dtype != bool:
            genome = genome.astype(bool)
        mu_opts = decode_genome(genome)
        self.mu_opts = mu_opts
        self.post = np.ones(3) / 3  # uniform initial
        phenotype = int(np.argmax(self.post))
        super().__init__(genome=genome, phenotype=phenotype)
        self._fitness_table = fitness_table
        self.assimilated = False

    def update_and_choose(self, T_obs: float, hes: int) -> None:
        lik = norm.pdf(T_obs, loc=self.mu_opts, scale=SIGMA_FIXED)
        total = lik.sum()
        if total == 0 or np.isnan(total):
            post = np.ones(3) / 3
        else:
            post = lik / total
        self.post = post
        self.phenotype = int(np.argmax(post))
        with np.errstate(divide="ignore", invalid="ignore"):
            ent = -np.sum(post * np.log(post, where=post > 0))
        cost = C_LT if self.assimilated else C_MEM * ent
        self.fitness = self._fitness_table[hes, self.phenotype] - cost

    def update_phenotype_history(self) -> None:  # noqa: D401
        """Update phenotype history tracking."""
        self.previous_phenotype = self.phenotype


def create_sensible_gaussian_genome(rng: np.random.Generator | None = None) -> np.ndarray:
    """Create a genome with sensible temperature preferences.
    
    Initializes μ values near reasonable temperatures:
    - μ₁ near -0.5 (for cold dawn/dusk → P1)
    - μ₂ near 0.5 (for moderate morning → P2)
    - μ₃ near 2.0 (for afternoon spike → P3)
    """
    if rng is None:
        rng = np.random.default_rng()
    
    # Target temperatures with some variation
    target_temps = [-0.5, 0.5, 2.0]
    genome_bits = []
    
    for target in target_temps:
        # Add noise to target
        noisy_target = target + rng.normal(0, 0.3)
        # Clamp to valid range [-2, 4]
        noisy_target = np.clip(noisy_target, -2, 4)
        # Convert to bits (10 bits per phenotype)
        val = int((noisy_target + 2) / 6 * 1023)
        # Convert to binary string to match decode_genome's expectation
        bit_string = format(val, '010b')
        bits = [c == '1' for c in bit_string]
        genome_bits.extend(bits)
    
    return np.array(genome_bits, dtype=bool) 