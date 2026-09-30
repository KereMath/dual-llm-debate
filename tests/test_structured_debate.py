"""Tests for the schema-enforced debate round (structured outputs first,
free-text parsing only as fallback)."""

import pytest

import src.phases.phase_3_4_iterative_debate as debate
from src.schemas import DebateState, DebateComparisonOutput


def make_state() -> DebateState:
    return DebateState(
        topic="Q?",
        shared_context="Source [1]: something",
        gemini_draft="gemini draft",
        claude_draft="claude draft",
        max_rounds=1,
    )


def structured_payload(answer: str) -> dict:
    return {
        "comparison_table": [
            {
                "claim_id": 1,
                "resolution": "Both agree on the core claim",
                "status": "agree",
                "your_confidence": 0.95,
                "other_confidence": 0.9,
                "your_source": "https://example.com/a",
            }
        ],
        "consensus_score": 0.95,
        "convergence_status": "converged",
        "revised_answer": answer,
        "new_agreements": ["core claim"],
        "still_disputed": [],
    }


class TestSchema:
    def test_as_round_dict_fills_derived_fields(self):
        out = DebateComparisonOutput.model_validate(structured_payload("A"))
        d = out.as_round_dict()
        assert d["total_claims"] == 1
        assert d["agreed_claims"] == 1
        assert d["comparison_table"][0]["resolution"] == "Both agree on the core claim"

    def test_schema_rejects_bad_status(self):
        bad = structured_payload("A")
        bad["comparison_table"][0]["status"] = "maybe"
        with pytest.raises(Exception):
            DebateComparisonOutput.model_validate(bad)


class TestStructuredRound:
    def test_round_uses_structured_outputs_without_text_parsing(self, monkeypatch):
        monkeypatch.setattr(debate, "call_gemini_structured",
                            lambda **kw: structured_payload("gemini revised"))
        monkeypatch.setattr(debate, "call_claude_structured",
                            lambda **kw: structured_payload("claude revised"))

        def no_text_calls(**kw):
            raise AssertionError("text-mode API must not be called when structured succeeds")
        monkeypatch.setattr(debate, "call_gemini_api", no_text_calls)
        monkeypatch.setattr(debate, "call_claude_api", no_text_calls)

        state = debate.run_iterative_debate_round(make_state(), round_num=1)

        assert state.debate_rounds[0].gemini_answer == "gemini revised"
        assert state.debate_rounds[0].claude_answer == "claude revised"
        # High-confidence mutual agreement got locked with real text
        assert len(state.locked_agreements) == 1
        assert state.locked_agreements[0].statement == "Both agree on the core claim"
        # Real coverage math ran (not the 0.5 parse fallback)
        assert state.debate_rounds[0].gemini_coverage > 0.9

    def test_falls_back_to_text_mode_when_structured_fails(self, monkeypatch):
        def boom(**kw):
            raise RuntimeError("schema not supported")
        monkeypatch.setattr(debate, "call_gemini_structured", boom)
        monkeypatch.setattr(debate, "call_claude_structured", boom)

        text_response = '''```json
{"comparison_table": [{"claim_id": 1, "resolution": "R", "status": "agree", "your_confidence": 0.9, "other_confidence": 0.9}], "consensus_score": 0.9, "convergence_status": "continue"}
```
=== REVISED ANSWER ===
text-mode answer
=== END ===
'''
        monkeypatch.setattr(debate, "call_gemini_api", lambda **kw: text_response)
        monkeypatch.setattr(debate, "call_claude_api", lambda **kw: text_response)

        state = debate.run_iterative_debate_round(make_state(), round_num=1)

        assert state.debate_rounds[0].gemini_answer == "text-mode answer"
        assert len(state.locked_agreements) == 1
