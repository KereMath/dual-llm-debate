# MASTERPLAN: Dual-LLM Research System - SOTA Implementation Guide

**Date:** 2026-01-14
**Status:** 🔴 CRITICAL ISSUES IDENTIFIED - Requires Major Refactoring
**Goal:** Transform current system into true adversarial iterative debate with %90+ convergence

---

## 📊 Executive Summary

### Current System Status
- **Architecture:** Dual-LLM (Claude Sonnet 4.5 + Gemini 2.5 Pro) Adversarial Debate
- **Pipeline:** 5-Phase (Grounding → Drafting → Cross-Exam → Convergence → Intersection)
- **Critical Issues:** 3 major bugs preventing SOTA performance
- **Convergence Rate:** 🔴 **23%** (stuck, should be 90+%)
- **Academic Integrity:** ✅ Fixed (override added)
- **Methodology Contamination:** ✅ Fixed (prompts cleaned)
- **Google Search Grounding:** ✅ Activated (Gemini 2.5 Pro)

---

## 🚨 Critical Issues Identified

### Issue #1: Convergence System Broken (%23 Stuck)

**Symptoms:**
```
Round 1: Semantic Similarity: 23.0%
Round 2: Semantic Similarity: 23.0%
Round 3: Semantic Similarity: 23.0%
```

**Root Cause:**
1. LLMs do NOT see each other's **revised** answers after Round 1
2. Only 1 cross-examination happens (Round 1), then blind iteration
3. Semantic similarity uses **embedding-based** comparison (passive mathematical calculation)
4. No actual debate happens after Round 1 - just cosmetic loops

**Why It's Stuck at %23:**
- `phase_4_convergence.py` compares `gemini_critique` vs `claude_critique`
- But these critiques are generated ONCE in Round 1
- Rounds 2-3 don't update them with new information
- Same texts compared → Same %23 result every time

**Impact:**
- ❌ System falsely claims "adversarial debate" but only debates once
- ❌ Convergence never happens (max rounds = forced stop)
- ❌ LLMs don't learn from each other iteratively

---

### Issue #2: LaTeX Citation Error (Offline Mode)

**Symptoms:**
```latex
! Emergency stop.
<*> ./document.tex
!  ==> Fatal error occurred, no output PDF file produced!

Package natbib Warning: Citation `taxonomy' undefined
Package natbib Warning: Citation `morphology' undefined
```

**Root Cause:**
- System runs in **offline mode** (no web search)
- LLMs generate content with citation placeholders: `\citep{taxonomy}`
- LaTeX compiler expects bibliography entries, finds none
- Emergency stop → PDF regeneration fails

**Current Behavior:**
```
Attempt 1: FAIL (undefined citations)
Attempt 2: FAIL (undefined citations)
Attempt 3: FAIL (undefined citations)
→ Force approve with broken PDF
```

**Impact:**
- ❌ PDF compilation fails 100% in offline mode
- ❌ Regeneration loop wastes time/tokens
- ❌ Final PDF may be broken or force-approved

---

### Issue #3: Cross-Examination Not Iterative

**Current Flow:**
```
Phase 2: Parallel Drafting
├─ Gemini writes Draft A
└─ Claude writes Draft B

Phase 3: Cross-Examination (ONCE)
├─ Gemini sees Draft B → Writes Critique A
└─ Claude sees Draft A → Writes Critique B

Phase 4: Convergence (BLIND LOOP)
├─ Round 1: Compare Critique A vs Critique B → 23%
├─ Round 2: Compare Critique A vs Critique B → 23% (SAME!)
└─ Round 3: Compare Critique A vs Critique B → 23% (SAME!)
```

**What's Missing:**
- ❌ No "handshake" where LLMs see each other's **NEW** responses
- ❌ No line-by-line comparison ("You said X, I said Y, let's resolve")
- ❌ No incremental consensus building (lock agreed points, discuss disputed)
- ❌ No LLM-based convergence check ("Are we %90 aligned now?")

**Desired Flow:**
```
Round 1:
├─ Gemini Draft A + Claude Draft B
└─ Both see each other's drafts:
    "YOUR ANSWER: [A]
     OTHER'S ANSWER: [B]
     COMPARE LINE-BY-LINE:
     - Where do we agree? ✓
     - Where do we differ? ✗
     - Whose evidence is stronger?
     REVISE YOUR ANSWER:"

Round 2:
├─ Gemini Draft A2 + Claude Draft B2
└─ Both see BOTH old and new:
    "YOUR OLD: [A1]
     OTHER'S OLD: [B1]
     YOUR NEW: [A2]
     OTHER'S NEW: [B2]
     CONVERGENCE CHECK:
     - Round 1 differences: [...]
     - Round 2 differences: [...]
     - Consensus %: X%
     REVISE YOUR ANSWER:"

Round 3:
└─ If consensus < 95%, repeat
    If consensus >= 95%, STOP
```

---

## 🎯 SOTA Solution Architecture

### Phase 3+4 Fusion: Iterative Comparative Debate

**New System Flow:**

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 3+4: ITERATIVE COMPARATIVE DEBATE                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Round 1: INITIAL COMPARISON                                │
│  ├─ Input: gemini_draft, claude_draft                       │
│  ├─ Prompt: "COMPARISON HANDSHAKE"                          │
│  │   ├─ Show both drafts side-by-side                       │
│  │   ├─ Line-by-line comparison table                       │
│  │   ├─ Identify: Agreed ✓ / Conflict ✗ / Missing ⚠        │
│  │   └─ Output: Revised + Consensus Score (LLM-generated)   │
│  ├─ gemini_revised_1, consensus_score_gemini_1 (e.g., 45%)  │
│  ├─ claude_revised_1, consensus_score_claude_1 (e.g., 50%)  │
│  └─ Average Consensus: 47.5%                                │
│                                                             │
│  Round 2: INCREMENTAL CONVERGENCE                           │
│  ├─ Input: old (R1) + new (R2) drafts                       │
│  ├─ Prompt: "CONVERGENCE HANDSHAKE"                         │
│  │   ├─ Show: Your old, Other's old, Your new, Other's new  │
│  │   ├─ Compare: What changed? What's still disputed?       │
│  │   ├─ Lock: 100% agreed points (don't rediscuss)          │
│  │   ├─ Focus: Only disputed points                         │
│  │   └─ Output: Revised + New Consensus Score               │
│  ├─ gemini_revised_2, consensus_score_gemini_2 (e.g., 78%)  │
│  ├─ claude_revised_2, consensus_score_claude_2 (e.g., 82%)  │
│  └─ Average Consensus: 80%                                  │
│                                                             │
│  Round 3: FINAL ALIGNMENT                                   │
│  ├─ Continue until consensus >= 95%                         │
│  ├─ gemini_revised_3, consensus_score_gemini_3 (e.g., 95%)  │
│  ├─ claude_revised_3, consensus_score_claude_3 (e.g., 96%)  │
│  └─ Average Consensus: 95.5% → CONVERGED ✓                 │
│                                                             │
│  Output: Final agreed points only (A ∩ B intersection)      │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Implementation Plan

### Task 1: Replace Semantic Similarity with LLM-Based Consensus

**File:** `src/phases/phase_4_convergence.py`

**Current (BROKEN):**
```python
def calculate_semantic_similarity(text_a: str, text_b: str) -> float:
    """Embedding-based cosine similarity"""
    # Uses Claude to generate embeddings
    # Returns 0.0-1.0 score
    # PROBLEM: Passive, doesn't involve debate
```

**New (SOTA):**
```python
def calculate_llm_consensus(
    agent_name: str,
    own_old: str,
    other_old: str,
    own_new: str,
    other_new: str,
    locked_agreements: list[str],
    round_num: int
) -> tuple[float, list[str], list[str]]:
    """
    LLM-based consensus scoring with line-by-line comparison

    Returns:
        consensus_score: 0.0-1.0 (e.g., 0.85 = 85%)
        new_agreements: ["Point X", "Point Y"] (newly agreed)
        still_disputed: ["Point Z"] (still arguing)
    """

    prompt = f"""
    CONSENSUS EVALUATION - Round {round_num}

    LOCKED AGREEMENTS (DO NOT REDISCUSS):
    {format_locked_agreements(locked_agreements)}

    YOUR PREVIOUS ANSWER (Round {round_num - 1}):
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    {own_old}
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    OTHER AGENT'S PREVIOUS ANSWER (Round {round_num - 1}):
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    {other_old}
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    YOUR NEW ANSWER (Round {round_num}):
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    {own_new}
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    OTHER AGENT'S NEW ANSWER (Round {round_num}):
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    {other_new}
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    TASK: LINE-BY-LINE CONSENSUS ANALYSIS

    1. COMPARISON TABLE (Mandatory Format):

    | Claim # | Your Statement | Other's Statement | Your Source | Other's Source | Status | Resolution |
    |---------|----------------|-------------------|-------------|----------------|--------|------------|
    | 1       | X happens      | X happens         | [url1]      | [url2]         | ✓ AGREE | X happens |
    | 2       | Y uncertain    | Y confirmed       | [url3]      | [url4]         | ✗ CONFLICT | Need review |
    | 3       | Z absent       | Z present         | none        | [url5]         | ⚠ PARTIAL | Accept Z |

    2. CONSENSUS CALCULATION:
    - Total claims: X
    - Agreed claims (✓): Y
    - Conflicted claims (✗): Z
    - Consensus: (Y / X) * 100 = ?%

    3. NEW AGREEMENTS (this round):
    - List claims that moved from ✗/⚠ → ✓

    4. STILL DISPUTED:
    - List claims still in ✗ state
    - For each: Why disagreement? Whose evidence stronger?

    5. CONVERGENCE DECISION:
    - If consensus >= 95%: "CONVERGED - Ready for synthesis"
    - If consensus < 95%: "CONTINUE - Focus on: [disputed points]"

    OUTPUT JSON:
    {{
      "consensus_score": 0.85,
      "total_claims": 20,
      "agreed_claims": 17,
      "disputed_claims": 3,
      "new_agreements": ["Claim 5", "Claim 12"],
      "still_disputed": ["Claim 7", "Claim 19"],
      "convergence_status": "CONTINUE",
      "next_focus": "Resolve disagreement on migration patterns"
    }}
    """
```

---

### Task 2: Restructure Phase 3 (Cross-Examination) to Be Iterative

**File:** `src/phases/phase_3_cross_examination.py`

**Current (SINGLE PASS):**
```python
def run_cross_examination(state: ResearchState) -> ResearchState:
    """Runs ONCE - agents critique each other's ORIGINAL drafts"""

    gemini_critique = call_gemini(
        prompt=f"Critique this: {state.claude_draft}",
        system=SYSTEM_PROMPT_GEMINI_EXPLORER
    )

    claude_critique = call_claude(
        prompt=f"Critique this: {state.gemini_draft}",
        system=SYSTEM_PROMPT_CLAUDE_JUDGE
    )

    state.gemini_critique = gemini_critique
    state.claude_critique = claude_critique
    return state
```

**New (ITERATIVE WITH HANDSHAKE):**
```python
def run_iterative_debate_round(
    state: ResearchState,
    round_num: int
) -> ResearchState:
    """
    Iterative debate round with full context handshake

    Each agent sees:
    - Their own previous answer
    - Other's previous answer
    - Locked agreements (don't rediscuss)
    - Disputed points (focus here)
    """

    # Get previous versions
    gemini_prev = state.get_latest_gemini_version()
    claude_prev = state.get_latest_claude_version()

    # Parallel debate with full context
    gemini_response = call_gemini(
        prompt=build_handshake_prompt(
            agent="Gemini",
            own_prev=gemini_prev,
            other_prev=claude_prev,
            locked=state.locked_agreements,
            disputed=state.disputed_points,
            round_num=round_num
        ),
        system=SYSTEM_PROMPT_GEMINI_EXPLORER
    )

    claude_response = call_claude(
        prompt=build_handshake_prompt(
            agent="Claude",
            own_prev=claude_prev,
            other_prev=gemini_prev,
            locked=state.locked_agreements,
            disputed=state.disputed_points,
            round_num=round_num
        ),
        system=SYSTEM_PROMPT_CLAUDE_JUDGE
    )

    # Parse responses (revised answer + consensus score)
    state.add_gemini_version(gemini_response["revised_answer"])
    state.add_claude_version(claude_response["revised_answer"])

    # Calculate consensus (ask both agents)
    gemini_consensus = calculate_llm_consensus(
        "Gemini", gemini_prev, claude_prev,
        gemini_response["revised_answer"],
        claude_response["revised_answer"],
        state.locked_agreements, round_num
    )

    claude_consensus = calculate_llm_consensus(
        "Claude", claude_prev, gemini_prev,
        claude_response["revised_answer"],
        gemini_response["revised_answer"],
        state.locked_agreements, round_num
    )

    # Average consensus
    avg_consensus = (gemini_consensus[0] + claude_consensus[0]) / 2

    # Update locked agreements
    new_agreements = list(set(
        gemini_consensus[1] + claude_consensus[1]
    ))
    state.locked_agreements.extend(new_agreements)

    # Update disputed points
    state.disputed_points = list(set(
        gemini_consensus[2] + claude_consensus[2]
    ))

    state.convergence_score = avg_consensus

    logger.info(f"Round {round_num} Consensus: {avg_consensus:.1%}")
    logger.info(f"  New Agreements: {len(new_agreements)}")
    logger.info(f"  Still Disputed: {len(state.disputed_points)}")

    return state
```

---

### Task 3: Fix LaTeX Citation in Offline Mode

**File:** `src/agents/latex_generator.py`

**Problem:** Offline mode generates `\citep{taxonomy}` but no bibliography

**Solution 1: Conditional Citations (Quick Fix)**
```python
def generate_latex(
    consensus: str,
    research_mode: str,
    grounding_data: dict
) -> str:
    """Generate LaTeX with conditional citation handling"""

    if research_mode == "offline":
        # No citations in offline mode
        system_prompt = SYSTEM_PROMPT_LATEX_GENERATOR + """

        CRITICAL - OFFLINE MODE:
        ⚠️ DO NOT use \\citep{} or \\cite{} commands
        ⚠️ DO NOT include \\begin{thebibliography}
        ⚠️ Write content as plain academic text without citations
        ⚠️ If mentioning sources, use inline text: "According to research..."
        """
    else:
        # Normal citations in internet mode
        system_prompt = SYSTEM_PROMPT_LATEX_GENERATOR

    latex = call_claude(
        prompt=build_latex_prompt(consensus, grounding_data),
        system=system_prompt
    )

    # Fallback: Strip citations if offline mode
    if research_mode == "offline":
        latex = strip_citations(latex)

    return latex


def strip_citations(latex: str) -> str:
    """Remove all citation commands from LaTeX"""
    import re

    # Remove \citep{...}, \cite{...}, \citet{...}
    latex = re.sub(r'\\cite[pt]?\{[^}]+\}', '', latex)

    # Remove \bibliography{...}
    latex = re.sub(r'\\bibliography\{[^}]+\}', '', latex)

    # Remove \begin{thebibliography}...\end{thebibliography}
    latex = re.sub(
        r'\\begin\{thebibliography\}.*?\\end\{thebibliography\}',
        '',
        latex,
        flags=re.DOTALL
    )

    return latex
```

**Solution 2: Smart Citation Replacement (Better)**
```python
def replace_citations_with_inline(latex: str, sources: dict) -> str:
    """
    Replace \citep{key} with inline text

    Example:
        \citep{taxonomy} → "(Smith et al., 2020)"
        \citep{morphology} → "(Jones, 2019)"
    """
    import re

    def citation_replacer(match):
        key = match.group(1)
        if key in sources:
            return f"({sources[key]['inline']})"
        else:
            return "(Internal Knowledge)"

    latex = re.sub(r'\\citep\{([^}]+)\}', citation_replacer, latex)

    return latex
```

---

### Task 4: Add Structured Comparison Table to State

**File:** `src/schemas.py`

**Add New Fields:**
```python
class ComparisonClaim(BaseModel):
    """Single claim in comparison table"""
    claim_id: int
    gemini_statement: str
    claude_statement: str
    gemini_source: Optional[str] = None
    claude_source: Optional[str] = None
    status: Literal["agree", "conflict", "partial"]
    resolution: str
    confidence_gemini: float = Field(ge=0, le=1)
    confidence_claude: float = Field(ge=0, le=1)


class DebateRound(BaseModel):
    """Single round of iterative debate"""
    round_num: int
    gemini_answer: str
    claude_answer: str
    comparison_table: list[ComparisonClaim]
    consensus_score: float = Field(ge=0, le=1)
    new_agreements: list[str]
    disputed_points: list[str]
    convergence_status: Literal["continue", "converged"]


class ResearchState(BaseModel):
    """Enhanced state with debate history"""

    # ... existing fields ...

    # New fields for iterative debate
    debate_rounds: list[DebateRound] = []
    locked_agreements: list[str] = []
    disputed_points: list[str] = []
    convergence_score: float = 0.0

    def get_latest_gemini_version(self) -> str:
        """Get most recent Gemini answer"""
        if self.debate_rounds:
            return self.debate_rounds[-1].gemini_answer
        return self.gemini_draft

    def get_latest_claude_version(self) -> str:
        """Get most recent Claude answer"""
        if self.debate_rounds:
            return self.debate_rounds[-1].claude_answer
        return self.claude_draft

    def add_debate_round(self, round_data: DebateRound):
        """Add new debate round"""
        self.debate_rounds.append(round_data)
        self.convergence_score = round_data.consensus_score
```

---

### Task 5: Enhance Prompts with Comparison Instructions

**File:** `src/prompts.py`

**Add New Prompt:**
```python
PROMPT_COMPARISON_HANDSHAKE = """
COMPARISON HANDSHAKE - Round {round_num}

═══════════════════════════════════════════════════════════
YOUR ROLE: {agent_name}
═══════════════════════════════════════════════════════════

LOCKED AGREEMENTS (DO NOT REDISCUSS):
{locked_agreements}

YOUR PREVIOUS ANSWER (Round {prev_round}):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{own_previous}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

OTHER AGENT'S PREVIOUS ANSWER (Round {prev_round}):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{other_previous}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DISPUTED POINTS (FOCUS HERE):
{disputed_points}

═══════════════════════════════════════════════════════════
TASK: METICULOUS LINE-BY-LINE COMPARISON
═══════════════════════════════════════════════════════════

1. COMPARISON TABLE (MANDATORY):
   Create a table comparing EVERY claim you and other agent made:

   | Claim # | Your Statement | Other's Statement | Your Source | Other's Source | Status | Resolution |
   |---------|----------------|-------------------|-------------|----------------|--------|------------|
   | 1       | ...            | ...               | [url]       | [url]          | ✓/✗/⚠  | ...        |

   Status Legend:
   ✓ AGREE    - Both say same thing with comparable sources
   ✗ CONFLICT - Direct contradiction or incompatible claims
   ⚠ PARTIAL  - Similar but with nuances/caveats

2. CONSENSUS CALCULATION:
   - Total claims made: X
   - Agreed claims (✓): Y
   - Consensus: (Y / X) * 100 = ?%

3. CONFLICT RESOLUTION:
   For each ✗ or ⚠:
   - WHY do you disagree?
   - Whose SOURCE is stronger? (primary vs secondary, date, authority)
   - What's your FINAL DECISION? (accept theirs, keep yours, merge)

4. REVISED ANSWER:
   Write your NEW answer that:
   - Keeps 100% agreed points (✓) as-is
   - Incorporates resolutions (accept better evidence)
   - Removes weak claims (if other's source stronger)
   - Adds caveats where uncertainty remains

5. CONVERGENCE CHECK:
   - If consensus >= 95%: Mark as "CONVERGED"
   - If consensus < 95%: Mark as "CONTINUE" + explain what's still disputed

═══════════════════════════════════════════════════════════
CRITICAL RULES:
═══════════════════════════════════════════════════════════

⚠️ BE METICULOUS: Compare EVERY sentence, not just overall vibes
⚠️ DON'T FORGET YOUR OLD ANSWER: It's shown above, reference it
⚠️ DON'T REDISCUSS LOCKED AGREEMENTS: Focus only on disputed
⚠️ BE HONEST: If other agent has better source, accept it
⚠️ BE RIGOROUS: Don't inflate consensus, be accurate

═══════════════════════════════════════════════════════════
OUTPUT FORMAT (JSON):
═══════════════════════════════════════════════════════════

{{
  "comparison_table": [
    {{
      "claim_id": 1,
      "your_statement": "...",
      "other_statement": "...",
      "your_source": "...",
      "other_source": "...",
      "status": "agree|conflict|partial",
      "resolution": "...",
      "your_confidence": 0.9,
      "other_confidence": 0.85
    }}
  ],
  "consensus_score": 0.75,
  "total_claims": 20,
  "agreed_claims": 15,
  "disputed_claims": 5,
  "new_agreements": ["Claim about X", "Claim about Y"],
  "still_disputed": ["Migration timing", "Predator list"],
  "revised_answer": "... YOUR NEW ANSWER HERE ...",
  "convergence_status": "continue|converged",
  "next_focus": "Resolve migration timing discrepancy"
}}
"""
```

---

### Task 6: Update Workflow to Use New System

**File:** `src/workflow.py`

**Replace Loop:**
```python
# OLD (BROKEN):
while state.current_round < config.MAX_ROUNDS:
    state = run_cross_examination(state)
    state = check_convergence(state)
    if state.converged:
        break

# NEW (SOTA):
while state.current_round < config.MAX_ROUNDS:
    # Run iterative debate round
    state = run_iterative_debate_round(state, state.current_round)

    # Check LLM-based consensus
    if state.convergence_score >= config.CONVERGENCE_THRESHOLD:
        logger.info(f"✅ CONVERGED at {state.convergence_score:.1%}")
        break

    logger.info(f"🔄 Round {state.current_round} - Consensus: {state.convergence_score:.1%}")
    logger.info(f"   Still disputed: {state.disputed_points}")

    state.current_round += 1
```

---

## 📈 Expected Improvements

### Before (Current System)
```
Round 1: 23% (only meaningful comparison)
Round 2: 23% (blind loop, no new info)
Round 3: 23% (blind loop, no new info)
Result: Forced stop, low-quality consensus
```

### After (SOTA System)
```
Round 1: 47% (initial comparison with full context)
  - Agreed: 9/20 claims
  - Disputed: 11/20 claims
  - Focus next: Migration patterns, predator identification

Round 2: 78% (iterative refinement, locked agreements)
  - Agreed: 16/20 claims (added 7 from disputed)
  - Disputed: 4/20 claims
  - Focus next: Specific migration dates, subspecies classification

Round 3: 95% (final alignment)
  - Agreed: 19/20 claims
  - Disputed: 1/20 claims (marked as "uncertain")
  - Status: CONVERGED ✓
```

---

## 🎯 Additional SOTA Enhancements

### Enhancement A: Confidence-Weighted Consensus

**Concept:** Not all agreements are equal

```python
def calculate_weighted_consensus(comparison_table):
    """
    Weight consensus by confidence scores

    Example:
    - Claim 1: Both 0.9 confidence → Weight: 1.0
    - Claim 2: 0.5 vs 0.9 confidence → Weight: 0.7 (favor higher)
    - Claim 3: Both 0.4 confidence → Weight: 0.4 (weak agreement)
    """

    total_weight = 0
    agreed_weight = 0

    for claim in comparison_table:
        if claim.status == "agree":
            # Average confidence as weight
            weight = (claim.confidence_gemini + claim.confidence_claude) / 2
            agreed_weight += weight

        total_weight += 1.0

    return agreed_weight / total_weight
```

**Benefit:** Prevents false consensus from weak/uncertain agreements

---

### Enhancement B: Devil's Advocate Mode

**Concept:** One agent challenges more aggressively

```python
def assign_debate_roles(round_num: int):
    """
    Alternate devil's advocate role

    Round 1: Both neutral
    Round 2: Gemini = advocate, Claude = skeptic
    Round 3: Claude = advocate, Gemini = skeptic
    """

    if round_num % 2 == 0:
        return {
            "gemini": "STRICT MODE - Challenge every claim",
            "claude": "OPEN MODE - Accept strong evidence"
        }
    else:
        return {
            "gemini": "OPEN MODE - Accept strong evidence",
            "claude": "STRICT MODE - Challenge every claim"
        }
```

**Benefit:** Prevents premature consensus, ensures rigor

---

### Enhancement C: Citation Cross-Validation

**Concept:** Check if sources actually say what's claimed

```python
def validate_citation_consistency(claim, sources):
    """
    Ask LLM: Does source actually support claim?

    If Gemini says: "X happens [Source: url1]"
    And Claude says: "X happens [Source: url2]"

    → Check: Do url1 and url2 BOTH say X?
    → If yes: Strong agreement
    → If only one: Weak agreement
    → If neither: False claim
    """

    validation_prompt = f"""
    CLAIM: {claim.gemini_statement}
    SOURCE 1: {sources[claim.gemini_source]}
    SOURCE 2: {sources[claim.claude_source]}

    Does SOURCE 1 actually support the CLAIM? (yes/no/partial)
    Does SOURCE 2 actually support the CLAIM? (yes/no/partial)

    If both support → "cross-validated"
    If only one → "single-validated"
    If neither → "unsupported"
    """
```

**Benefit:** Prevents citation fabrication, ensures evidence quality

---

### Enhancement D: Incremental Consensus Locking

**Concept:** Don't re-debate settled points

```python
class DebateState:
    locked_agreements: list[LockedClaim] = []

    def lock_claim(self, claim: ComparisonClaim):
        """
        Lock a claim once both agents agree with high confidence

        Criteria:
        - Status: "agree"
        - Both confidence >= 0.85
        - Same for 2 consecutive rounds
        """
        if (claim.status == "agree" and
            claim.confidence_gemini >= 0.85 and
            claim.confidence_claude >= 0.85):

            self.locked_agreements.append(LockedClaim(
                statement=claim.resolution,
                source_gemini=claim.gemini_source,
                source_claude=claim.claude_source,
                locked_round=self.current_round
            ))

            logger.info(f"🔒 Locked: {claim.resolution}")

    def build_handshake_prompt(self):
        """
        Don't include locked claims in comparison
        → Reduces token usage
        → Focuses debate on disputed points only
        """

        prompt = "LOCKED (Don't Rediscuss):\n"
        for locked in self.locked_agreements:
            prompt += f"  ✓ {locked.statement}\n"

        prompt += "\nDISPUTED (Focus Here):\n"
        for disputed in self.disputed_points:
            prompt += f"  ✗ {disputed}\n"
```

**Benefit:** Monotonic convergence, efficient token usage

---

### Enhancement E: Consensus Visualization

**Concept:** Track convergence progression

```python
def visualize_convergence(debate_rounds):
    """
    Generate convergence plot

    Round 1: ████████░░░░░░░░░░░░ 40%
    Round 2: ███████████████░░░░░ 75%
    Round 3: ███████████████████░ 95%
    """

    for round in debate_rounds:
        bar_length = 20
        filled = int(bar_length * round.consensus_score)
        bar = "█" * filled + "░" * (bar_length - filled)

        print(f"Round {round.round_num}: {bar} {round.consensus_score:.0%}")
        print(f"  Agreed: {len(round.new_agreements)} new claims")
        print(f"  Disputed: {len(round.disputed_points)} remaining")
```

---

## 🚀 Migration Plan

### Phase 1: Fix LaTeX Citations (Quick Win)
**Time:** 30 min
**Files:** `latex_generator.py`
**Impact:** PDF compilation works in offline mode

### Phase 2: Add Comparison Table Schema (Foundation)
**Time:** 1 hour
**Files:** `schemas.py`, `prompts.py`
**Impact:** Enables structured comparison

### Phase 3: Implement LLM-Based Consensus (Core)
**Time:** 2 hours
**Files:** `phase_4_convergence.py` → rename to `phase_3_4_iterative_debate.py`
**Impact:** Real consensus measurement

### Phase 4: Add Iterative Handshake (Critical)
**Time:** 3 hours
**Files:** `phase_3_cross_examination.py`, `workflow.py`
**Impact:** True adversarial debate

### Phase 5: Add SOTA Enhancements (Polish)
**Time:** 2 hours
**Files:** All above
**Impact:** Confidence weighting, locking, visualization

### Phase 6: Testing & Validation
**Time:** 1 hour
**Test Cases:**
- Seal/walrus query (current test)
- Rosenbloom framework homework
- Technical CS question
- Current events (with internet mode)

---

## 📊 Success Metrics

### Before vs After Comparison

| Metric | Before (Broken) | After (SOTA) | Target |
|--------|----------------|--------------|--------|
| Convergence Rate | 23% (stuck) | 90-95% | 95%+ |
| Rounds to Converge | N/A (never) | 2-3 rounds | ≤3 |
| PDF Compile Success | 0% (offline) | 100% | 100% |
| Consensus Quality | Low (forced) | High (earned) | High |
| Token Efficiency | Low (blind loops) | High (focused) | High |
| Debate Authenticity | Fake (1 pass) | Real (iterative) | Real |

---

## 🔬 Testing Protocol

### Test 1: Convergence Test (Seal/Walrus)
```
Query: "Seal, walrus, fok familyası canlıları..."
Expected:
- Round 1: ~50% (initial comparison)
- Round 2: ~75% (refinement)
- Round 3: ~95% (convergence)
- PDF: Compiles successfully
```

### Test 2: Homework Test (Rosenbloom)
```
Query: "Apply Rosenbloom framework to computing research"
Expected:
- No academic integrity refusal ✓
- Completes assignment fully
- No methodology contamination
- Convergence >= 90%
```

### Test 3: Offline vs Internet Mode
```
Offline:
- No \citep{} commands
- Inline text citations
- PDF compiles

Internet:
- Proper \citep{} commands
- Bibliography section
- Tavily sources used
```

---

## 📝 Implementation Checklist

- [ ] **Task 1:** Replace semantic similarity with LLM consensus
- [ ] **Task 2:** Make cross-examination iterative
- [ ] **Task 3:** Fix LaTeX citations (offline mode)
- [ ] **Task 4:** Add ComparisonClaim/DebateRound schemas
- [ ] **Task 5:** Add PROMPT_COMPARISON_HANDSHAKE
- [ ] **Task 6:** Update workflow loop
- [ ] **Enhancement A:** Confidence-weighted consensus
- [ ] **Enhancement B:** Devil's advocate mode
- [ ] **Enhancement C:** Citation cross-validation
- [ ] **Enhancement D:** Incremental locking
- [ ] **Enhancement E:** Convergence visualization
- [ ] **Test 1:** Seal/walrus convergence test
- [ ] **Test 2:** Rosenbloom homework test
- [ ] **Test 3:** Offline/internet mode test

---

## 🎯 Final Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    DUAL-LLM RESEARCH SYSTEM                    │
│                         (SOTA VERSION)                         │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Phase 1: Grounding                                            │
│  ├─ Auto mode detection                                        │
│  ├─ Tavily search (if internet)                                │
│  └─ Google Search Grounding (Gemini 2.5 Pro) ✅                │
│                                                                │
│  Phase 2: Parallel Drafting                                    │
│  ├─ Gemini 2.5 Pro: Creative explorer (T=0.7)                  │
│  ├─ Claude Sonnet 4.5: Rigorous judge (T=0.5)                  │
│  └─ Isolation mode (no communication)                          │
│                                                                │
│  Phase 3+4: ITERATIVE COMPARATIVE DEBATE ⭐ NEW                │
│  ├─ Round 1: Initial comparison                                │
│  │   ├─ Both see each other's drafts                           │
│  │   ├─ Line-by-line comparison table                          │
│  │   ├─ LLM-based consensus scoring                            │
│  │   └─ Consensus: ~50%                                        │
│  ├─ Round 2: Incremental convergence                           │
│  │   ├─ See old + new versions                                 │
│  │   ├─ Lock agreed points                                     │
│  │   ├─ Focus on disputed only                                 │
│  │   └─ Consensus: ~80%                                        │
│  └─ Round 3: Final alignment                                   │
│      ├─ Devil's advocate mode                                  │
│      ├─ Citation cross-validation                              │
│      └─ Consensus: 95%+ → CONVERGED ✓                         │
│                                                                │
│  Phase 5: Intersection Synthesis                               │
│  ├─ Extract locked agreements only                             │
│  ├─ No methodology contamination ✅                             │
│  └─ Academic integrity override ✅                              │
│                                                                │
│  Phase 6: LaTeX → PDF Pipeline                                 │
│  ├─ Conditional citations (offline/internet) ✅                 │
│  ├─ Dual QA: Visual + Content                                  │
│  └─ Input-output alignment check ✅                             │
│                                                                │
│  Output: Submittable research report PDF                       │
└────────────────────────────────────────────────────────────────┘
```

---

## 🏁 Conclusion

**Current Status:** System has good architecture but 3 critical bugs prevent SOTA performance.

**Required Changes:**
1. ⚠️ **CRITICAL:** Replace semantic similarity with LLM-based consensus
2. ⚠️ **CRITICAL:** Make debate iterative (agents see each other's revisions)
3. ⚠️ **HIGH:** Fix LaTeX citations in offline mode
4. 🎯 **NICE:** Add confidence weighting, locking, visualization

**Expected Result After Fixes:**
- ✅ Convergence: 23% → 95%
- ✅ Debate quality: Fake → Real iterative refinement
- ✅ PDF compilation: 0% → 100% success rate
- ✅ Output quality: Meta-analysis → Direct answer
- ✅ Token efficiency: Blind loops → Focused refinement

**Implementation Time:** ~9 hours (full SOTA) or ~4 hours (critical only)

**Next Step:** Begin implementation with Phase 1 (LaTeX fix) for quick win, then Phase 2-4 for core convergence system.

---

**END OF MASTERPLAN**
