"""Smoke test: the Streamlit app script runs without exceptions."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def test_app_renders_without_errors():
    at = AppTest.from_file(str(APP_PATH), default_timeout=30)
    at.run()
    assert not at.exception, f"App raised: {at.exception}"
    # Title and the primary input are present
    assert at.title[0].value.endswith("Dual-LLM Research Debate")
    assert len(at.text_input) == 1
    assert len(at.button) >= 1
