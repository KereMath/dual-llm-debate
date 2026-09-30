"""
Phase 2: Parallel Drafting
Both agents draft independently (zero contamination)
"""

import logging
import asyncio

from ..schemas import DebateState
from ..api_clients import call_gemini_async, call_claude_async
from ..prompts import SYSTEM_PROMPT_GEMINI_EXPLORER, SYSTEM_PROMPT_CLAUDE_JUDGE

logger = logging.getLogger(__name__)


async def phase_2_parallel_drafting(state: DebateState) -> DebateState:
    """
    Faz 2: Parallel Drafting (İzolasyon İçinde Taslak)

    AMAÇ: "Bias" (Önyargı) izolasyonu sağlamak
    - Agent A ve Agent B birbirinden BAĞIMSIZ çalışır
    - İkisi de aynı shared_context'i kullanır
    - Biri diğerinin çıktısını görmez (zero contamination)

    Process: Her iki ajan da soruyu bağımsız cevaplar
    Output: state.gemini_draft ve state.claude_draft
    """

    logger.info("Faz 2: Parallel Drafting (Isolation Mode)")

    if not state.shared_context:
        raise ValueError("Cannot draft without grounding (shared_context)")

    # Prepare prompt (same for both)
    context_prompt = f"""Araştırma Sorusu: {state.topic}

Web Kaynaklarından Elde Edilen Bilgiler (Değişmez Gerçek):
{state.shared_context}

Görev:
- Soruyu bu kaynaklara dayanarak cevapla
- Her iddia için [Source: <detay>] formatında kaynak belirt
- Kapsamlı ol ama sadece kaynaklarda olanı yaz
- Speküle etme, kendi bilgini kullanma

Cevabını yaz:"""

    # Execute in parallel (asyncio)
    try:
        gemini_task = asyncio.create_task(
            call_gemini_async(context_prompt, SYSTEM_PROMPT_GEMINI_EXPLORER)
        )

        claude_task = asyncio.create_task(
            call_claude_async(context_prompt, SYSTEM_PROMPT_CLAUDE_JUDGE)
        )

        # Await both
        gemini_draft, claude_draft = await asyncio.gather(
            gemini_task,
            claude_task,
            return_exceptions=True
        )

        # A debate needs BOTH drafts. Continuing with an error placeholder
        # would make the whole pipeline debate against an error message,
        # so a failed draft fails the run explicitly.
        failures = []
        if isinstance(gemini_draft, Exception):
            logger.error(f"Gemini draft failed: {gemini_draft}")
            state.add_error(f"Gemini draft error: {gemini_draft}")
            failures.append(f"Gemini: {gemini_draft}")
        if isinstance(claude_draft, Exception):
            logger.error(f"Claude draft failed: {claude_draft}")
            state.add_error(f"Claude draft error: {claude_draft}")
            failures.append(f"Claude: {claude_draft}")
        if failures:
            raise RuntimeError(
                "Parallel drafting failed - cannot run a debate without both drafts. "
                + " | ".join(failures)
            )

        # Update state
        state.gemini_draft = gemini_draft
        state.claude_draft = claude_draft
        state.iteration_counter = 0  # Initialize counter

        logger.info(f"✅ Parallel drafts complete")
        logger.info(f"   Explorer (Gemini): {len(gemini_draft)} chars")
        logger.info(f"   Judge (Claude): {len(claude_draft)} chars")

        return state

    except Exception as e:
        logger.critical(f"Parallel drafting failed: {e}")
        state.add_error(f"Critical drafting error: {str(e)}")
        raise


def phase_2_parallel_drafting_sync(state: DebateState) -> DebateState:
    """
    Synchronous wrapper for LangGraph compatibility
    LangGraph nodes must be sync functions
    """
    # Run async function in sync context
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(phase_2_parallel_drafting(state))
    finally:
        loop.close()
