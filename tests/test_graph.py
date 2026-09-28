"""Tests for pytrack.core.graph — dependency graph and cycle detection."""

from pathlib import Path

from pytrack.core.graph import build_graph, detect_cycles, get_dependency_chain, get_module_dependencies
from pytrack.core.parser import parse_directory


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sample_project"


def test_build_graph_creates_nodes():
    """Every parsed module should appear as a node in the graph."""
    result = parse_directory(FIXTURES)
    graph = build_graph(result)

    assert "pkg_a" in graph.nodes
    assert "pkg_b" in graph.nodes
    assert "pkg_a.utils" in graph.nodes
    assert "pkg_b.helper" in graph.nodes


def test_build_graph_creates_edges():
    """pkg_a imports from pkg_b and vice versa — edges should exist."""
    result = parse_directory(FIXTURES)
    graph = build_graph(result)

    assert graph.has_edge("pkg_a", "pkg_b")
    assert graph.has_edge("pkg_b", "pkg_a")


def test_detect_cycles_finds_circular_dependency():
    """The fixture project has a deliberate cycle: pkg_a ↔ pkg_b."""
    result = parse_directory(FIXTURES)
    graph = build_graph(result)
    cycles = detect_cycles(graph)

    assert len(cycles) > 0

    # Flatten all cycles and check that both packages appear
    flat = {m for cycle in cycles for m in cycle}
    assert "pkg_a" in flat
    assert "pkg_b" in flat


def test_detect_cycles_empty_on_acyclic():
    """An empty graph should have no cycles."""
    import networkx as nx

    graph = nx.DiGraph()
    graph.add_edge("a", "b")
    graph.add_edge("b", "c")

    cycles = detect_cycles(graph)
    assert cycles == []


def test_get_module_dependencies():
    """Direct dependencies of pkg_a should include pkg_b."""
    result = parse_directory(FIXTURES)
    graph = build_graph(result)

    deps = get_module_dependencies(graph, "pkg_a")
    assert "pkg_b" in deps


def test_get_dependency_chain():
    """Transitive deps of pkg_a should include pkg_b (and vice versa)."""
    result = parse_directory(FIXTURES)
    graph = build_graph(result)

    chain = get_dependency_chain(graph, "pkg_a")
    assert "pkg_b" in chain


def test_get_dependency_chain_unknown_module():
    """Querying an unknown module should return an empty list."""
    result = parse_directory(FIXTURES)
    graph = build_graph(result)

    assert get_dependency_chain(graph, "nonexistent") == []
