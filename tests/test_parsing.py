"""Tests for debate response parsing (JSON + revised answer extraction)."""

from src.phases.phase_3_4_iterative_debate import parse_comparison_response


VALID_RESPONSE = '''Here is my comparison:

```json
{
  "comparison_table": [
    {"claim_id": 1, "status": "agree", "your_confidence": 0.9, "other_confidence": 0.85}
  ],
  "consensus_score": 0.75,
  "total_claims": 4,
  "agreed_claims": 3,
  "convergence_status": "continue"
}
```

=== REVISED ANSWER ===
This is my revised answer.
=== END ===
'''


class TestValidResponse:
    def test_parses_json_and_revised_answer(self):
        data = parse_comparison_response(VALID_RESPONSE)
        assert data["consensus_score"] == 0.75
        assert data["convergence_status"] == "continue"
        assert len(data["comparison_table"]) == 1
        assert data["revised_answer"] == "This is my revised answer."

    def test_trailing_commas_are_cleaned(self):
        response = '''```json
{"comparison_table": [{"claim_id": 1, "status": "agree",},], "consensus_score": 0.8, "convergence_status": "continue",}
```
=== REVISED ANSWER ===
Answer text.
=== END ===
'''
        data = parse_comparison_response(response)
        assert data["consensus_score"] == 0.8
        assert data["revised_answer"] == "Answer text."

    def test_missing_optional_fields_get_defaults(self):
        response = '''```json
{"consensus_score": 0.6, "convergence_status": "continue"}
```
=== REVISED ANSWER ===
Short.
=== END ===
'''
        data = parse_comparison_response(response)
        assert data["comparison_table"] == []
        assert data["new_agreements"] == []
        assert data["still_disputed"] == []


class TestMalformedResponse:
    def test_fallback_extracts_score_from_broken_json(self):
        response = '''```json
{"consensus_score": 0.65, "this json is broken
```
=== REVISED ANSWER ===
Fallback answer.
=== END ===
'''
        data = parse_comparison_response(response)
        assert data["consensus_score"] == 0.65
        assert data["revised_answer"] == "Fallback answer."
        assert data["convergence_status"] == "continue"

    def test_fallback_converts_percentage_to_fraction(self):
        response = '```json\n{broken json, consensus: 47%\n```'
        data = parse_comparison_response(response)
        assert data["consensus_score"] == 0.47

    def test_total_garbage_defaults_to_half_consensus(self):
        data = parse_comparison_response("complete garbage, no json at all")
        assert data["consensus_score"] == 0.5
        assert data["convergence_status"] == "continue"
        # Raw text preserved as the answer so the round is not lost
        assert "complete garbage" in data["revised_answer"]
