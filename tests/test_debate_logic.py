"""Tests for the iterative debate's consensus math and claim locking."""

import pytest

from src.phases.phase_3_4_iterative_debate import (
    get_progressive_confidence_threshold,
    calculate_weighted_consensus,
    calculate_symmetric_consensus,
    identify_lockable_claims,
)


class TestProgressiveThreshold:
    def test_rises_per_round(self):
        assert get_progressive_confidence_threshold(1) == 0.70
        assert get_progressive_confidence_threshold(2) == 0.80
        assert get_progressive_confidence_threshold(3) == 0.85
        assert get_progressive_confidence_threshold(5) == 0.85


class TestWeightedConsensus:
    def test_empty_table_is_zero(self):
        assert calculate_weighted_consensus([]) == 0.0

    def test_full_agreement_full_confidence(self):
        table = [
            {"status": "agree", "your_confidence": 1.0, "other_confidence": 1.0},
            {"status": "agree", "your_confidence": 1.0, "other_confidence": 1.0},
        ]
        assert calculate_weighted_consensus(table) == 1.0

    def test_partial_counts_half(self):
        table = [{"status": "partial", "your_confidence": 1.0, "other_confidence": 1.0}]
        assert calculate_weighted_consensus(table) == 0.5

    def test_conflict_counts_zero(self):
        table = [{"status": "conflict", "your_confidence": 1.0, "other_confidence": 1.0}]
        assert calculate_weighted_consensus(table) == 0.0

    def test_agreement_weighted_by_confidence(self):
        table = [{"status": "agree", "your_confidence": 0.6, "other_confidence": 0.8}]
        assert calculate_weighted_consensus(table) == pytest.approx(0.7)


class TestSymmetricConsensus:
    def test_empty_tables_are_zero(self):
        assert calculate_symmetric_consensus([], []) == 0.0
        assert calculate_symmetric_consensus([{"claim_id": 1}], []) == 0.0

    def test_only_intersection_counts(self):
        gemini = [
            {"claim_id": 1, "status": "agree", "your_confidence": 1.0},
            {"claim_id": 2, "status": "agree", "your_confidence": 1.0},  # not in Claude's table
        ]
        claude = [{"claim_id": 1, "status": "agree", "other_confidence": 1.0}]
        assert calculate_symmetric_consensus(gemini, claude) == 1.0

    def test_both_must_agree_for_full_weight(self):
        gemini = [{"claim_id": 1, "status": "agree", "your_confidence": 1.0}]
        claude = [{"claim_id": 1, "status": "conflict", "other_confidence": 1.0}]
        assert calculate_symmetric_consensus(gemini, claude) == 0.0

    def test_partial_from_either_side_counts_half(self):
        gemini = [{"claim_id": 1, "status": "partial", "your_confidence": 1.0}]
        claude = [{"claim_id": 1, "status": "agree", "other_confidence": 1.0}]
        assert calculate_symmetric_consensus(gemini, claude) == 0.5


class TestClaimLocking:
    def make_tables(self, g_conf, c_conf, g_status="agree", c_status="agree"):
        gemini = [{
            "claim_id": 1,
            "status": g_status,
            "your_confidence": g_conf,
            "resolution": "Locked statement",
            "your_source": "https://example.com/g",
        }]
        claude = [{
            "claim_id": 1,
            "status": c_status,
            "other_confidence": c_conf,
            "your_source": "https://example.com/c",
        }]
        return gemini, claude

    def test_locks_when_both_agree_above_threshold(self):
        gemini, claude = self.make_tables(0.9, 0.9)
        locked = identify_lockable_claims(gemini, claude, round_num=1)
        assert len(locked) == 1
        assert locked[0].statement == "Locked statement"
        assert locked[0].locked_round == 1
        assert locked[0].confidence_avg == pytest.approx(0.9)

    def test_no_lock_below_round_threshold(self):
        # 0.75 passes round 1 (0.70) but not round 2 (0.80)
        gemini, claude = self.make_tables(0.75, 0.75)
        assert len(identify_lockable_claims(gemini, claude, round_num=1)) == 1
        assert len(identify_lockable_claims(gemini, claude, round_num=2)) == 0

    def test_no_lock_on_partial_status(self):
        gemini, claude = self.make_tables(0.95, 0.95, g_status="partial")
        assert identify_lockable_claims(gemini, claude, round_num=1) == []

    def test_no_lock_when_claim_missing_from_one_table(self):
        gemini, _ = self.make_tables(0.95, 0.95)
        assert identify_lockable_claims(gemini, [], round_num=1) == []
