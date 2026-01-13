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

    gemini_critique: str = Field(default="", description="Explorer's critique of Judge")
    claude_critique: str = Field(default="", description="Judge's critique of Explorer")

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

    class Config:
        arbitrary_types_allowed = True


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
    """
    completeness_score: float = Field(default=0.0, ge=0, le=30)
    citation_score: float = Field(default=0.0, ge=0, le=30)
    structure_score: float = Field(default=0.0, ge=0, le=20)
    academic_score: float = Field(default=0.0, ge=0, le=20)
