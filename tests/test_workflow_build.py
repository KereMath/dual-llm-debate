"""Smoke test: the LangGraph workflow compiles with all nodes wired."""

from src.workflow import build_research_workflow


def test_workflow_graph_compiles():
    workflow = build_research_workflow()
    assert workflow is not None
