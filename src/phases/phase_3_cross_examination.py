"""
Phase 3: Cross-Examination
Ruthless critique between agents
"""

import logging

from ..schemas import DebateState
from ..api_clients import call_gemini_api, call_claude_api
from ..prompts import (
    SYSTEM_PROMPT_GEMINI_EXPLORER,
    SYSTEM_PROMPT_CLAUDE_JUDGE,
    PROMPT_TEMPLATE_CRITIQUE
)

logger = logging.getLogger(__name__)


def phase_3_cross_examination(state: DebateState) -> DebateState:
    """
    Faz 3: Cross-Examination (Çapraz Sorgu)

    PHILOSOPHY: "Nezaket değil, Acımasızlık"
    - Her ajan diğerinin taslağını SERT eleştirir
    - Zayıf kanıt, mantık hatası, spekülatif iddia → Acımasızca işaretle
    - Amaç: Karşılıklı eleştiri ile kaliteyi artırmak

    Logic:
    - Agent A (Explorer), Agent B'nin (Judge) taslağını okur:
      "Senin şu iddian kaynaklarda yok, kanıtla."
    - Agent B (Judge), Agent A'nın (Explorer) taslağını okur:
      "Bu mantık zinciri hatalı, şurayı düzelt."

    Process: Her ajan critique + revised_answer üretir
    Output: state.gemini_critique, state.claude_critique
           state.gemini_draft (updated), state.claude_draft (updated)
    """

    state.iteration_counter += 1
    logger.info(f"Faz 3: Cross-Examination (Round {state.iteration_counter})")

    # Gemini critiques Claude
    gemini_critique_prompt = PROMPT_TEMPLATE_CRITIQUE.format(
        other_agent_draft=state.claude_draft,
        web_context=state.shared_context,
        own_draft=state.gemini_draft
    )

    # Claude critiques Gemini
    claude_critique_prompt = PROMPT_TEMPLATE_CRITIQUE.format(
        other_agent_draft=state.gemini_draft,
        web_context=state.shared_context,
        own_draft=state.claude_draft
    )

    try:
        # Call both agents
        gemini_response = call_gemini_api(
            gemini_critique_prompt,
            SYSTEM_PROMPT_GEMINI_EXPLORER
        )

        claude_response = call_claude_api(
            claude_critique_prompt,
            SYSTEM_PROMPT_CLAUDE_JUDGE
        )

        # Parse responses (CRITIQUE + REVISED_ANSWER)
        gemini_critique, gemini_revised = parse_critique_response(
            gemini_response,
            "Gemini Explorer"
        )

        claude_critique, claude_revised = parse_critique_response(
            claude_response,
            "Claude Judge"
        )

        # Update state
        state.gemini_critique = gemini_critique
        state.claude_critique = claude_critique
        state.gemini_draft = gemini_revised
        state.claude_draft = claude_revised

        logger.info(f"✅ Cross-examination complete (Round {state.iteration_counter})")

        return state

    except Exception as e:
        logger.error(f"Cross-examination failed: {e}")
        state.add_error(f"Round {state.iteration_counter} critique error: {str(e)}")

        # Graceful degradation: Keep previous drafts
        logger.warning("Using previous drafts due to critique failure")
        return state


def parse_critique_response(response: str, agent_name: str) -> tuple[str, str]:
    """
    Parse CRITIQUE + REVISED_ANSWER format

    Expected:
    CRITIQUE:
    ...

    REVISED_ANSWER:
    ...

    Returns: (critique_text, revised_draft)
    """

    try:
        if "CRITIQUE:" in response and "REVISED_ANSWER:" in response:
            parts = response.split("REVISED_ANSWER:", 1)
            critique = parts[0].replace("CRITIQUE:", "").strip()
            revised = parts[1].strip()
            return critique, revised

        elif "CRITIQUE:" in response:
            parts = response.split("CRITIQUE:", 1)
            sections = parts[1].split("\n\n", 1)
            critique = sections[0].strip()
            revised = sections[1].strip() if len(sections) > 1 else response
            return critique, revised

        else:
            logger.warning(f"{agent_name} did not follow format")
            return f"[No structured critique from {agent_name}]", response

    except Exception as e:
        logger.error(f"Parse failure for {agent_name}: {e}")
        return "[Parse error]", response
