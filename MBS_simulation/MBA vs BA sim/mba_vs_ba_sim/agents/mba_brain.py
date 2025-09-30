from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Tuple

import numpy as np

_LOG_2PI = math.log(2.0 * math.pi)


def _gaussian_logpdf(x: float, mu: float, sigma: float) -> float:
    """Return log N(x | mu, sigma^2)."""
    return -0.5 * (_LOG_2PI + 2.0 * math.log(sigma)) - 0.5 * ((x - mu) / sigma) ** 2


@dataclass
class BayesianBrain:  # noqa: D101
    means: np.ndarray  # shape (5, 3)
    sigmas: Tuple[float, float, float]
    pi: np.ndarray  # shape (5,)

    def __post_init__(self) -> None:  # noqa: D401
        self.means = np.asarray(self.means, dtype=float)
        if self.means.shape != (5, 3):
            raise ValueError("means must have shape (5, 3)")
        self.sigmas = tuple(float(s) for s in self.sigmas)
        if len(self.sigmas) != 3:
            raise ValueError("sigmas must have length 3")
        self.pi = np.asarray(self.pi, dtype=float)
        if self.pi.shape != (5,):
            raise ValueError("pi must have length 5")
        # Ensure it sums to 1
        self.pi = self.pi / self.pi.sum()

    # ------------------------------------------------------------------
    def update(self, cue: Tuple[float, float, float]) -> None:  # noqa: D401
        """Bayesian update given noisy cue (T_obs, C_obs, N_obs)."""
        cue_arr = np.asarray(cue, dtype=float)
        if cue_arr.shape != (3,):
            raise ValueError("cue must be 3-length iterable")

        log_likelihoods = np.zeros(5)
        for i in range(5):
            ll = 0.0
            for d in range(3):
                ll += _gaussian_logpdf(cue_arr[d], self.means[i, d], self.sigmas[d])
            log_likelihoods[i] = ll

        # Work in log-space to avoid underflow: posterior ∝ exp(log π + log L)
        log_posterior = np.log(self.pi) + log_likelihoods
        # Normalise in log-space
        log_posterior -= np.max(log_posterior)  # for numerical stability
        posterior = np.exp(log_posterior)
        posterior /= posterior.sum()

        self.pi = posterior

    # ------------------------------------------------------------------
    def entropy(self) -> float:  # noqa: D401
        """Return Shannon entropy of the current belief (nats)."""
        with np.errstate(divide="ignore"):
            ent = -np.sum(self.pi * np.log(self.pi, where=self.pi > 0))
        return float(ent)

    # ------------------------------------------------------------------
    def expected_fitness(self, fitness_table: np.ndarray) -> np.ndarray:  # noqa: D401
        """Return expected fitness for each phenotype (length 3)."""
        if fitness_table.shape != (5, 3):
            raise ValueError("fitness_table must be shape (5,3)")
        return self.pi @ fitness_table  # type: ignore[arg-type]

    def best_phenotype(self, fitness_table: np.ndarray) -> int:  # noqa: D401
        """Return phenotype index (0,1,2) with maximal expected fitness."""
        return int(np.argmax(self.expected_fitness(fitness_table))) 