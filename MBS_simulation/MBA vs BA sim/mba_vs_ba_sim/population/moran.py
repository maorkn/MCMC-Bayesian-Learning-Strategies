from __future__ import annotations

import copy
import random
from typing import List, Dict

import numpy as np

from ..agents.base import AgentBase, conditional_fitness
from ..agents.blind import BlindAgent
from ..agents import mba as mba_mod
from ..agents.mba import MBAgent
from ..agents.mba_gauss import GaussianMBAgent
from ..env.environment import Environment
from ..preparatory_rule import compile_preparatory_rule, PreparatoryRule

DEFAULT_CUES: tuple[float, float, float] = (0.0, 0.0, 0.0)  # placeholder cues

class MoranPopulation:  # noqa: D101
    def __init__(self, agents: List[AgentBase], mu: float = 1e-4, rng: np.random.Generator | None = None):
        if not agents:
            raise ValueError("Population cannot be empty.")
        self.agents: List[AgentBase] = agents
        self.mu = mu
        self.rng = rng or np.random.default_rng()

    def run_daily_cycle(
        self,
        hes_seq: np.ndarray,
        ticket: dict | None = None,
        *,
        penalty_size: float = 0.7,   # penalty applied to unprepared P1 at HES 0/4
        cost_multiplier: float = 1.0, # scales MBA plasticity cost
        gamma: float | None = None   # backward compatibility: converts to penalty_size
    ) -> None:
        """
        Runs the full 5-HES cycle for a single day, calculates final daily fitness,
        and allows agents to learn at each sub-step.
        
        Args:
            hes_seq: Array of HES states and cues for the day
            ticket: Optional permutation ticket for non-canonical sequences (DEPRECATED)
            penalty_size: Penalty applied to unprepared P1 at HES 0/4 (0.0-1.0)
            cost_multiplier: Multiplier for MBA plasticity cost
            gamma: Backward compatibility parameter - converts to penalty_size
        """
        # Handle backward compatibility with gamma parameter
        if gamma is not None:
            penalty_size = gamma

        # Determine if we're using a permutation or canonical sequence
        if ticket is not None:
            # Legacy ticket system - extract permutation and use new rule system
            perm = ticket.get("perm", [0, 1, 2, 3, 4])
            self._run_daily_cycle_with_preparatory_rule(hes_seq, perm, penalty_size, cost_multiplier)
        else:
            # Canonical sequence [0, 1, 2, 3, 4]
            self._run_daily_cycle_with_preparatory_rule(hes_seq, [0, 1, 2, 3, 4], penalty_size, cost_multiplier)

    def _run_daily_cycle_with_preparatory_rule(
        self,
        hes_seq: np.ndarray,
        perm: List[int],
        penalty_size: float,
        cost_multiplier: float
    ) -> None:
        """
        Run daily cycle using the new PreparatoryRule system.
        
        Args:
            hes_seq: Array of HES states and cues for the day
            perm: HES permutation sequence (e.g., [0,1,2,3,4] for canonical)
            penalty_size: Penalty applied to unprepared P1 at HES 0/4
            cost_multiplier: Multiplier for MBA plasticity cost
        """
        daily_fitness_accumulator: Dict[int, List[float]] = {id(a): [] for a in self.agents}

        # Create preparatory rule for this permutation
        prep_rule = compile_preparatory_rule(perm)
        
        # Create per-agent rule instances (each agent needs independent state)
        agent_rules: Dict[int, PreparatoryRule] = {}
        for agent in self.agents:
            agent_rules[id(agent)] = compile_preparatory_rule(perm)

        prev_temp = 0.0
        
        for t in range(hes_seq.shape[0]):
            # Extract HES and cue
            if hes_seq.shape[1] >= 3:
                hes, cue, slot_idx = int(hes_seq[t,0]), hes_seq[t,1], int(hes_seq[t,2])
            else:
                hes, cue = int(hes_seq[t,0]), hes_seq[t,1]
                slot_idx = t  # backward compatible

            d_temp = cue - prev_temp

            for agent in self.agents:
                current_phenotype = agent.phenotype[agent.phenotype_index]
                agent_id = id(agent)
                agent_rule = agent_rules[agent_id]
                
                # Update preparatory state using the ACTUAL HES and current phenotype
                agent_rule.step_fitness(current_phenotype, slot_idx, hes)
                is_prepared = agent_rule.is_prepared()

                # Compute fitness centrally using the penalty model against the actual HES
                base_fit = agent.daily_fitness(hes)
                if hes in (0, 4) and current_phenotype == 0 and not is_prepared:
                    sub_step_fitness = max(0.0, base_fit - penalty_size)
                else:
                    sub_step_fitness = base_fit

                # Store fitness for daily average
                daily_fitness_accumulator[agent_id].append(sub_step_fitness)

                # Agent-specific processing
                if isinstance(agent, BlindAgent):
                    agent.fitness = sub_step_fitness
                elif isinstance(agent, MBAgent):
                    agent.fitness = sub_step_fitness
                    
                    # Per-step learning as specified in the paper
                    agent.learn_step(sub_step_fitness, hes, is_prepared, self.rng)
                elif isinstance(agent, GaussianMBAgent):
                    # This agent remains incompatible and should be updated or removed
                    T_obs = cue
                    agent.update_and_choose(T_obs, hes)
                    sub_step_fitness = agent.fitness
                    daily_fitness_accumulator[agent_id][-1] = sub_step_fitness
                else:
                    raise TypeError(f"Unknown agent subclass encountered: {type(agent)}")

                # Agent state update happens after each HES
                if hasattr(agent, 'update_phenotype_history'):
                    agent.update_phenotype_history(self.rng, d_temp)
            
            prev_temp = cue

        # After the day is over, calculate the average fitness
        for agent in self.agents:
            agent_id = id(agent)
            fitness_history = daily_fitness_accumulator[agent_id]
            agent.fitness = max(0.0, float(np.mean(fitness_history)))
            
            # Apply MBA plasticity cost
            if isinstance(agent, MBAgent):
                agent.fitness = max(0.0, agent.fitness - cost_multiplier * agent.plasticity_cost())
                
                # Check for genetic assimilation
                avg_daily_fitness = agent.fitness
                if avg_daily_fitness > 0.65:  # FITNESS_THRESHOLD
                    agent.successful_days_counter += 1
                else:
                    agent.successful_days_counter = 0
                
                if agent.successful_days_counter >= 3:  # K_STABLE_MBA
                    agent.assimilate_genome()

            # Reset phenotype index for the next day's cycle
            agent.phenotype_index = 0
            
            # Note: Preparatory rule state is NOT reset at end of day
            # It resets when cycling back to HES 3, as per the biological logic

    # ------------------------------------------------------------------
    def moran_step(self) -> None:  # noqa: D401
        """Execute a single Moran birth–death event keeping population size constant."""
        total_fit = sum(a.fitness for a in self.agents)
        # If everyone has zero fitness we fall back to uniform parent choice
        if total_fit == 0.0:
            weights = None
        else:
            weights = [a.fitness / total_fit for a in self.agents]

        parent_idx = self.rng.choice(len(self.agents), p=weights)
        victim_idx = self.rng.choice(len(self.agents))

        parent = self.agents[parent_idx]
        victim = self.agents[victim_idx]

        # Produce child (clone + mutation) --------------------------------
        child = copy.deepcopy(parent)
        child.age = 0
        child.lifespan = random.randint(10, 25)
        child.mutate_genome(self.mu, rng=self.rng)

        # Replace victim with child --------------------------------------
        self.agents[victim_idx] = child

        # Age survivors ---------------------------------------------------
        for idx, agent in enumerate(self.agents):
            if idx != victim_idx:
                agent.age += 1

    # ------------------------------------------------------------------
    def __len__(self) -> int:  # noqa: D401
        return len(self.agents)
