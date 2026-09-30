"""Tests for the canonical claim inventory (the real fix for claim-ID
alignment: one shared numbered list both agents evaluate)."""

import pytest

import src.phases.phase_3_4_iterative_debate as debate
from src.schemas import DebateState, InventoryClaim


def make_state(**kwargs) -> DebateState:
    state = DebateState(
        topic="Q?",
        shared_context="ctx",
        gemini_draft="gemini draft",
        claude_draft="claude draft",
        **kwargs,
    )
    return state


INVENTORY_PAYLOAD = {
    "claims": [
        {"claim_id": 1, "statement": "Water boils at 100C at sea level"},
        {"claim_id": 2, "statement": "The boiling point drops at altitude"},
    ]
}


class TestEnsureClaimInventory:
    def test_extraction_populates_state(self, monkeypatch):
        captured = {}

        def fake_structured(**kw):
            captured.update(kw)
            return INVENTORY_PAYLOAD

        monkeypatch.setattr(debate, "call_claude_structured", fake_structured)
        state = debate.ensure_claim_inventory(make_state())

        assert [c.claim_id for c in state.claim_inventory] == [1, 2]
        # Extraction must be deterministic and see both drafts
        assert captured["temperature"] == 0.0
        assert "gemini draft" in captured["prompt"]
        assert "claude draft" in captured["prompt"]

    def test_failure_falls_back_to_no_inventory(self, monkeypatch):
        def boom(**kw):
            raise RuntimeError("api down")

        monkeypatch.setattr(debate, "call_claude_structured", boom)
        state = debate.ensure_claim_inventory(make_state())

        assert state.claim_inventory == []
        assert any("inventory" in e.lower() for e in state.errors)

    def test_duplicate_ids_and_empty_statements_dropped(self, monkeypatch):
        payload = {"claims": [
            {"claim_id": 1, "statement": "A"},
            {"claim_id": 1, "statement": "duplicate id"},
            {"claim_id": 2, "statement": "   "},
            {"claim_id": 3, "statement": "C"},
        ]}
        monkeypatch.setattr(debate, "call_claude_structured", lambda **kw: payload)
        state = debate.ensure_claim_inventory(make_state())
        assert [(c.claim_id, c.statement) for c in state.claim_inventory] == [(1, "A"), (3, "C")]

    def test_existing_inventory_not_reextracted(self, monkeypatch):
        def boom(**kw):
            raise AssertionError("must not re-extract")
        monkeypatch.setattr(debate, "call_claude_structured", boom)
        state = make_state()
        state.claim_inventory = [InventoryClaim(claim_id=1, statement="S")]
        debate.ensure_claim_inventory(state)  # no exception = pass


class TestInventoryDrivenLocking:
    def make_row(self, claim_id, resolution, conf=0.95):
        return {"claim_id": claim_id, "status": "agree", "your_confidence": conf,
                "resolution": resolution, "your_source": None}

    def test_inventory_id_locks_with_canonical_text(self):
        # Differently-worded resolutions would fail the similarity guard,
        # but a shared INVENTORY id is the same claim by construction —
        # and the canonical statement is what gets locked
        inventory = {1: "Water boils at 100C at sea level"}
        gemini = [self.make_row(1, "H2O reaches boiling at one hundred degrees")]
        claude = [self.make_row(1, "Sea-level boiling temperature is 100 Celsius")]

        locked = debate.identify_lockable_claims(gemini, claude, round_num=1,
                                                 inventory_map=inventory)
        assert len(locked) == 1
        assert locked[0].statement == "Water boils at 100C at sea level"

    def test_non_inventory_id_still_guarded(self):
        inventory = {1: "Water boils at 100C at sea level"}
        gemini = [self.make_row(7, "Water boils at 100C at sea level")]
        claude = [self.make_row(7, "The Eiffel Tower is located in Paris France")]
        locked = debate.identify_lockable_claims(gemini, claude, round_num=1,
                                                 inventory_map=inventory)
        assert locked == []

    def test_symmetric_consensus_trusts_inventory_ids(self):
        gemini = [self.make_row(1, "phrasing one", conf=1.0)]
        claude = [self.make_row(1, "a completely different phrasing", conf=1.0)]
        # Without inventory the mismatched texts are skipped...
        assert debate.calculate_symmetric_consensus(gemini, claude) == 0.0
        # ...with the id in the inventory, the pair counts
        assert debate.calculate_symmetric_consensus(gemini, claude,
                                                    inventory_ids={1}) == 1.0


class TestNoDuplicateLocks:
    def test_relocked_statement_not_duplicated(self, monkeypatch):
        # Agents re-agreeing on an already-locked canonical claim in a later
        # round must not create a duplicate entry
        payload = {
            "comparison_table": [{
                "claim_id": 1, "resolution": "Canonical S", "status": "agree",
                "your_confidence": 0.95, "other_confidence": 0.9,
            }],
            "consensus_score": 0.5,
            "convergence_status": "continue",
            "revised_answer": "ans",
        }
        monkeypatch.setattr(debate, "call_gemini_structured", lambda **kw: payload)
        monkeypatch.setattr(debate, "call_claude_structured", lambda **kw: payload)

        state = make_state(max_rounds=2)
        state.claim_inventory = [InventoryClaim(claim_id=1, statement="Canonical S")]

        state = debate.run_iterative_debate_round(state, round_num=1)
        assert len(state.locked_agreements) == 1
        state = debate.run_iterative_debate_round(state, round_num=2)
        assert len(state.locked_agreements) == 1  # still one, not two


class TestInventoryFiltering:
    def test_invented_ids_are_discarded(self):
        table = [{"claim_id": 1}, {"claim_id": 99}, {"claim_id": 2}]
        kept = debate.filter_to_inventory_ids(table, {1, 2}, "TestAgent")
        assert [c["claim_id"] for c in kept] == [1, 2]

    def test_no_inventory_keeps_table_untouched(self):
        table = [{"claim_id": 99}]
        assert debate.filter_to_inventory_ids(table, set(), "TestAgent") == table


class TestHandshakeIncludesInventory:
    def test_inventory_rendered_into_prompt(self):
        prompt = debate.build_handshake_prompt(
            agent_name="A", topic="Q?", shared_context="ctx",
            own_previous="own", other_previous="other",
            locked_agreements=[], disputed_points=[], round_num=1,
            collaborative_instruction="",
            claim_inventory=[InventoryClaim(claim_id=1, statement="Canonical S")],
        )
        assert "CANONICAL CLAIM INVENTORY" in prompt
        assert "1. Canonical S" in prompt
