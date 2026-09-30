"""
Data Schemas
Pydantic models for state management and data validation
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Literal
from datetime import datetime


# ═══════════════════════════════════════════════════════════
# WEB SEARCH SCHEMAS
# ═══════════════════════════════════════════════════════════

class Source(BaseModel):
    """
    Single web source from Tavily
    """
    url: str = Field(description="Source URL")
    title: str = Field(description="Page title")
    content: str = Field(description="Extracted content")
    relevance_score: float = Field(default=1.0, description="Tavily relevance score")


class WebContext(BaseModel):
    """
    Aggregated web search results
    """
    sources: List[Source] = Field(default_factory=list)
    combined_text: str = Field(default="", description="All sources combined")
    search_query: str = Field(default="")
    total_sources: int = Field(default=0)


# ═══════════════════════════════════════════════════════════
# CORE STATE (The RAM of the system)
# ═══════════════════════════════════════════════════════════

class DebateState(BaseModel):
    """
    Minimal, clean state structure
    Based on PLAN.md principles

    This is the "RAM" of the cyclic state machine.
    Every node reads this, modifies it, and returns it.
    """

    # ───────────────────────────────────────────────────────
    # IMMUTABLE INPUTS (Set once, never changed)
    # ───────────────────────────────────────────────────────

    topic: str = Field(description="User's research question")

    research_mode: Literal["offline", "internet", "auto"] = Field(
        default="auto",
        description="V1=offline (no search), V2=internet (Tavily), auto=keyword-based decision"
    )

    report_language: Literal["auto", "tr", "en"] = Field(
        default="auto",
        description="Language of the final report: auto=follow the question's language"
    )

    shared_context: str = Field(
        default="",
        description="Web search results or offline notice (immutable after grounding)"
    )

    max_rounds: int = Field(
        default=3,
        ge=1,
        le=5,
        description="Maximum debate iterations (Default: 3)"
    )

    convergence_threshold: float = Field(
        default=0.95,
        ge=0.85,
        le=0.99,
        description="Semantic similarity target (Default: 95%)"
    )

    # ───────────────────────────────────────────────────────
    # AGENT OUTPUTS (Mutable - Updated each iteration)
    # ───────────────────────────────────────────────────────

    gemini_draft: str = Field(default="", description="Explorer's current draft")
    claude_draft: str = Field(default="", description="Judge's current draft")

    # ───────────────────────────────────────────────────────
    # LOOP CONTROL (Counters and flags)
    # ───────────────────────────────────────────────────────

    iteration_counter: int = Field(
        default=0,
        ge=0,
        description="Current iteration (0, 1, 2, ...)"
    )

    similarity_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Semantic agreement between drafts"
    )

    converged: bool = Field(default=False, description="Natural consensus reached?")
    forced_stop: bool = Field(default=False, description="Stopped due to max_rounds?")

    # ───────────────────────────────────────────────────────
    # CONSENSUS OUTPUT
    # ───────────────────────────────────────────────────────

    consensus_report: Optional[str] = Field(
        default=None,
        description="Final intersection report (A ∩ B)"
    )

    # ───────────────────────────────────────────────────────
    # PDF GENERATION PIPELINE
    # ───────────────────────────────────────────────────────

    latex_code: Optional[str] = Field(default=None, description="Generated LaTeX source")
    pdf_path: Optional[str] = Field(default=None, description="Compiled PDF file path")

    latex_retry_count: int = Field(default=0, description="LaTeX compilation retries")
    pdf_regeneration_count: int = Field(default=0, description="PDF quality regenerations")

    visual_qa_score: float = Field(default=0.0, description="Gemini Vision QA score")
    content_qa_score: float = Field(default=0.0, description="Claude Text QA score")
    average_qa_score: float = Field(default=0.0, description="Average QA score")

    pdf_approved: bool = Field(default=False, description="PDF passed QA?")
    qa_failed: bool = Field(
        default=False,
        description="QA could not be performed (API/parse error) — PDF is explicitly NOT approved"
    )

    # ───────────────────────────────────────────────────────
    # METADATA & DIAGNOSTICS
    # ───────────────────────────────────────────────────────

    errors: List[str] = Field(default_factory=list, description="Error log")

    statistics: Dict = Field(
        default_factory=dict,
        description="Performance metrics"
    )

    start_time: Optional[datetime] = Field(default=None)
    end_time: Optional[datetime] = Field(default=None)

    # Web context (for internal use)
    web_context: Optional[WebContext] = Field(default=None, description="Parsed web results")

    # ───────────────────────────────────────────────────────
    # ITERATIVE DEBATE TRACKING (SOTA Enhancement)
    # ───────────────────────────────────────────────────────

    debate_rounds: List["DebateRound"] = Field(
        default_factory=list,
        description="History of all debate rounds"
    )

    locked_agreements: List["LockedClaim"] = Field(
        default_factory=list,
        description="Claims both agents agreed on (won't be redebated)"
    )

    current_disputed_points: List[str] = Field(
        default_factory=list,
        description="Points still under debate"
    )

    # ───────────────────────────────────────────────────────
    # HELPERS
    # ───────────────────────────────────────────────────────

    def add_error(self, error: str):
        """Add error to log"""
        self.errors.append(error)

    def get_duration(self) -> float:
        """Get execution duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    def get_latest_gemini_answer(self) -> str:
        """Get most recent Gemini answer"""
        if self.debate_rounds:
            return self.debate_rounds[-1].gemini_answer
        return self.gemini_draft

    def get_latest_claude_answer(self) -> str:
        """Get most recent Claude answer"""
        if self.debate_rounds:
            return self.debate_rounds[-1].claude_answer
        return self.claude_draft

    def add_debate_round(self, round_data: "DebateRound"):
        """Add new debate round and update state"""
        self.debate_rounds.append(round_data)
        self.similarity_score = round_data.consensus_score
        self.iteration_counter = round_data.round_num

        # Update convergence status
        if round_data.convergence_status == "converged":
            self.converged = True

    model_config = {"arbitrary_types_allowed": True}


# ═══════════════════════════════════════════════════════════
# QA RESULT SCHEMAS
# ═══════════════════════════════════════════════════════════

class QAScore(BaseModel):
    """
    Quality assessment result
    """
    score: float = Field(ge=0, le=100, description="Overall score 0-100")
    feedback: str = Field(description="Detailed feedback")
    criteria_scores: Dict[str, float] = Field(default_factory=dict)
    passed: bool = Field(default=False, description="Passed threshold?")


class VisualQAScore(QAScore):
    """
    Visual quality assessment (Gemini Vision)
    """
    layout_score: float = Field(default=0.0, ge=0, le=25)
    typography_score: float = Field(default=0.0, ge=0, le=25)
    tables_figures_score: float = Field(default=0.0, ge=0, le=25)
    professional_score: float = Field(default=0.0, ge=0, le=25)


class ContentQAScore(QAScore):
    """
    Content quality assessment (Claude Text)
    Updated weights: Completeness 35, Citations 25, Structure 20, Academic 20
    """
    completeness_score: float = Field(default=0.0, ge=0, le=35)  # Increased from 30
    citation_score: float = Field(default=0.0, ge=0, le=25)      # Decreased from 30
    structure_score: float = Field(default=0.0, ge=0, le=20)
    academic_score: float = Field(default=0.0, ge=0, le=20)


# ═══════════════════════════════════════════════════════════
# ITERATIVE DEBATE SCHEMAS (SOTA Enhancement)
# ═══════════════════════════════════════════════════════════

class ComparisonClaim(BaseModel):
    """
    Single claim in line-by-line comparison table
    Used for structured consensus tracking
    """
    claim_id: int = Field(description="Unique claim identifier")
    gemini_statement: str = Field(description="Gemini's version of this claim")
    claude_statement: str = Field(description="Claude's version of this claim")
    gemini_source: Optional[str] = Field(default=None, description="Gemini's source URL")
    claude_source: Optional[str] = Field(default=None, description="Claude's source URL")
    status: Literal["agree", "conflict", "partial"] = Field(description="Agreement status")
    resolution: str = Field(description="Resolved/final version of claim")
    confidence_gemini: float = Field(default=0.8, ge=0, le=1, description="Gemini's confidence")
    confidence_claude: float = Field(default=0.8, ge=0, le=1, description="Claude's confidence")


class DebateRound(BaseModel):
    """
    Single round of iterative comparative debate
    Tracks full state of one debate iteration
    """
    round_num: int = Field(description="Round number (1, 2, 3...)")
    gemini_answer: str = Field(description="Gemini's answer this round")
    claude_answer: str = Field(description="Claude's answer this round")
    comparison_table: List[ComparisonClaim] = Field(default_factory=list, description="Claim-by-claim comparison")
    consensus_score: float = Field(default=0.0, ge=0, le=1, description="Symmetric consensus (0-1, official metric)")
    gemini_coverage: float = Field(default=0.0, ge=0, le=1, description="Gemini's confidence-weighted coverage")
    claude_coverage: float = Field(default=0.0, ge=0, le=1, description="Claude's confidence-weighted coverage")
    avg_coverage: float = Field(default=0.0, ge=0, le=1, description="Average of the two coverages")
    new_agreements: List[str] = Field(default_factory=list, description="Newly agreed claims this round")
    disputed_points: List[str] = Field(default_factory=list, description="Still disputed claims")
    convergence_status: Literal["continue", "converged"] = Field(description="Should debate continue?")
    next_focus: Optional[str] = Field(default=None, description="What to focus on next round")


class LockedClaim(BaseModel):
    """
    A claim that both agents agreed on with high confidence
    Locked claims are not re-debated in future rounds
    """
    statement: str = Field(description="The agreed-upon statement")
    source_gemini: Optional[str] = Field(default=None)
    source_claude: Optional[str] = Field(default=None)
    locked_round: int = Field(description="Round when this was locked")
    confidence_avg: float = Field(ge=0, le=1, description="Average confidence when locked")


# ═══════════════════════════════════════════════════════════
# STRUCTURED DEBATE OUTPUT (enforced via Claude tool-use and
# Gemini response_schema — replaces free-text JSON parsing)
# ═══════════════════════════════════════════════════════════

class ComparisonClaimOutput(BaseModel):
    """One row of the claim-by-claim comparison table, as the model must emit it"""
    claim_id: int = Field(description="Unique claim number, same across both agents")
    resolution: str = Field(description="Short final statement of this claim (max ~200 chars)")
    status: Literal["agree", "conflict", "partial"] = Field(description="Agreement status")
    your_confidence: float = Field(description="Your confidence in this claim, 0.0-1.0")
    other_confidence: float = Field(description="Other agent's apparent confidence, 0.0-1.0")
    your_source: Optional[str] = Field(default=None, description="Your source URL/reference")
    other_source: Optional[str] = Field(default=None, description="Other agent's source")


class DebateComparisonOutput(BaseModel):
    """Full structured response for one debate round"""
    comparison_table: List[ComparisonClaimOutput] = Field(default_factory=list)
    consensus_score: float = Field(description="Overall agreement estimate, 0.0-1.0")
    convergence_status: Literal["continue", "converged"] = Field(
        description="'converged' only if agreement is essentially complete")
    revised_answer: str = Field(description="Your full revised answer text")
    new_agreements: List[str] = Field(default_factory=list)
    still_disputed: List[str] = Field(default_factory=list)
    next_focus: Optional[str] = Field(default=None)

    def as_round_dict(self) -> dict:
        """Normalize to the dict shape the debate loop consumes"""
        data = self.model_dump()
        data.setdefault("total_claims", len(self.comparison_table))
        data.setdefault("agreed_claims",
                        sum(1 for c in self.comparison_table if c.status == "agree"))
        return data
