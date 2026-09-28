"""Dependency graph construction and cycle detection using NetworkX.

Converts parsed import records into a directed graph and exposes
deterministic analysis helpers such as cycle detection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import networkx as nx

if TYPE_CHECKING:
    from pytrack.core.parser import ParseResult


def build_graph(parse_result: ParseResult) -> nx.DiGraph:
    """Build a directed dependency graph from parsed import records.

    Each node represents a module discovered during parsing.  An edge
    ``A → B`` means *module A imports something from module B*.

    Parameters
    ----------
    parse_result:
        The output of :func:`pytrack.core.parser.parse_directory`.

    Returns
    -------
    nx.DiGraph
        A NetworkX directed graph of module-level dependencies.
    """
    graph = nx.DiGraph()

    # Ensure every parsed module exists as a node even if it imports nothing
    known_modules = set(parse_result.imports.keys())
    graph.add_nodes_from(known_modules)

    for module_name, records in parse_result.imports.items():
        for record in records:
            if record.is_from_import:
                target = record.source_module
            else:
                target = record.imported_name

            # Only add edges to modules that exist in the parsed codebase
            # (skip stdlib / third-party imports)
            top_level = target.split(".")[0] if target else ""
            if top_level in known_modules or target in known_modules:
                # Resolve to the most specific known module
                resolved = _resolve_target(target, known_modules)
                if resolved and resolved != module_name:
                    graph.add_edge(module_name, resolved)

    return graph


def _resolve_target(target: str, known_modules: set[str]) -> str | None:
    """Resolve an import target to the best matching known module.

    Tries the full dotted path first, then progressively shorter
    prefixes until a match is found.
    """
    if target in known_modules:
        return target

    # Try progressively shorter prefixes
    parts = target.split(".")
    for i in range(len(parts) - 1, 0, -1):
        candidate = ".".join(parts[:i])
        if candidate in known_modules:
            return candidate

    return None


def detect_cycles(graph: nx.DiGraph) -> list[list[str]]:
    """Return all simple cycles in the directed graph.

    Parameters
    ----------
    graph:
        A NetworkX :class:`~networkx.DiGraph` built by :func:`build_graph`.

    Returns
    -------
    list[list[str]]
        Each inner list is a cycle represented as an ordered sequence of
        module names.  An empty list means the graph is acyclic.
    """
    return list(nx.simple_cycles(graph))


def get_module_dependencies(graph: nx.DiGraph, module_name: str) -> list[str]:
    """Return the direct dependencies (successors) of a module.

    Parameters
    ----------
    graph:
        The dependency graph.
    module_name:
        Dotted module name to query.

    Returns
    -------
    list[str]
        Sorted list of modules that *module_name* depends on.
    """
    if module_name not in graph:
        return []
    return sorted(graph.successors(module_name))


def get_dependency_chain(graph: nx.DiGraph, module_name: str) -> list[str]:
    """Return the full transitive dependency chain for a module.

    Uses BFS to collect every module reachable from *module_name*.

    Parameters
    ----------
    graph:
        The dependency graph.
    module_name:
        Dotted module name to query.

    Returns
    -------
    list[str]
        Sorted list of all transitively reachable modules.
    """
    if module_name not in graph:
        return []
    reachable = nx.descendants(graph, module_name)
    return sorted(reachable)
