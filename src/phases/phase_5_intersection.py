"""
Phase 5: Intersection Synthesis (A ∩ B)
Extract only mutually agreed claims
"""

import logging

from ..schemas import DebateState
from ..api_clients import call_claude_api
from ..prompts import SYSTEM_PROMPT_SYNTHESIZER, PROMPT_CONSENSUS_EXTRACTION

logger = logging.getLogger(__name__)


def phase_5_intersection_synthesis(state: DebateState) -> DebateState:
    """
    Faz 5: Intersection Synthesis (Hakem Kararı)

    MATHEMATICAL TRUTH: Truth = A ∩ B

    Algorithm:
    1. İki taslağı karşılaştır
    2. SADECE her ikisinin de kesinlikle kabul ettiği iddiaları al
    3. Bir tarafın şüphe duyduğu, reddettiği veya bahsetmediği
       her türlü bilgiyi SİL
    4. Sonuç: %100 doğrulanmış "Saf Bilgi"

    Philosophy: "Şüphe varsa çıkar"
    """

    logger.info("Faz 5: Intersection Synthesis (Hakem Kararı)")

    consensus_prompt = PROMPT_CONSENSUS_EXTRACTION.format(
        topic=state.topic,
        shared_context=state.shared_context,
        gemini_draft=state.gemini_draft,
        claude_draft=state.claude_draft,
        iteration_counter=state.iteration_counter,
        similarity_score=state.similarity_score,
        forced_stop=state.forced_stop
    )

    try:
        consensus_text = call_claude_api(
            prompt=consensus_prompt,
            system_prompt=SYSTEM_PROMPT_SYNTHESIZER,
            temperature=0.2,
            max_tokens=4000
        )

        state.consensus_report = consensus_text

        logger.info(f"✅ Intersection synthesis complete")
        logger.info(f"   Report length: {len(consensus_text)} chars")

        return state

    except Exception as e:
        logger.error(f"Consensus extraction failed: {e}")
        state.add_error(f"Consensus error: {str(e)}")

        # Fallback: Minimal report
        state.consensus_report = f"""# Konsensus Raporu (Hata)

## Araştırma Sorusu
{state.topic}

## Hata
Konsensus çıkarma başarısız: {str(e)}

## Agent Taslakları
Agent A: {len(state.gemini_draft)} chars
Agent B: {len(state.claude_draft)} chars
"""

        return state
