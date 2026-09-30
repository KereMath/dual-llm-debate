"""
Phases Module
Grounding, parallel drafting, iterative debate (phase 3+4) and intersection synthesis
"""

from .phase_1_grounding import phase_1_grounding
from .phase_2_parallel_drafting import phase_2_parallel_drafting_sync
from .phase_3_4_iterative_debate import run_debate_loop
from .phase_5_intersection import phase_5_intersection_synthesis

__all__ = [
    "phase_1_grounding",
    "phase_2_parallel_drafting_sync",
    "run_debate_loop",
    "phase_5_intersection_synthesis",
]
