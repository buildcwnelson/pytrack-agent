"""Tests for pytrack.agent.tools — Agno toolkit functions."""

from pathlib import Path

from pytrack.agent.tools import ArchitectureToolkit
from pytrack.core.graph import build_graph
from pytrack.core.parser import parse_directory


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sample_project"


def _make_toolkit() -> ArchitectureToolkit:
    """Helper: build the graph and return an initialized toolkit."""
    result = parse_directory(FIXTURES)
    graph = build_graph(result)
    return ArchitectureToolkit(graph=graph, root_dir=FIXTURES)


def test_get_module_source_reads_file():
    """get_module_source should return the source code of a valid file."""
    toolkit = _make_toolkit()
    source = toolkit.get_module_source("pkg_a/utils.py")
    assert "def compute" in source


def test_get_module_source_nonexistent_file():
    """get_module_source should return an error for a missing file."""
    toolkit = _make_toolkit()
    result = toolkit.get_module_source("nonexistent.py")
    assert result.startswith("Error:")


def test_get_module_source_outside_root():
    """get_module_source should refuse paths outside the project root."""
    toolkit = _make_toolkit()
    result = toolkit.get_module_source("/etc/passwd")
    assert result.startswith("Error:")


def test_get_module_source_non_python_file():
    """get_module_source should refuse non-.py files."""
    toolkit = _make_toolkit()
    result = toolkit.get_module_source("README.md")
    assert result.startswith("Error:")


def test_get_dependency_chain_known_module():
    """get_dependency_chain should return deps for a known module."""
    toolkit = _make_toolkit()
    chain = toolkit.get_dependency_chain("pkg_a")
    assert isinstance(chain, list)
    assert "pkg_b" in chain


def test_get_dependency_chain_unknown_module():
    """get_dependency_chain should return an empty list for unknown modules."""
    toolkit = _make_toolkit()
    chain = toolkit.get_dependency_chain("unknown_module")
    assert chain == []
