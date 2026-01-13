"""
Phases Module
All 5 debate phases + PDF pipeline
"""

from .phase_1_grounding import phase_1_grounding
from .phase_2_parallel_drafting import phase_2_parallel_drafting_sync
from .phase_3_cross_examination import phase_3_cross_examination
from .phase_4_convergence import phase_4_convergence_check
from .phase_5_intersection import phase_5_intersection_synthesis

__all__ = [
    "phase_1_grounding",
    "phase_2_parallel_drafting_sync",
    "phase_3_cross_examination",
    "phase_4_convergence_check",
    "phase_5_intersection_synthesis",
]
