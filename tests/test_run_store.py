"""Tests for local run persistence (results must survive UI refreshes)."""

from datetime import datetime

import src.run_store as run_store
from src.schemas import DebateState, LockedClaim


def make_state() -> DebateState:
    state = DebateState(topic="Kalıcılık testi: fotosentez?", research_mode="offline")
    state.consensus_report = "# Report"
    state.average_qa_score = 80.0
    state.start_time = datetime.now()
    state.end_time = datetime.now()
    state.locked_agreements = [
        LockedClaim(statement="S", locked_round=1, confidence_avg=0.9)
    ]
    return state


class TestRunStore:
    def test_save_load_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.setattr(run_store, "RUNS_DIR", tmp_path)
        path = run_store.save_run(make_state())
        assert path is not None and path.exists()

        loaded = run_store.load_run(path)
        assert loaded is not None
        assert loaded.topic == "Kalıcılık testi: fotosentez?"
        assert loaded.consensus_report == "# Report"
        assert loaded.locked_agreements[0].statement == "S"

    def test_list_runs_newest_first(self, tmp_path, monkeypatch):
        monkeypatch.setattr(run_store, "RUNS_DIR", tmp_path)
        (tmp_path / "20260101_000000_a.json").write_text("{}", encoding="utf-8")
        (tmp_path / "20260201_000000_b.json").write_text("{}", encoding="utf-8")
        runs = run_store.list_runs()
        assert [p.name for p in runs] == ["20260201_000000_b.json", "20260101_000000_a.json"]

    def test_load_invalid_file_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.setattr(run_store, "RUNS_DIR", tmp_path)
        bad = tmp_path / "20260101_000000_bad.json"
        bad.write_text("not json", encoding="utf-8")
        assert run_store.load_run(bad) is None

    def test_run_label_is_readable(self):
        label = run_store.run_label(run_store.Path("20260930_141200_fotosentez-nedir.json"))
        assert label == "2026-09-30 14:12 · fotosentez nedir"

    def test_slug_handles_unicode_topics(self, tmp_path, monkeypatch):
        monkeypatch.setattr(run_store, "RUNS_DIR", tmp_path)
        state = make_state()
        state.topic = "Çok özel karakterli / soru: %100 ölçüm?"
        path = run_store.save_run(state)
        assert path is not None and path.exists()
