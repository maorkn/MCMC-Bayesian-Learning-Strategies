"""
Simple Preparatory Rule System for HES Permutations

Simple Rule:
- If P3 @HES3: unlock = True  
- If unlock AND P1 at HES4: fitness = 1.0, else fitness = 0.3 
- If unlock AND P1 at HES0: fitness = 1.0, else fitness = 0.3   
- After 4 steps (1 complete cycle) → unlock = False 
"""

def generate_rule(sequence):
    """
    Generates a permuted rule string based on the positions of HES 3, 0, and 4 in the given sequence.

    :param sequence: A list or tuple representing the permutation of HES (e.g., [0, 3, 2, 1, 4])
    :return: A string representing the permuted rule.
    """
    # Find the slots (0-based indices) for HES 3, 0, and 4
    slot_3 = sequence.index(3)
    slot_0 = sequence.index(0)
    slot_4 = sequence.index(4)
    
    # Format the rule string with the found slots
    rule = f"""Simple Rule:
- If P3 @HES3 (slot {slot_3}): unlock = True  
- If unlock AND P1 at HES4 (slot {slot_4}): fitness = 1.0, else fitness = 0.3 
- If unlock AND P1 at HES0 (slot {slot_0}): fitness = 1.0, else fitness = 0.3   
- After 4 steps (1 complete cycle) → unlock = False 
"""
    return rule

class SimplePreparatoryRule:
    """Simple stateful preparatory rule."""
    
    def __init__(self, sequence):
        self.sequence = sequence
        self.slot_3 = sequence.index(3)
        self.slot_0 = sequence.index(0) 
        self.slot_4 = sequence.index(4)
        self.unlock = False
        self.uses_left = 0
        self.steps_since_unlock = 0
        
    def reset(self):
        """Reset for new day."""
        self.unlock = False
        self.uses_left = 0
        self.steps_since_unlock = 0
        
    def step_fitness(self, phenotype_idx, slot_idx, current_hes):
        """Update preparation state for this step; fitness is computed externally.

        Args:
            phenotype_idx: current phenotype (0=P1, 1=P2, 2=P3)
            slot_idx: index within the (permuted) 5-slot daily cycle [0..4]
            current_hes: the actual environmental state at this step (0..4)

        Returns:
            None (fitness is computed by the caller using the central conditional_fitness)
        """
        # Trigger unlock only when P3 is expressed at the actual HES 3
        if current_hes == 3 and phenotype_idx == 2:  # P3 @ HES3
            self.unlock = True
            self.uses_left = 2
            self.steps_since_unlock = 1  # Count this trigger step

        # If prepared P1 use occurs at HES 0/4, consume one use (fitness bonus applied externally)
        if phenotype_idx == 0 and current_hes in (0, 4):
            if self.unlock and self.uses_left > 0:
                self.uses_left -= 1

        # Increment unlock lifetime and expire after a full cycle (4 subsequent steps)
        if self.unlock and not (current_hes == 3 and phenotype_idx == 2):
            self.steps_since_unlock += 1
            if self.steps_since_unlock > 4:
                self.unlock = False
                self.uses_left = 0
                self.steps_since_unlock = 0

        return None
        
    def is_prepared(self):
        """Check if currently prepared."""
        return self.unlock and self.uses_left > 0

# Backward compatibility
def compile_preparatory_rule(sequence):
    """Create a simple preparatory rule for the sequence."""
    return SimplePreparatoryRule(sequence)

PreparatoryRule = SimplePreparatoryRule
