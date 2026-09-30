"""
Phase 3+4 Fusion: Iterative Comparative Debate

True iterative debate where agents see each other's revisions,
lock high-confidence agreements round by round, and converge
on a 4-metric consensus check.
"""

import json
import logging
from typing import Tuple, List, Optional

from src.schemas import DebateState, DebateRound, ComparisonClaim, LockedClaim
from src.api_clients import call_claude_api, call_gemini_api
from src.prompts import (
    PROMPT_COMPARISON_HANDSHAKE,
    SYSTEM_PROMPT_GEMINI_EXPLORER,
    SYSTEM_PROMPT_CLAUDE_JUDGE
)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════

def get_progressive_confidence_threshold(round_num: int) -> float:
    """
    Progressive confidence threshold system (SOTA)

    Round 1: 0.70 - Accept moderate confidence agreements
    Round 2: 0.80 - Raise the bar for locking
    Round 3+: 0.85 - Only lock very confident agreements

    This ensures monotonic convergence without aggressive challenging
    """
    if round_num == 1:
        return 0.70
    elif round_num == 2:
        return 0.80
    else:
        return 0.85


def get_collaborative_instruction(round_num: int, locked_count: int) -> str:
    """
    Get collaborative instruction for agents

    Round 1: Neutral comparison
    Round 2+: Collaborative convergence (respect locked claims)
    """
    if round_num == 1:
        return ""  # Neutral first round
    else:
        return f"""
═══════════════════════════════════════════════════════════
🤝 COLLABORATIVE CONVERGENCE MODE
═══════════════════════════════════════════════════════════

This round, focus on constructive agreement:
- ✅ RESPECT all {locked_count} locked claims from previous rounds
- 🎯 FOCUS on disputed/partial claims only
- 🔍 Be HONEST: mark "conflict" only if evidence genuinely contradicts
- 🤝 Be CONSTRUCTIVE: find common ground where evidence allows
- 📊 Be RIGOROUS: require adequate evidence for "agree" status
- 🎓 Goal: Converge on truth through evidence, not forced consensus

Quality standards for locking (Round {round_num} threshold: {get_progressive_confidence_threshold(round_num):.0%}):
- Both agents must mark "agree"
- Both confidence ≥ {get_progressive_confidence_threshold(round_num):.0%}
- Evidence must support the claim

═══════════════════════════════════════════════════════════
"""


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
    collaborative_instruction: str
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
        collaborative_instruction=collaborative_instruction
    )


def parse_comparison_response(response_text: str) -> dict:
    """
    Parse LLM response into structured comparison data

    Expected format:
    ```json
    {...}
    ```
    === REVISED ANSWER ===
    [text]
    === END ===
    """
    try:
        import re

        # Extract JSON block
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            json_text = response_text[json_start:json_end].strip()
        else:
            # Fallback: try to find JSON object (with nested braces support)
            # Match from first { to last } that contains "comparison_table"
            if '"comparison_table"' in response_text:
                start_idx = response_text.find('{')
                end_idx = response_text.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    json_text = response_text[start_idx:end_idx+1]
                else:
                    json_text = response_text
            else:
                json_text = response_text

        # Clean common JSON errors before parsing
        json_text = json_text.replace(',]', ']')  # Remove trailing commas in arrays
        json_text = json_text.replace(',}', '}')  # Remove trailing commas in objects

        data = json.loads(json_text)

        # Extract revised answer from text section (after JSON)
        if "=== REVISED ANSWER ===" in response_text:
            answer_start = response_text.find("=== REVISED ANSWER ===") + 22
            answer_end = response_text.find("=== END ===", answer_start)
            if answer_end == -1:
                revised_answer = response_text[answer_start:].strip()
            else:
                revised_answer = response_text[answer_start:answer_end].strip()
        else:
            # Fallback: use part after JSON
            revised_answer = response_text[json_end+3:].strip() if "```" in response_text else response_text

        # Add revised_answer to data
        data["revised_answer"] = revised_answer

        # Validate required fields
        required = ["consensus_score", "revised_answer", "convergence_status"]
        for field in required:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")

        # Set defaults for optional fields
        if "comparison_table" not in data:
            data["comparison_table"] = []
        if "new_agreements" not in data:
            data["new_agreements"] = []
        if "still_disputed" not in data:
            data["still_disputed"] = []
        if "total_claims" not in data:
            data["total_claims"] = 0
        if "agreed_claims" not in data:
            data["agreed_claims"] = 0

        return data

    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        logger.debug(f"Failed JSON text: {response_text[:1000]}...")

        # Log the problematic JSON to help debug
        logger.debug(f"Full response (first 2000 chars): {response_text[:2000]}")

        # Try to extract at least the revised_answer and consensus_score
        # using regex as fallback
        revised_answer = response_text
        consensus_score = 0.5

        # Try to extract consensus_score from text - multiple patterns
        import re

        # Pattern 1: "consensus_score": 0.75 or "consensus_score": 75
        consensus_match = re.search(r'"consensus_score":\s*(\d+\.?\d*)', response_text)
        if not consensus_match:
            # Pattern 2: consensus: 75% or consensus score: 0.75
            consensus_match = re.search(r'consensus[:\s]+(\d+\.?\d*)%?', response_text, re.IGNORECASE)
        if not consensus_match:
            # Pattern 3: Average consensus or Avg consensus
            consensus_match = re.search(r'(?:avg|average)\s+consensus[:\s]+(\d+\.?\d*)%?', response_text, re.IGNORECASE)

        if consensus_match:
            try:
                raw_score = float(consensus_match.group(1))
                # If score > 1, it's percentage format (e.g., 47 means 47%)
                if raw_score > 1.0:
                    consensus_score = raw_score / 100.0
                else:
                    consensus_score = raw_score
                # Clamp to valid range
                consensus_score = max(0.0, min(1.0, consensus_score))
            except:
                pass

        # Try to extract revised_answer from text section
        if "=== REVISED ANSWER ===" in response_text:
            answer_start = response_text.find("=== REVISED ANSWER ===") + 22
            answer_end = response_text.find("=== END ===", answer_start)
            if answer_end == -1:
                revised_answer = response_text[answer_start:].strip()
            else:
                revised_answer = response_text[answer_start:answer_end].strip()
        else:
            # Try to extract revised_answer from JSON if present
            answer_match = re.search(r'"revised_answer":\s*"(.*?)"(?=\s*[,}])', response_text, re.DOTALL)
            if answer_match:
                revised_answer = answer_match.group(1)
            else:
                revised_answer = response_text

        if consensus_score == 0.5:
            logger.warning(f"Using fallback parsing: consensus={consensus_score:.1%} (default, no score found)")
        else:
            logger.warning(f"Using fallback parsing: consensus={consensus_score:.1%} (extracted from text)")

        return {
            "comparison_table": [],
            "consensus_score": consensus_score,
            "total_claims": 0,
            "agreed_claims": 0,
            "disputed_claims": 0,
            "new_agreements": [],
            "still_disputed": ["JSON parse error - partial data"],
            "revised_answer": revised_answer,
            "convergence_status": "continue",
            "next_focus": "Fix JSON formatting"
        }

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
    Calculate confidence-weighted consensus score (individual perspective)

    Not all agreements are equal:
    - High confidence agreement (0.9, 0.9) = strong
    - Low confidence agreement (0.4, 0.5) = weak

    This is an asymmetric metric - each agent uses their own claim base
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


def calculate_symmetric_consensus(
    gemini_table: List[dict],
    claude_table: List[dict]
) -> float:
    """
    Calculate symmetric consensus - both agents see same score

    Only counts claims that BOTH agents evaluated (intersection)
    This ensures mathematical consistency and prevents confusion

    Returns:
        Consensus score (0.0-1.0) based on intersection of claims
    """
    if not gemini_table or not claude_table:
        return 0.0

    total_weight = 0.0
    agreed_weight = 0.0

    # Match claims by ID (intersection approach)
    for g_claim in gemini_table:
        claim_id = g_claim.get("claim_id")
        c_claim = next((c for c in claude_table if c.get("claim_id") == claim_id), None)

        if not c_claim:
            continue  # Skip if not in both tables

        # Both agents evaluated this claim
        g_conf = g_claim.get("your_confidence", 0.5)
        c_conf = c_claim.get("other_confidence", 0.5)
        avg_conf = (g_conf + c_conf) / 2

        total_weight += 1.0

        # Check status from BOTH perspectives
        g_status = g_claim.get("status")
        c_status = c_claim.get("status")

        if g_status == "agree" and c_status == "agree":
            # Full agreement
            agreed_weight += avg_conf
        elif g_status == "partial" or c_status == "partial":
            # At least one sees partial agreement
            agreed_weight += (avg_conf * 0.5)
        # conflict = 0

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

    SOTA: Progressive confidence threshold system
    - Round 1: threshold = 0.70 (more claims locked early)
    - Round 2: threshold = 0.80 (higher bar)
    - Round 3+: threshold = 0.85 (only very confident claims)

    Locking criteria:
    - Both agents marked as "agree"
    - Both confidence >= progressive_threshold
    - Statement is semantically same
    """
    lockable = []

    # Get progressive threshold for this round
    threshold = get_progressive_confidence_threshold(round_num)

    logger.debug(f"  Locking threshold for Round {round_num}: {threshold:.0%}")

    # Match claims by ID (assumes both tables have same structure)
    for g_claim in gemini_table:
        claim_id = g_claim.get("claim_id")

        # Find matching claim in Claude's table
        c_claim = next((c for c in claude_table if c.get("claim_id") == claim_id), None)

        if not c_claim:
            continue

        # Check locking criteria with progressive threshold
        gemini_conf = g_claim.get("your_confidence", 0)
        claude_conf = c_claim.get("other_confidence", 0)

        if (g_claim.get("status") == "agree" and
            c_claim.get("status") == "agree" and
            gemini_conf >= threshold and
            claude_conf >= threshold):

            # Lock this claim
            locked = LockedClaim(
                statement=g_claim.get("resolution", ""),
                source_gemini=g_claim.get("your_source"),
                source_claude=c_claim.get("your_source"),
                locked_round=round_num,
                confidence_avg=(gemini_conf + claude_conf) / 2
            )
            lockable.append(locked)
            logger.debug(f"    ✓ Locked: {locked.statement[:80]}... (conf: {locked.confidence_avg:.2f})")

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

    # Get collaborative instruction (round 1 neutral, round 2+ convergence mode)
    locked_count = len(state.locked_agreements)
    collaborative_instruction = get_collaborative_instruction(round_num, locked_count)

    logger.info(f"  Progressive threshold: {get_progressive_confidence_threshold(round_num):.0%}")
    logger.info(f"  Mode: {'Neutral comparison' if round_num == 1 else 'Collaborative convergence'}")

    # Build prompts for both agents (same instruction for both - no alternating roles)
    gemini_prompt = build_handshake_prompt(
        agent_name="Gemini (Explorer)",
        topic=state.topic,
        shared_context=state.shared_context,
        own_previous=gemini_prev,
        other_previous=claude_prev,
        locked_agreements=state.locked_agreements,
        disputed_points=state.current_disputed_points,
        round_num=round_num,
        collaborative_instruction=collaborative_instruction
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
        collaborative_instruction=collaborative_instruction
    )

    # Call both agents in parallel using threading
    logger.info("  → Gemini and Claude comparing and revising in parallel...")

    import concurrent.futures

    def call_gemini():
        return call_gemini_api(
            prompt=gemini_prompt,
            system_prompt=SYSTEM_PROMPT_GEMINI_EXPLORER
        )

    def call_claude():
        return call_claude_api(
            prompt=claude_prompt,
            system_prompt=SYSTEM_PROMPT_CLAUDE_JUDGE
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_gemini = executor.submit(call_gemini)
        future_claude = executor.submit(call_claude)

        gemini_response = future_gemini.result()
        claude_response = future_claude.result()

    logger.info("  → Both agents completed")

    # Parse responses
    logger.debug(f"Gemini response preview: {gemini_response[:500]}...")
    gemini_data = parse_comparison_response(gemini_response)

    logger.debug(f"Claude response preview: {claude_response[:500]}...")
    claude_data = parse_comparison_response(claude_response)

    # ═══════════════════════════════════════════════════════════
    # HYBRID CONSENSUS CALCULATION (4 METRICS)
    # ═══════════════════════════════════════════════════════════
    # We calculate BOTH symmetric and asymmetric metrics:
    # 1. Symmetric Consensus (intersection-based, official metric for convergence)
    # 2. Gemini Coverage (asymmetric, diagnostic)
    # 3. Claude Coverage (asymmetric, diagnostic)
    # 4. Average Coverage (asymmetric average)
    #
    # ALL 4 METRICS must reach threshold for convergence
    # ═══════════════════════════════════════════════════════════

    # Calculate asymmetric coverage (individual perspectives)
    if gemini_data.get("comparison_table"):
        gemini_coverage = calculate_weighted_consensus(gemini_data["comparison_table"])
        logger.debug(f"  Gemini: Calculated coverage from {len(gemini_data['comparison_table'])} claims")
    else:
        # Use regex-extracted consensus_score from fallback parsing
        gemini_coverage = gemini_data.get("consensus_score", 0.5)
        if gemini_coverage == 0.0:
            logger.error(f"  ⚠️ Gemini coverage is 0.0% - likely parse failure!")
        logger.warning(f"  Using fallback Gemini coverage: {gemini_coverage:.1%} (JSON parse failed)")

    if claude_data.get("comparison_table"):
        claude_coverage = calculate_weighted_consensus(claude_data["comparison_table"])
        logger.debug(f"  Claude: Calculated coverage from {len(claude_data['comparison_table'])} claims")
    else:
        # Use regex-extracted consensus_score from fallback parsing
        claude_coverage = claude_data.get("consensus_score", 0.5)
        if claude_coverage == 0.0:
            logger.error(f"  ⚠️ Claude coverage is 0.0% - likely parse failure!")
        logger.warning(f"  Using fallback Claude coverage: {claude_coverage:.1%} (JSON parse failed)")

    # Calculate symmetric consensus (intersection-based, official metric)
    if gemini_data.get("comparison_table") and claude_data.get("comparison_table"):
        gemini_table = gemini_data["comparison_table"]
        claude_table = claude_data["comparison_table"]

        # Debug: Check intersection size
        gemini_ids = set(c.get("claim_id") for c in gemini_table)
        claude_ids = set(c.get("claim_id") for c in claude_table)
        intersection_ids = gemini_ids & claude_ids

        logger.debug(f"  Claim matching: Gemini {len(gemini_ids)} claims, Claude {len(claude_ids)} claims, Intersection {len(intersection_ids)} claims")

        symmetric_consensus = calculate_symmetric_consensus(gemini_table, claude_table)
        logger.debug(f"  Symmetric consensus calculated from intersection")
    else:
        # Fallback: average of individual scores if JSON parse failed
        symmetric_consensus = (gemini_coverage + claude_coverage) / 2
        logger.warning(f"  Using fallback symmetric consensus (average): {symmetric_consensus:.1%}")

    # Calculate average coverage (for comparison)
    avg_coverage = (gemini_coverage + claude_coverage) / 2

    # ═══════════════════════════════════════════════════════════
    # LOG ALL 4 METRICS
    # ═══════════════════════════════════════════════════════════
    logger.info(f"  📊 METRICS (4-way consensus):")
    logger.info(f"     • Symmetric: {symmetric_consensus:.1%} (intersection-based)")
    logger.info(f"     • Gemini Coverage: {gemini_coverage:.1%} (asymmetric)")
    logger.info(f"     • Claude Coverage: {claude_coverage:.1%} (asymmetric)")
    logger.info(f"     • Average Coverage: {avg_coverage:.1%} (asymmetric avg)")

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

    # ═══════════════════════════════════════════════════════════
    # 4-WAY CONVERGENCE CHECK
    # ═══════════════════════════════════════════════════════════
    # ALL 4 metrics must reach threshold for true convergence:
    # 1. Symmetric consensus >= threshold
    # 2. Gemini coverage >= threshold
    # 3. Claude coverage >= threshold
    # 4. Average coverage >= threshold
    # ═══════════════════════════════════════════════════════════
    convergence_threshold = state.convergence_threshold

    # Check each metric individually
    symmetric_ok = symmetric_consensus >= convergence_threshold
    gemini_ok = gemini_coverage >= convergence_threshold
    claude_ok = claude_coverage >= convergence_threshold
    avg_ok = avg_coverage >= convergence_threshold

    # ALL 4 must pass
    converged = symmetric_ok and gemini_ok and claude_ok and avg_ok

    # Log which metrics passed/failed
    logger.info(f"  🎯 Convergence Check (threshold: {convergence_threshold:.0%}):")
    logger.info(f"     {'✅' if symmetric_ok else '❌'} Symmetric: {symmetric_consensus:.1%}")
    logger.info(f"     {'✅' if gemini_ok else '❌'} Gemini Coverage: {gemini_coverage:.1%}")
    logger.info(f"     {'✅' if claude_ok else '❌'} Claude Coverage: {claude_coverage:.1%}")
    logger.info(f"     {'✅' if avg_ok else '❌'} Average Coverage: {avg_coverage:.1%}")

    # Collect new agreements (combine LLM-reported + locked claims)
    llm_agreements = gemini_data.get("new_agreements", []) + claude_data.get("new_agreements", [])
    locked_agreements = [claim.statement for claim in new_locked]  # Extract statements from locked claims
    all_new_agreements = llm_agreements + locked_agreements

    # Create DebateRound record
    # Store symmetric consensus as primary metric
    debate_round = DebateRound(
        round_num=round_num,
        gemini_answer=gemini_data.get("revised_answer", ""),
        claude_answer=claude_data.get("revised_answer", ""),
        comparison_table=[],  # Could store full table but it's large
        consensus_score=symmetric_consensus,  # Use symmetric as official metric
        new_agreements=all_new_agreements,
        disputed_points=disputed,
        convergence_status="converged" if converged else "continue",
        next_focus=gemini_data.get("next_focus", "") or claude_data.get("next_focus", "")
    )

    # Add to state
    state.add_debate_round(debate_round)

    # Log result with 4-metric summary
    if converged:
        logger.info(f"✅ CONVERGED - All 4 metrics >= {convergence_threshold:.0%}")
    else:
        # Find lowest metric for gap reporting
        min_metric = min(symmetric_consensus, gemini_coverage, claude_coverage, avg_coverage)
        gap = convergence_threshold - min_metric
        logger.info(f"🔄 Debate continues (Lowest metric: {min_metric:.1%}, Gap: {gap:.1%})")

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
