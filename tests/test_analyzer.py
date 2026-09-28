"""Tests for pytrack.agent.analyzer — agent creation and configuration."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pytrack.agent.analyzer import SYSTEM_INSTRUCTIONS, analyze_cycles, create_analyzer_agent
from pytrack.core.graph import build_graph
from pytrack.core.parser import parse_directory
from pytrack.models.schemas import RefactoringRoadmap


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sample_project"


def _build_test_graph():
    """Helper: parse fixtures and build graph."""
    result = parse_directory(FIXTURES)
    return build_graph(result)


def test_create_analyzer_agent_returns_agent():
    """create_analyzer_agent should return an Agno Agent."""
    from agno.agent import Agent

    graph = _build_test_graph()
    agent = create_analyzer_agent(graph, FIXTURES, model_id="llama3")
    assert isinstance(agent, Agent)


def test_create_analyzer_agent_has_tools():
    """The agent should have the architecture toolkit registered."""
    graph = _build_test_graph()
    agent = create_analyzer_agent(graph, FIXTURES)

    # The agent should have tools configured
    assert agent.tools is not None
    assert len(agent.tools) > 0


def test_create_analyzer_agent_has_output_schema():
    """The agent should have RefactoringRoadmap as its output schema."""
    graph = _build_test_graph()
    agent = create_analyzer_agent(graph, FIXTURES)
    assert agent.output_schema == RefactoringRoadmap


def test_create_analyzer_agent_has_instructions():
    """The agent should have the system instructions set."""
    graph = _build_test_graph()
    agent = create_analyzer_agent(graph, FIXTURES)
    assert agent.instructions is not None
    assert any(SYSTEM_INSTRUCTIONS in instr for instr in agent.instructions)


def test_create_analyzer_agent_custom_model():
    """Should support custom Ollama model IDs."""
    graph = _build_test_graph()
    agent = create_analyzer_agent(graph, FIXTURES, model_id="qwen2.5-coder")
    assert agent.model.id == "qwen2.5-coder"


@pytest.mark.asyncio
async def test_analyze_cycles_empty():
    """analyze_cycles should return None for empty cycle list."""
    graph = _build_test_graph()
    agent = create_analyzer_agent(graph, FIXTURES)
    result = await analyze_cycles(agent, [])
    assert result is None


@pytest.mark.asyncio
async def test_analyze_cycles_with_mocked_agent():
    """analyze_cycles should return a RefactoringRoadmap when the agent succeeds."""
    graph = _build_test_graph()
    agent = create_analyzer_agent(graph, FIXTURES)

    mock_roadmap = RefactoringRoadmap(
        architecture_score=35,
        findings=[
            "Circular dependency between pkg_a and pkg_b",
            "pkg_a.__init__ imports helper from pkg_b",
            "pkg_b.__init__ imports utils from pkg_a",
        ],
        actionable_steps=[
            "Extract shared types into a new pkg_common module",
            "Update pkg_a to import from pkg_common instead of pkg_b",
            "Update pkg_b to import from pkg_common instead of pkg_a",
        ],
    )

    mock_response = MagicMock()
    mock_response.content = mock_roadmap

    with patch.object(agent, "arun", new_callable=AsyncMock, return_value=mock_response):
        result = await analyze_cycles(agent, [["pkg_a", "pkg_b"]])

    assert result is not None
    assert isinstance(result, RefactoringRoadmap)
    assert result.architecture_score == 35
    assert len(result.findings) == 3
    assert len(result.actionable_steps) == 3
