"""Tests for pytrack.cli — Typer CLI interface and Rich rendering."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from pytrack.cli import app
from pytrack.main import AnalysisResult
from pytrack.models.schemas import RefactoringRoadmap

runner = CliRunner()
FIXTURES = str(Path(__file__).resolve().parent / "fixtures" / "sample_project")


def test_cli_analyze_no_ai():
    """pytrack --no-ai should run without the AI agent."""
    result = runner.invoke(app, ["--path", FIXTURES, "--no-ai"])
    assert result.exit_code == 0
    assert "Circular Dependencies" in result.output or "No circular" in result.output


def test_cli_analyze_shows_cycle_detection():
    """The CLI should display cycle detection results."""
    result = runner.invoke(app, ["--path", FIXTURES, "--no-ai"])
    assert result.exit_code == 0
    # The fixture has circular dependencies
    assert "Cycle" in result.output


def test_cli_analyze_invalid_path():
    """An invalid path should exit with code 1."""
    result = runner.invoke(app, ["--path", "/nonexistent/path"])
    assert result.exit_code == 1
    assert "Error" in result.output


def test_cli_analyze_with_mocked_ai():
    """Full CLI run with mocked AI agent should render the roadmap."""
    mock_roadmap = RefactoringRoadmap(
        architecture_score=45,
        findings=[
            "Circular dependency between pkg_a and pkg_b",
            "pkg_a.__init__.py imports from pkg_b at module level",
        ],
        actionable_steps=[
            "Create a new pkg_common module for shared types",
            "Move shared interfaces to pkg_common",
            "Update imports in pkg_a and pkg_b to use pkg_common",
        ],
    )

    mock_result = AnalysisResult(
        target_dir=FIXTURES,
        module_count=4,
        edge_count=2,
        cycles=[["pkg_a", "pkg_b"]],
        roadmap=mock_roadmap,
        tracing_enabled=False,
    )

    with patch("pytrack.cli.run_analysis", new_callable=AsyncMock, return_value=mock_result):
        result = runner.invoke(
            app,
            ["--path", FIXTURES, "--model", "llama3", "--no-tracing"],
        )

    assert result.exit_code == 0
    assert "45/100" in result.output
    assert "Findings" in result.output
    assert "Refactoring Roadmap" in result.output


def test_cli_analyze_renders_module_count():
    """The header should show the module count."""
    result = runner.invoke(app, ["--path", FIXTURES, "--no-ai"])
    assert result.exit_code == 0
    assert "4" in result.output  # 4 modules in fixtures


def test_cli_help():
    """The help command should show available options."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "--path" in result.output
    assert "--model" in result.output
    assert "--no-ai" in result.output
    assert "--no-tracing" in result.output
