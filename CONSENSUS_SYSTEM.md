# 4-Way Consensus System (SOTA)

## Overview
This system uses **4 independent metrics** to ensure true convergence between Gemini and Claude agents. ALL 4 metrics must reach the threshold (default: 85%) for convergence.

---

## The 4 Metrics

### 1. **Symmetric Consensus** (Official Metric)
- **What:** Intersection-based consensus - only counts claims BOTH agents evaluated
- **Why:** Mathematically consistent, prevents confusion
- **How:** Matches claims by ID, calculates agreement only on shared claims
- **Example:**
  - Gemini has 10 claims, Claude has 8 claims
  - Intersection: 5 claims (both evaluated)
  - Symmetric consensus = agreement rate on these 5 claims

### 2. **Gemini Coverage** (Diagnostic)
- **What:** Asymmetric metric - Gemini's perspective
- **Why:** Shows how well Claude agrees with Gemini's claims
- **How:** Gemini's total claims as base, calculates % Claude agrees with
- **Example:**
  - Gemini made 10 claims
  - Claude agrees with 7 of them
  - Gemini coverage = 70%

### 3. **Claude Coverage** (Diagnostic)
- **What:** Asymmetric metric - Claude's perspective
- **Why:** Shows how well Gemini agrees with Claude's claims
- **How:** Claude's total claims as base, calculates % Gemini agrees with
- **Example:**
  - Claude made 8 claims
  - Gemini agrees with 7 of them
  - Claude coverage = 87.5%

### 4. **Average Coverage** (Diagnostic)
- **What:** Simple average of Gemini and Claude coverage
- **Why:** Overall alignment metric
- **How:** (Gemini coverage + Claude coverage) / 2

---

## Convergence Logic

### OLD SYSTEM (Problematic)
```python
# Only checked average of 2 asymmetric metrics
converged = (gemini_consensus + claude_consensus) / 2 >= 0.85
```

**Problem:**
- Gemini: 36% ❌
- Claude: 82% ✅
- Average: 59% ❌ → Continue

But this masked the fact that Gemini had VERY low consensus!

### NEW SYSTEM (SOTA)
```python
# ALL 4 metrics must pass
converged = (
    symmetric_consensus >= 0.85 AND
    gemini_coverage >= 0.85 AND
    claude_coverage >= 0.85 AND
    avg_coverage >= 0.85
)
```

**Benefit:**
- Gemini: 71% ❌
- Claude: 89% ✅
- Symmetric: 80% ❌
- Average: 80% ❌
- Result: Continue (need more rounds)

**When it converges:**
- Gemini: 87% ✅
- Claude: 91% ✅
- Symmetric: 89% ✅
- Average: 89% ✅
- Result: ✅ CONVERGED - All 4 metrics satisfied!

---

## Example Log Output

```
Round 1: Iterative Debate
  Progressive threshold: 70%
  Mode: Neutral comparison
  → Gemini and Claude comparing and revising in parallel...
  → Both agents completed

  📊 METRICS (4-way consensus):
     • Symmetric: 65.3% (intersection-based)
     • Gemini Coverage: 58.7% (asymmetric)
     • Claude Coverage: 81.2% (asymmetric)
     • Average Coverage: 70.0% (asymmetric avg)

  🎯 Convergence Check (threshold: 85%):
     ❌ Symmetric: 65.3%
     ❌ Gemini Coverage: 58.7%
     ❌ Claude Coverage: 81.2%
     ❌ Average Coverage: 70.0%

  New locked claims: 4
  Still disputed: 6

  🔄 Debate continues (Lowest metric: 58.7%, Gap: 26.3%)
```

---

## Benefits

### 1. **No Premature Convergence**
- Can't converge if one agent still has low consensus
- Ensures both perspectives are aligned

### 2. **Diagnostic Visibility**
- See exactly which agent needs more alignment
- "Gemini 60%, Claude 90%" → Gemini needs to accept more of Claude's claims

### 3. **True Agreement**
- Symmetric metric prevents base asymmetry confusion
- Both agents see same "official" consensus score

### 4. **Progressive Confidence**
- Round 1: 70% threshold → quick early locks
- Round 2: 80% threshold → medium confidence
- Round 3+: 85% threshold → only high-confidence claims lock

---

## Configuration

### `.env` Settings
```env
MAX_ROUNDS=999  # Effectively unlimited - stops when converged
CONVERGENCE_THRESHOLD=0.85  # All 4 metrics must reach 85%
```

### Why 999 rounds?
- System will stop when ALL 4 metrics >= 85%
- No arbitrary round limit (2-3 rounds)
- Ensures quality over speed
- Typical convergence: 3-7 rounds depending on topic complexity

---

## Implementation Details

### Key Functions

1. **`calculate_symmetric_consensus(gemini_table, claude_table)`**
   - Matches claims by ID (intersection)
   - Returns single consensus score both agents see

2. **`calculate_weighted_consensus(comparison_table)`**
   - Individual perspective (asymmetric)
   - Returns coverage from one agent's viewpoint

3. **4-Way Convergence Check**
   - Checks all 4 metrics individually
   - Logs which passed (✅) or failed (❌)
   - Only converges if ALL pass

### Confidence Weighting
```python
# Not all agreements are equal
if claim.status == "agree":
    agreed_weight += avg_confidence  # Full weight
elif claim.status == "partial":
    agreed_weight += avg_confidence * 0.5  # Half weight
# "conflict" contributes 0
```

---

## Troubleshooting

### "Gemini coverage stuck at 60%"
- Gemini is making claims Claude doesn't agree with
- Check disputed points → likely Gemini being too broad
- Solution: Collaborative mode will push Gemini to be more conservative

### "Symmetric consensus lower than both coverages"
- Normal! Symmetric only counts intersection
- Example:
  - Gemini: 10 claims, 7 agree → 70% coverage
  - Claude: 8 claims, 7 agree → 87.5% coverage
  - Intersection: 5 claims, 4 agree → 80% symmetric
- This is mathematically correct

### "Convergence taking too many rounds"
- Check progressive thresholds (70% → 80% → 85%)
- May need to lower CONVERGENCE_THRESHOLD to 0.80
- Or adjust progressive thresholds in code

---

## Comparison: OLD vs NEW

| Aspect | OLD (Asymmetric Only) | NEW (4-Way Hybrid) |
|--------|----------------------|-------------------|
| **Metrics** | 2 (Gemini, Claude) | 4 (Symmetric + 3 asymmetric) |
| **Convergence** | Average >= threshold | ALL 4 >= threshold |
| **Confusion** | "Why 36% vs 82%?" | Clear diagnostic metrics |
| **Quality** | Can converge with low Gemini consensus | Forces both agents to align |
| **Visibility** | Limited insight | Full diagnostic breakdown |
| **Stopping** | Fixed MAX_ROUNDS | Dynamic (stops when truly converged) |

---

## Future Enhancements

1. **Weighted Thresholds**
   - Require symmetric >= 90%, but coverage >= 80%
   - Prioritize intersection quality

2. **Adaptive Thresholds**
   - Easy topics: require 95%
   - Hard topics: accept 80%
   - Based on initial consensus gap

3. **Metric Decay**
   - If stuck for 3 rounds, lower threshold by 5%
   - Prevents infinite loops

4. **Per-Claim Tracking**
   - Store which specific claims block convergence
   - Focus next round only on blocking claims

---

## Credits

**Design:** SOTA dual-LLM adversarial debate system
**Implementation:** 4-way consensus with progressive confidence
**Version:** 2.0 (January 2026)
