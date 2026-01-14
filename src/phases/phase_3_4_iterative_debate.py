"""
Phase 3+4 Fusion: Iterative Comparative Debate (SOTA)

Replaces old phase_3_cross_examination.py + phase_4_convergence.py
with true iterative debate where agents see each other's revisions
"""

import json
import logging
from typing import Tuple, List, Optional

from src.schemas import DebateState, DebateRound, ComparisonClaim, LockedClaim
from src.api_clients import call_claude_api, call_gemini_api
from src.prompts import (
    PROMPT_COMPARISON_HANDSHAKE,
    DEVIL_ADVOCATE_STRICT,
    DEVIL_ADVOCATE_OPEN,
    SYSTEM_PROMPT_GEMINI_EXPLORER,
    SYSTEM_PROMPT_CLAUDE_JUDGE
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════

def assign_devil_advocate_roles(round_num: int) -> dict:
    """
    Alternate devil's advocate role each round

    Round 1: Both neutral
    Round 2: Gemini strict, Claude open
    Round 3: Claude strict, Gemini open
    """
    if round_num == 1:
        return {
            "gemini": "",
            "claude": ""
        }
    elif round_num % 2 == 0:
        return {
            "gemini": DEVIL_ADVOCATE_STRICT,
            "claude": DEVIL_ADVOCATE_OPEN
        }
    else:
        return {
            "gemini": DEVIL_ADVOCATE_OPEN,
            "claude": DEVIL_ADVOCATE_STRICT
        }


def format_locked_agreements(locked: List[LockedClaim]) -> str:
    """Format locked agreements for display"""
    if not locked:
        return "None yet - this is the first comparison."

    result = []
    for claim in locked:
        result.append(f"✓ {claim.statement} (Locked in Round {claim.locked_round}, confidence: {claim.confidence_avg:.2f})")

    return "\n".join(result)


def format_disputed_points(disputed: List[str]) -> str:
    """Format disputed points for display"""
    if not disputed:
        return "None - all points agreed or this is first round."

    result = []
    for i, point in enumerate(disputed, 1):
        result.append(f"✗ {i}. {point}")

    return "\n".join(result)


def build_handshake_prompt(
    agent_name: str,
    topic: str,
    shared_context: str,
    own_previous: str,
    other_previous: str,
    locked_agreements: List[LockedClaim],
    disputed_points: List[str],
    round_num: int,
    devil_advocate_instruction: str
) -> str:
    """Build comparison handshake prompt for agent"""

    prev_round = round_num - 1 if round_num > 1 else 0

    return PROMPT_COMPARISON_HANDSHAKE.format(
        round_num=round_num,
        agent_name=agent_name,
        topic=topic,
        shared_context=shared_context[:5000],  # Truncate if too long
        locked_agreements=format_locked_agreements(locked_agreements),
        prev_round=prev_round,
        own_previous=own_previous,
        other_previous=other_previous,
        disputed_points=format_disputed_points(disputed_points),
        devil_advocate_instruction=devil_advocate_instruction
    )


def parse_comparison_response(response_text: str) -> dict:
    """
    Parse LLM response into structured comparison data

    Expected JSON format from LLM
    """
    try:
        # Try to extract JSON from response
        # LLMs sometimes wrap JSON in markdown code blocks
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        else:
            json_text = response_text

        data = json.loads(json_text)

        # Validate required fields
        required = ["comparison_table", "consensus_score", "revised_answer", "convergence_status"]
        for field in required:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        return data

    except Exception as e:
        logger.error(f"Failed to parse comparison response: {e}")
        logger.debug(f"Response text: {response_text[:500]}...")

        # Return fallback structure
        return {
            "comparison_table": [],
            "consensus_score": 0.5,
            "total_claims": 0,
            "agreed_claims": 0,
            "disputed_claims": 0,
            "new_agreements": [],
            "still_disputed": ["Parse error - using fallback"],
            "revised_answer": response_text,  # Use raw response as answer
            "convergence_status": "continue",
            "next_focus": "Fix JSON parsing"
        }


def calculate_weighted_consensus(comparison_table: List[dict]) -> float:
    """
    Calculate confidence-weighted consensus score

    Not all agreements are equal:
    - High confidence agreement (0.9, 0.9) = strong
    - Low confidence agreement (0.4, 0.5) = weak
    """
    if not comparison_table:
        return 0.0

    total_weight = 0.0
    agreed_weight = 0.0

    for claim in comparison_table:
        # Average confidence as weight
        conf_gemini = claim.get("your_confidence", 0.5)
        conf_claude = claim.get("other_confidence", 0.5)
        avg_conf = (conf_gemini + conf_claude) / 2

        total_weight += 1.0

        if claim.get("status") == "agree":
            # Weight by confidence
            agreed_weight += avg_conf
        elif claim.get("status") == "partial":
            # Partial agreement = half weight
            agreed_weight += (avg_conf * 0.5)
        # "conflict" contributes 0

    if total_weight == 0:
        return 0.0

    return agreed_weight / total_weight


def identify_lockable_claims(
    gemini_table: List[dict],
    claude_table: List[dict],
    round_num: int
) -> List[LockedClaim]:
    """
    Identify claims that can be locked (both agents agree with high confidence)

    Locking criteria:
    - Both agents marked as "agree"
    - Both confidence >= 0.85
    - Statement is semantically same
    """
    lockable = []

    # Match claims by ID (assumes both tables have same structure)
    for g_claim in gemini_table:
        claim_id = g_claim.get("claim_id")

        # Find matching claim in Claude's table
        c_claim = next((c for c in claude_table if c.get("claim_id") == claim_id), None)

        if not c_claim:
            continue

        # Check locking criteria
        if (g_claim.get("status") == "agree" and
            c_claim.get("status") == "agree" and
            g_claim.get("your_confidence", 0) >= 0.85 and
            c_claim.get("other_confidence", 0) >= 0.85):

            # Lock this claim
            locked = LockedClaim(
                statement=g_claim.get("resolution", ""),
                source_gemini=g_claim.get("your_source"),
                source_claude=c_claim.get("your_source"),
                locked_round=round_num,
                confidence_avg=(g_claim.get("your_confidence", 0) + c_claim.get("other_confidence", 0)) / 2
            )
            lockable.append(locked)

    return lockable


# ═══════════════════════════════════════════════════════════
# MAIN ITERATIVE DEBATE FUNCTION
# ═══════════════════════════════════════════════════════════

def run_iterative_debate_round(
    state: DebateState,
    round_num: int
) -> DebateState:
    """
    Run single round of iterative comparative debate

    Both agents:
    1. See each other's previous answers
    2. Compare line-by-line
    3. Calculate consensus
    4. Revise their answers
    5. Report what's agreed/disputed
    """

    logger.info(f"Faz 3+4: Iterative Debate Round {round_num}")

    # Get previous versions
    if round_num == 1:
        # First round: use original drafts
        gemini_prev = state.gemini_draft
        claude_prev = state.claude_draft
    else:
        # Subsequent rounds: use latest from debate history
        gemini_prev = state.get_latest_gemini_answer()
        claude_prev = state.get_latest_claude_answer()

    # Assign devil's advocate roles
    devil_roles = assign_devil_advocate_roles(round_num)

    # Build prompts for both agents
    gemini_prompt = build_handshake_prompt(
        agent_name="Gemini (Explorer)",
        topic=state.topic,
        shared_context=state.shared_context,
        own_previous=gemini_prev,
        other_previous=claude_prev,
        locked_agreements=state.locked_agreements,
        disputed_points=state.current_disputed_points,
        round_num=round_num,
        devil_advocate_instruction=devil_roles["gemini"]
    )

    claude_prompt = build_handshake_prompt(
        agent_name="Claude (Judge)",
        topic=state.topic,
        shared_context=state.shared_context,
        own_previous=claude_prev,
        other_previous=gemini_prev,
        locked_agreements=state.locked_agreements,
        disputed_points=state.current_disputed_points,
        round_num=round_num,
        devil_advocate_instruction=devil_roles["claude"]
    )

    # Call both agents in parallel (async would be better but keeping it simple)
    logger.info("  → Gemini comparing and revising...")
    gemini_response = call_gemini_api(
        prompt=gemini_prompt,
        system_prompt=SYSTEM_PROMPT_GEMINI_EXPLORER
    )

    logger.info("  → Claude comparing and revising...")
    claude_response = call_claude_api(
        prompt=claude_prompt,
        system_prompt=SYSTEM_PROMPT_CLAUDE_JUDGE
    )

    # Parse responses
    gemini_data = parse_comparison_response(gemini_response)
    claude_data = parse_comparison_response(claude_response)

    # Calculate weighted consensus (average of both agents' scores)
    gemini_consensus = calculate_weighted_consensus(gemini_data.get("comparison_table", []))
    claude_consensus = calculate_weighted_consensus(claude_data.get("comparison_table", []))
    avg_consensus = (gemini_consensus + claude_consensus) / 2

    logger.info(f"  Consensus: Gemini {gemini_consensus:.1%}, Claude {claude_consensus:.1%}, Avg {avg_consensus:.1%}")

    # Identify lockable claims (high confidence agreements)
    new_locked = identify_lockable_claims(
        gemini_data.get("comparison_table", []),
        claude_data.get("comparison_table", []),
        round_num
    )

    # Update state with new locks
    state.locked_agreements.extend(new_locked)

    logger.info(f"  New locked claims: {len(new_locked)}")

    # Collect disputed points (union of both agents' disputes)
    disputed = list(set(
        gemini_data.get("still_disputed", []) +
        claude_data.get("still_disputed", [])
    ))
    state.current_disputed_points = disputed

    logger.info(f"  Still disputed: {len(disputed)}")

    # Determine convergence status
    convergence_threshold = state.convergence_threshold
    converged = (
        avg_consensus >= convergence_threshold and
        gemini_data.get("convergence_status") == "converged" and
        claude_data.get("convergence_status") == "converged"
    )

    # Create DebateRound record
    debate_round = DebateRound(
        round_num=round_num,
        gemini_answer=gemini_data.get("revised_answer", ""),
        claude_answer=claude_data.get("revised_answer", ""),
        comparison_table=[],  # Could store full table but it's large
        consensus_score=avg_consensus,
        new_agreements=gemini_data.get("new_agreements", []) + claude_data.get("new_agreements", []),
        disputed_points=disputed,
        convergence_status="converged" if converged else "continue",
        next_focus=gemini_data.get("next_focus", "") or claude_data.get("next_focus", "")
    )

    # Add to state
    state.add_debate_round(debate_round)

    # Log result
    if converged:
        logger.info(f"✅ CONVERGED at {avg_consensus:.1%}")
    else:
        logger.info(f"🔄 Debate continues (Gap: {(convergence_threshold - avg_consensus):.1%})")

    return state


# ═══════════════════════════════════════════════════════════
# CONVERGENCE VISUALIZATION
# ═══════════════════════════════════════════════════════════

def visualize_convergence(state: DebateState):
    """
    Print ASCII visualization of convergence progress
    """
    logger.info("═══════════════════════════════════════════════════")
    logger.info("CONVERGENCE PROGRESSION")
    logger.info("═══════════════════════════════════════════════════")

    for round_data in state.debate_rounds:
        bar_length = 20
        filled = int(bar_length * round_data.consensus_score)
        bar = "█" * filled + "░" * (bar_length - filled)

        logger.info(f"Round {round_data.round_num}: {bar} {round_data.consensus_score:.0%}")
        logger.info(f"  Agreed: {len(round_data.new_agreements)} new claims")
        logger.info(f"  Disputed: {len(round_data.disputed_points)} remaining")

    logger.info(f"\nTotal Locked Claims: {len(state.locked_agreements)}")
    logger.info("═══════════════════════════════════════════════════")


# ═══════════════════════════════════════════════════════════
# EXPORT FOR BACKWARD COMPATIBILITY
# ═══════════════════════════════════════════════════════════

def run_debate_loop(state: DebateState) -> DebateState:
    """
    Run full iterative debate loop until convergence or max rounds

    Replacement for old phase_3 + phase_4 loop
    """

    while state.iteration_counter < state.max_rounds:
        round_num = state.iteration_counter + 1

        # Run debate round
        state = run_iterative_debate_round(state, round_num)

        # Check convergence
        if state.converged:
            logger.info(f"✅ Natural convergence reached at {state.similarity_score:.1%}")
            break

    # Check if forced stop
    if not state.converged:
        logger.warning(f"⚠️ FORCED STOP - Max rounds ({state.max_rounds}) reached")
        logger.warning(f"   Final consensus: {state.similarity_score:.1%} (threshold: {state.convergence_threshold:.1%})")
        state.forced_stop = True

    # Visualize convergence progression
    visualize_convergence(state)

    return state
