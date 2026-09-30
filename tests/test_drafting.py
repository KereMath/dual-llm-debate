"""Tests that parallel drafting fails EXPLICITLY when either draft fails.

A debate against an '[ERROR] ...' placeholder string is meaningless, so a
failed draft must abort the pipeline instead of being silently swallowed.
"""

import pytest

import src.phases.phase_2_parallel_drafting as phase2
from src.schemas import DebateState


def make_state() -> DebateState:
    return DebateState(topic="Q?", shared_context="context")


async def ok(prompt, system_prompt):
    return "a fine draft"


async def boom(prompt, system_prompt):
    raise RuntimeError("api down")


class TestParallelDrafting:
    def test_both_drafts_succeed(self, monkeypatch):
        monkeypatch.setattr(phase2, "call_gemini_async", ok)
        monkeypatch.setattr(phase2, "call_claude_async", ok)
        state = phase2.phase_2_parallel_drafting_sync(make_state())
        assert state.gemini_draft == "a fine draft"
        assert state.claude_draft == "a fine draft"

    def test_gemini_failure_aborts_run(self, monkeypatch):
        monkeypatch.setattr(phase2, "call_gemini_async", boom)
        monkeypatch.setattr(phase2, "call_claude_async", ok)
        with pytest.raises(RuntimeError, match="without both drafts"):
            phase2.phase_2_parallel_drafting_sync(make_state())

    def test_claude_failure_aborts_run(self, monkeypatch):
        monkeypatch.setattr(phase2, "call_gemini_async", ok)
        monkeypatch.setattr(phase2, "call_claude_async", boom)
        with pytest.raises(RuntimeError, match="without both drafts"):
            phase2.phase_2_parallel_drafting_sync(make_state())

    def test_missing_context_aborts_run(self):
        state = DebateState(topic="Q?", shared_context="")
        with pytest.raises(Exception):
            phase2.phase_2_parallel_drafting_sync(state)
