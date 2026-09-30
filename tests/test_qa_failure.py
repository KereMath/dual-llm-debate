"""Tests that QA fails EXPLICITLY on errors instead of auto-approving with 85."""

import pytest

import src.agents.qa_agents as qa
from src.schemas import DebateState
from src.workflow import should_regenerate_pdf
from src.config import config


def make_state(**kwargs) -> DebateState:
    return DebateState(topic="Q?", **kwargs)


class TestVisualQA:
    def test_unparseable_response_raises_qa_failure(self, monkeypatch):
        monkeypatch.setattr(qa, "call_gemini_vision_api",
                            lambda **kw: "no json here at all")
        with pytest.raises(qa.QAFailure, match="could not parse"):
            qa.run_visual_qa([b"fake-png"])

    def test_api_error_raises_qa_failure(self, monkeypatch):
        def boom(**kw):
            raise RuntimeError("vision api down")
        monkeypatch.setattr(qa, "call_gemini_vision_api", boom)
        with pytest.raises(qa.QAFailure, match="vision api down"):
            qa.run_visual_qa([b"fake-png"])

    def test_valid_response_scores_normally(self, monkeypatch):
        monkeypatch.setattr(
            qa, "call_gemini_vision_api",
            lambda **kw: '{"score": 90, "feedback": "ok", "criteria_scores": {"layout": 23}}'
        )
        result = qa.run_visual_qa([b"fake-png"])
        assert result.score == 90
        assert result.passed is True
        assert result.layout_score == 23


class TestContentQA:
    def test_unparseable_response_raises_qa_failure(self, monkeypatch):
        monkeypatch.setattr(qa, "call_claude_api", lambda **kw: "garbage")
        with pytest.raises(qa.QAFailure, match="could not parse"):
            qa.run_content_qa("pdf text", "consensus", "question")

    def test_missing_score_field_raises_qa_failure(self, monkeypatch):
        monkeypatch.setattr(qa, "call_claude_api", lambda **kw: '{"feedback": "no score"}')
        with pytest.raises(qa.QAFailure):
            qa.run_content_qa("pdf text", "consensus", "question")


class TestQualityAssuranceNode:
    def test_missing_pdf_marks_qa_failed(self):
        state = qa.quality_assurance_node(make_state(pdf_path=None))
        assert state.qa_failed is True
        assert state.pdf_approved is False

    def test_qa_failure_sets_zero_scores_not_85(self, tmp_path, monkeypatch):
        fake_pdf = tmp_path / "report.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 fake")

        monkeypatch.setattr(qa, "pdf_to_images", lambda p: [b"img"])
        monkeypatch.setattr(qa, "extract_pdf_text", lambda p: "text")

        def failing_visual(images):
            raise qa.QAFailure("visual model returned garbage")
        monkeypatch.setattr(qa, "run_visual_qa", failing_visual)

        state = qa.quality_assurance_node(make_state(pdf_path=str(fake_pdf)))

        assert state.qa_failed is True
        assert state.visual_qa_score == 0.0
        assert state.content_qa_score == 0.0
        assert state.average_qa_score == 0.0
        assert any("QA failure" in e for e in state.errors)


class TestApprovalDecision:
    def test_qa_failed_never_approves(self):
        # Even a would-be-passing average must not be approved when QA failed
        state = make_state(qa_failed=True, average_qa_score=99.0)
        state = qa.approval_decision_node(state)
        assert state.pdf_approved is False

    def test_score_above_threshold_approves(self):
        state = make_state(average_qa_score=config.QA_THRESHOLD + 1)
        state = qa.approval_decision_node(state)
        assert state.pdf_approved is True

    def test_score_below_threshold_rejects(self):
        state = make_state(average_qa_score=config.QA_THRESHOLD - 1)
        state = qa.approval_decision_node(state)
        assert state.pdf_approved is False


class TestRegenerationDecision:
    def test_approved_ends(self):
        assert should_regenerate_pdf(make_state(pdf_approved=True)) == "end"

    def test_qa_failure_ends_without_regeneration(self):
        # Regeneration cannot fix a QA infrastructure failure
        state = make_state(pdf_approved=False, qa_failed=True, pdf_regeneration_count=0)
        assert should_regenerate_pdf(state) == "end"

    def test_low_score_triggers_regeneration(self):
        state = make_state(pdf_approved=False, pdf_regeneration_count=0)
        assert should_regenerate_pdf(state) == "pdf_revision"

    def test_regeneration_stops_at_max(self):
        state = make_state(pdf_approved=False,
                           pdf_regeneration_count=config.MAX_PDF_REGENERATIONS)
        assert should_regenerate_pdf(state) == "end"
