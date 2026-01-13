"""
Phase 4: Convergence Check
Determine if debate should continue or terminate
"""

import logging

from ..schemas import DebateState
from ..api_clients import calculate_semantic_similarity

logger = logging.getLogger(__name__)


def phase_4_convergence_check(state: DebateState) -> DebateState:
    """
    Faz 4: Convergence Check

    TERMINATION LOGIC (Sonlandırma Kriterleri):
    1. Doğal Mutabakat: Semantic similarity >= threshold (e.g., 95%)
    2. Zorunlu Bitiş: iteration_counter >= max_rounds (e.g., 3)

    Process: İki taslak arasındaki semantic benzerliği hesapla
    Decision: Devam mı, bitir mi?
    """

    logger.info(f"Faz 4: Convergence Check (Round {state.iteration_counter})")

    try:
        # Calculate semantic similarity (LLM-based)
        similarity = calculate_semantic_similarity(
            state.gemini_draft,
            state.claude_draft
        )

        state.similarity_score = similarity

        logger.info(f"Semantic Similarity: {similarity:.1%}")
        logger.info(f"Threshold: {state.convergence_threshold:.1%}")

        # Check termination conditions
        if similarity >= state.convergence_threshold:
            # Natural consensus
            state.converged = True
            state.forced_stop = False
            logger.info(f"✅ DOĞAL MUTABAKAT (Natural Consensus) at {similarity:.1%}")

        elif state.iteration_counter >= state.max_rounds:
            # Forced stop
            state.converged = True
            state.forced_stop = True
            logger.warning(f"⚠️ ZORUNLU BITIS (Forced Stop) - Max rounds ({state.max_rounds}) reached")

        else:
            # Continue debate
            logger.info(f"🔄 Debate continues (Gap: {state.convergence_threshold - similarity:.1%})")

        return state

    except Exception as e:
        logger.error(f"Convergence check failed: {e}")
        state.add_error(f"Convergence error: {str(e)}")

        # Conservative fallback: Force convergence
        state.converged = True
        state.forced_stop = True
        state.similarity_score = 0.0

        return state
