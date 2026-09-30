"""
Phase 5: Intersection Synthesis (A ∩ B)
Distill the debate's output — locked claims + final revised answers — into a consensus report
"""

import logging
from typing import List

from ..schemas import DebateState, LockedClaim
from ..api_clients import call_claude_api
from ..prompts import (
    SYSTEM_PROMPT_SYNTHESIZER,
    PROMPT_CONSENSUS_EXTRACTION,
    report_language_instruction,
)

logger = logging.getLogger(__name__)


def format_locked_claims_for_synthesis(locked: List[LockedClaim]) -> str:
    """Format locked claims (with sources and confidence) for the synthesizer prompt"""
    if not locked:
        return "(Debate hiç iddia kilitleyemedi - sentez yalnızca revize cevapların kesişiminden yapılacak.)"

    lines = []
    for i, claim in enumerate(locked, 1):
        sources = []
        if claim.source_gemini:
            sources.append(claim.source_gemini)
        if claim.source_claude and claim.source_claude != claim.source_gemini:
            sources.append(claim.source_claude)
        source_str = f" [Source: {'; '.join(sources)}]" if sources else ""
        lines.append(
            f"{i}. {claim.statement}{source_str} "
            f"(Tur {claim.locked_round}, güven: {claim.confidence_avg:.2f})"
        )
        # Surface each agent's own wording when it differs from the
        # canonical statement - a narrowed/qualified version is a nuance
        # the referee must respect, not overwrite
        canonical = claim.statement.strip().lower()
        for label, wording in (("Gemini", claim.resolution_gemini),
                               ("Claude", claim.resolution_claude)):
            if wording and wording.strip().lower() != canonical:
                lines.append(f"   ({label} ifadesi: {wording.strip()})")

    return "\n".join(lines)


def format_disputed_points_for_synthesis(disputed: List[str]) -> str:
    """Format still-disputed points for the synthesizer prompt"""
    if not disputed:
        return "(Yok - tartışmalı nokta kalmadı.)"

    return "\n".join(f"- {point}" for point in disputed)


def phase_5_intersection_synthesis(state: DebateState) -> DebateState:
    """
    Faz 5: Intersection Synthesis (Hakem Kararı)

    MATHEMATICAL TRUTH: Truth = A ∩ B

    The referee is fed the DEBATE'S OUTPUT, not the pre-debate drafts:
    1. Locked claims (both agents agreed above the per-round confidence
       threshold) form the backbone of the report — all must be included
    2. Each agent's FINAL revised answer from the last debate round is the
       source for any additional intersection claims
    3. Still-disputed points are explicitly excluded

    Philosophy: "Şüphe varsa çıkar"
    """

    logger.info("Faz 5: Intersection Synthesis (Hakem Kararı)")

    # Feed the debate's output: final revised answers (fall back to the
    # phase-2 drafts only if no debate round was recorded)
    gemini_final = state.get_latest_gemini_answer()
    claude_final = state.get_latest_claude_answer()

    locked_claims_block = format_locked_claims_for_synthesis(state.locked_agreements)
    disputed_block = format_disputed_points_for_synthesis(state.current_disputed_points)

    logger.info(f"   Feeding synthesizer: {len(state.locked_agreements)} locked claims, "
                f"{len(state.current_disputed_points)} disputed points, "
                f"final answers from round {state.iteration_counter}")

    consensus_prompt = PROMPT_CONSENSUS_EXTRACTION.format(
        topic=state.topic,
        shared_context=state.shared_context,
        locked_claims=locked_claims_block,
        disputed_points=disputed_block,
        gemini_final=gemini_final,
        claude_final=claude_final,
        iteration_counter=state.iteration_counter,
        language_instruction=report_language_instruction(state.report_language)
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
        # Explicit failure flag: the pipeline may still compile the degraded
        # report below for inspection, but the run must never end "approved"
        state.synthesis_failed = True

        # Fallback: report built from the locked claims (already dual-verified),
        # clearly marked as a degraded result
        state.consensus_report = f"""# Konsensus Raporu (Sentez Hatası - Kısıtlı Rapor)

## Araştırma Sorusu
{state.topic}

## Hata
Hakem sentezi başarısız oldu: {str(e)}

Aşağıdaki iddialar debate sırasında her iki ajan tarafından da onaylanıp
kilitlendi; hakem sentezi yapılamadığı için ham halleriyle listeleniyor.

## Kilitli İddialar (Çift Taraflı Doğrulanmış)
{locked_claims_block}
"""

        return state
