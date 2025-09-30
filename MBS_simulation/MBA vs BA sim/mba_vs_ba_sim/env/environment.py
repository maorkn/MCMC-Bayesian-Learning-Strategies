from __future__ import annotations

import numpy as np

class Environment:
    """
    Generates and manages the environmental conditions for the simulation.
    """

    def __init__(self, T: int, eps: float, rho: float, rng: np.random.Generator):
        self.T = T
        self.eps = eps
        self.rho = rho
        self.rng = rng
        self.hes_seq = self._generate_hes_sequence()

    def _generate_hes_sequence(self) -> np.ndarray:
        """
        Generates the sequence of Hidden Environmental States (HES) and cues.
        Returns a (T*5, 2) array where column 0 is the true state and column 1 is the cue.
        """
        hes_seq = np.zeros((self.T * 5, 2), dtype=int)
        
        # Initial state
        current_state = self.rng.integers(0, 5)
        
        for t in range(self.T * 5):
            # Autocorrelation
            if self.rng.random() >= self.rho:
                current_state = (current_state + 1) % 5
            
            hes_seq[t, 0] = current_state
            
            # Noise
            if self.rng.random() < self.eps:
                hes_seq[t, 1] = self.rng.integers(0, 5)
            else:
                hes_seq[t, 1] = current_state
                
        return hes_seq

    def get_state_and_cue(self, t: int) -> tuple[int, int]:
        """
        Returns the true state and cue for a given time step.
        """
        true_state, cue = self.hes_seq[t]
        return true_state, cue
