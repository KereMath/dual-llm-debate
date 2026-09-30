"""Tests that intersection synthesis consumes the DEBATE's output:
locked claims + final revised answers, not the pre-debate drafts."""

import pytest

import src.phases.phase_5_intersection as phase5
from src.schemas import DebateState, DebateRound, LockedClaim


def make_state(with_debate_round: bool = True) -> DebateState:
    state = DebateState(
        topic="Test question?",
        shared_context="Source [1]: something",
        gemini_draft="ORIGINAL_GEMINI_DRAFT",
        claude_draft="ORIGINAL_CLAUDE_DRAFT",
    )
    state.locked_agreements = [
        LockedClaim(
            statement="LOCKED_CLAIM_STATEMENT",
            source_gemini="https://example.com/a",
            source_claude="https://example.com/b",
            locked_round=1,
            confidence_avg=0.9,
        )
    ]
    state.current_disputed_points = ["DISPUTED_POINT_X"]

    if with_debate_round:
        state.add_debate_round(DebateRound(
            round_num=2,
            gemini_answer="REVISED_GEMINI_ANSWER",
            claude_answer="REVISED_CLAUDE_ANSWER",
            consensus_score=0.9,
            convergence_status="continue",
        ))

    return state


class TestSynthesisInputs:
    def test_feeds_locked_claims_and_revised_answers(self, monkeypatch):
        captured = {}

        def fake_claude(prompt, system_prompt, temperature=None, max_tokens=None):
            captured["prompt"] = prompt
            return "CONSENSUS_TEXT"

        monkeypatch.setattr(phase5, "call_claude_api", fake_claude)

        state = phase5.phase_5_intersection_synthesis(make_state())
        prompt = captured["prompt"]

        # The debate's output IS the synthesizer's input
        assert "LOCKED_CLAIM_STATEMENT" in prompt
        assert "REVISED_GEMINI_ANSWER" in prompt
        assert "REVISED_CLAUDE_ANSWER" in prompt
        assert "DISPUTED_POINT_X" in prompt
        # Locked claims keep their sources
        assert "https://example.com/a" in prompt

        # The pre-debate drafts are NOT what gets synthesized
        assert "ORIGINAL_GEMINI_DRAFT" not in prompt
        assert "ORIGINAL_CLAUDE_DRAFT" not in prompt

        assert state.consensus_report == "CONSENSUS_TEXT"

    def test_report_language_setting_reaches_the_prompt(self, monkeypatch):
        captured = {}

        def fake_claude(prompt, system_prompt, temperature=None, max_tokens=None):
            captured["prompt"] = prompt
            return "OK"

        monkeypatch.setattr(phase5, "call_claude_api", fake_claude)

        state = make_state()  # default: auto
        phase5.phase_5_intersection_synthesis(state)
        assert "SAME language as the research question" in captured["prompt"]

        state.report_language = "en"
        phase5.phase_5_intersection_synthesis(state)
        assert "ENTIRE report in ENGLISH" in captured["prompt"]

        state.report_language = "tr"
        phase5.phase_5_intersection_synthesis(state)
        assert "ALL prose in TURKISH" in captured["prompt"]

    def test_falls_back_to_drafts_when_no_debate_round(self, monkeypatch):
        captured = {}

        def fake_claude(prompt, system_prompt, temperature=None, max_tokens=None):
            captured["prompt"] = prompt
            return "OK"

        monkeypatch.setattr(phase5, "call_claude_api", fake_claude)

        phase5.phase_5_intersection_synthesis(make_state(with_debate_round=False))

        # Without debate rounds the only available answers are the drafts
        assert "ORIGINAL_GEMINI_DRAFT" in captured["prompt"]
        assert "ORIGINAL_CLAUDE_DRAFT" in captured["prompt"]


class TestSynthesisFailure:
    def test_fallback_report_lists_locked_claims_and_error(self, monkeypatch):
        def failing_claude(prompt, system_prompt, temperature=None, max_tokens=None):
            raise RuntimeError("api down")

        monkeypatch.setattr(phase5, "call_claude_api", failing_claude)

        state = phase5.phase_5_intersection_synthesis(make_state())

        assert state.errors, "synthesis failure must be recorded in the error log"
        # Explicit flag: the run must never end "approved" on a degraded report
        assert state.synthesis_failed is True
        assert "api down" in state.consensus_report
        # Even the degraded report is built from the dual-verified claims
        assert "LOCKED_CLAIM_STATEMENT" in state.consensus_report


class TestLockedClaimFormatting:
    def test_empty_list_notes_no_locked_claims(self):
        text = phase5.format_locked_claims_for_synthesis([])
        assert "kilitleyemedi" in text

    def test_deduplicates_identical_sources(self):
        claim = LockedClaim(
            statement="S",
            source_gemini="https://same.url",
            source_claude="https://same.url",
            locked_round=1,
            confidence_avg=0.8,
        )
        text = phase5.format_locked_claims_for_synthesis([claim])
        assert text.count("https://same.url") == 1
