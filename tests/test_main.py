"""Tests for pytrack.main — integration pipeline."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pytrack.main import AnalysisResult, run_analysis
from pytrack.models.schemas import RefactoringRoadmap


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sample_project"


async def test_run_analysis_finds_cycles():
    """The pipeline should detect cycles in the fixture project."""
    result = await run_analysis(
        target_dir=FIXTURES,
        enable_tracing=False,  # Don't require Phoenix for tests
    )

    assert isinstance(result, AnalysisResult)
    assert result.module_count > 0
    assert len(result.cycles) > 0


async def test_run_analysis_module_count():
    """The pipeline should count all modules in the fixture project."""
    result = await run_analysis(
        target_dir=FIXTURES,
        enable_tracing=False,
    )

    # pkg_a, pkg_a.utils, pkg_b, pkg_b.helper = 4 modules
    assert result.module_count == 4


async def test_run_analysis_no_parse_errors():
    """The fixture project has valid Python — no parse errors expected."""
    result = await run_analysis(
        target_dir=FIXTURES,
        enable_tracing=False,
    )

    assert len(result.parse_errors) == 0


async def test_run_analysis_with_mocked_agent():
    """Pipeline should produce a roadmap when the agent succeeds."""
    mock_roadmap = RefactoringRoadmap(
        architecture_score=30,
        findings=["Circular dependency between pkg_a and pkg_b"],
        actionable_steps=["Extract shared code into pkg_common"],
    )

    mock_response = MagicMock()
    mock_response.content = mock_roadmap

    with patch("pytrack.main.create_analyzer_agent") as mock_create:
        mock_agent = MagicMock()
        mock_agent.arun = AsyncMock(return_value=mock_response)
        mock_create.return_value = mock_agent

        result = await run_analysis(
            target_dir=FIXTURES,
            enable_tracing=False,
        )

    assert result.roadmap is not None
    assert result.roadmap.architecture_score == 30


async def test_run_analysis_agent_failure_handled():
    """Pipeline should handle agent failures gracefully."""
    with patch("pytrack.main.create_analyzer_agent") as mock_create:
        mock_agent = MagicMock()
        mock_agent.arun = AsyncMock(side_effect=RuntimeError("Ollama not running"))
        mock_create.return_value = mock_agent

        result = await run_analysis(
            target_dir=FIXTURES,
            enable_tracing=False,
        )

    # Should still return a result with cycles but no roadmap
    assert len(result.cycles) > 0
    assert result.roadmap is None
