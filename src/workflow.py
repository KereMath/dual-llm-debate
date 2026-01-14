"""
LangGraph Workflow
Complete cyclic state machine orchestration
"""

import logging
from typing import Literal
from datetime import datetime

from langgraph.graph import StateGraph, END

from .schemas import DebateState
from .phases import (
    phase_1_grounding,
    phase_2_parallel_drafting_sync,
    phase_5_intersection_synthesis,
)
# Import new iterative debate system
from .phases.phase_3_4_iterative_debate import run_debate_loop
from .agents import (
    latex_generation_node,
    pdf_compilation_node,
    quality_assurance_node,
    approval_decision_node,
    pdf_revision_node,
)
from .config import config

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# NODE WRAPPER (Convert DebateState return to dict)
# ═══════════════════════════════════════════════════════════

def wrap_node(func):
    """
    Wrapper to convert DebateState returns to dict for LangGraph compatibility
    LangGraph expects dict updates, not full Pydantic models
    """
    def wrapper(state: DebateState) -> dict:
        # Call original function
        result_state = func(state)

        # Return as dict (partial update)
        if isinstance(result_state, DebateState):
            return result_state.model_dump()
        return result_state

    return wrapper


# ═══════════════════════════════════════════════════════════
# WORKFLOW BUILDER
# ═══════════════════════════════════════════════════════════

def build_research_workflow() -> StateGraph:
    """
    Döngüsel Durum Makinesi (Cyclic State Machine)

    GRAPH STRUCTURE:

    START → grounding → parallel_drafting → cross_examination → convergence
                                                   ↑                 ↓
                                                   └─────NO──────────┘
                                                                 ↓ YES
                                                        intersection_synthesis
                                                                 ↓
                                                         latex_generation
                                                                 ↓
                                                         pdf_compilation
                                                                 ↓
                                                        quality_assurance
                                                                 ↓
                                                        approval_decision
                                                                 ↓
                                                     ┌───────────┴───────────┐
                                                     │                       │
                                                [APPROVED]              [REJECTED]
                                                     │                       │
                                                    END                 pdf_revision
                                                                             ↓
                                                                      (loop to compilation)
    """

    workflow = StateGraph(DebateState)

    # ───────────────────────────────────────────────────────
    # Add all nodes (wrapped to return dict)
    # ───────────────────────────────────────────────────────

    # Original debate nodes (Faz 1-2, 5)
    workflow.add_node("grounding", wrap_node(phase_1_grounding))
    workflow.add_node("parallel_drafting", wrap_node(phase_2_parallel_drafting_sync))

    # NEW: Iterative debate (replaces phase 3+4)
    workflow.add_node("iterative_debate", wrap_node(run_debate_loop))

    workflow.add_node("intersection_synthesis", wrap_node(phase_5_intersection_synthesis))

    # PDF generation nodes
    workflow.add_node("latex_generation", wrap_node(latex_generation_node))
    workflow.add_node("pdf_compilation", wrap_node(pdf_compilation_node))
    workflow.add_node("quality_assurance", wrap_node(quality_assurance_node))
    workflow.add_node("approval_decision", wrap_node(approval_decision_node))
    workflow.add_node("pdf_revision", wrap_node(pdf_revision_node))

    # ───────────────────────────────────────────────────────
    # Add sequential edges
    # ───────────────────────────────────────────────────────

    workflow.add_edge("grounding", "parallel_drafting")
    workflow.add_edge("parallel_drafting", "iterative_debate")
    workflow.add_edge("iterative_debate", "intersection_synthesis")

    # Consensus → LaTeX → PDF pipeline
    workflow.add_edge("intersection_synthesis", "latex_generation")
    workflow.add_edge("latex_generation", "pdf_compilation")
    workflow.add_edge("pdf_compilation", "quality_assurance")
    workflow.add_edge("quality_assurance", "approval_decision")

    # Revision loop
    workflow.add_edge("pdf_revision", "latex_generation")

    # ───────────────────────────────────────────────────────
    # Add conditional edges (loops)
    # ───────────────────────────────────────────────────────

    # NOTE: Debate loop is now INTERNAL to iterative_debate node
    # No conditional edge needed - it handles convergence internally

    # LOOP 2: PDF regeneration loop
    def should_regenerate_pdf(state: DebateState) -> Literal["pdf_revision", "end"]:
        if state.pdf_approved:
            return "end"
        else:
            # Check if we can regenerate
            if state.pdf_regeneration_count < config.MAX_PDF_REGENERATIONS:
                return "pdf_revision"
            else:
                # Max regenerations reached, end anyway
                logger.warning(f"Max PDF regenerations ({config.MAX_PDF_REGENERATIONS}) reached")
                return "end"

    workflow.add_conditional_edges(
        "approval_decision",
        should_regenerate_pdf,
        {
            "pdf_revision": "pdf_revision",
            "end": END
        }
    )

    # ───────────────────────────────────────────────────────
    # Set entry point
    # ───────────────────────────────────────────────────────

    workflow.set_entry_point("grounding")

    return workflow.compile()


# ═══════════════════════════════════════════════════════════
# EXECUTION FUNCTION
# ═══════════════════════════════════════════════════════════

def run_research(
    topic: str,
    research_mode: str = "auto",
    max_rounds: int = None,
    convergence_threshold: float = None
) -> DebateState:
    """
    Main entry point for research pipeline

    Args:
        topic: Research question
        research_mode: "offline", "internet", or "auto"
        max_rounds: Max debate rounds (default: from config)
        convergence_threshold: Similarity threshold (default: from config)

    Returns:
        Final state with PDF path and statistics
    """

    # Use config defaults if not specified
    if max_rounds is None:
        max_rounds = config.MAX_ROUNDS
    if convergence_threshold is None:
        convergence_threshold = config.CONVERGENCE_THRESHOLD

    # Initialize state
    initial_state = DebateState(
        topic=topic,
        research_mode=research_mode,
        max_rounds=max_rounds,
        convergence_threshold=convergence_threshold,
        start_time=datetime.now()
    )

    # Build workflow
    workflow = build_research_workflow()

    logger.info("="*60)
    logger.info(f"🚀 Starting Research & Publishing Pipeline")
    logger.info(f"   Topic: {topic}")
    logger.info(f"   Mode: {research_mode}")
    logger.info(f"   Max Rounds: {max_rounds}")
    logger.info(f"   Threshold: {convergence_threshold:.1%}")
    logger.info("="*60)

    # Execute workflow
    try:
        # LangGraph expects dict input, not Pydantic model
        final_state_dict = workflow.invoke(initial_state.model_dump())

        # Convert back to DebateState for return
        final_state = DebateState(**final_state_dict)

        # Finalize
        final_state.end_time = datetime.now()
        duration = final_state.get_duration()

        logger.info("="*60)
        logger.info(f"✅ Pipeline Complete in {duration:.1f}s")
        logger.info(f"   PDF: {final_state.pdf_path}")
        logger.info(f"   QA Score: {final_state.average_qa_score:.1f}/100")
        logger.info(f"   Debate Rounds: {final_state.iteration_counter}")
        logger.info(f"   Consensus: {final_state.similarity_score:.1%}")
        logger.info(f"   Approved: {'✅' if final_state.pdf_approved else '❌'}")
        if final_state.errors:
            logger.warning(f"   Errors: {len(final_state.errors)}")
        logger.info("="*60)

        return final_state

    except Exception as e:
        logger.critical(f"Pipeline failed: {e}")
        raise


# ═══════════════════════════════════════════════════════════
# LOGGING SETUP
# ═══════════════════════════════════════════════════════════

def setup_logging(log_file: str = None):
    """
    Configure logging for the application

    Args:
        log_file: Optional log file path
    """

    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    handlers = [logging.StreamHandler()]

    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=handlers
    )

    # Suppress verbose libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
