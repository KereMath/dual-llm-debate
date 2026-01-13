"""
Research & Publishing Machine
Dual-LLM Debate System for Academic PDF Generation
"""

__version__ = "1.0.0"

from .workflow import run_research, setup_logging
from .schemas import DebateState
from .config import config

__all__ = ["run_research", "setup_logging", "DebateState", "config"]
