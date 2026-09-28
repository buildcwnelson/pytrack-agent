"""Agno-compatible tools for the architecture analysis agent.

Provides tools that let the agent inspect source code and query the
dependency graph at inference time.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from agno.tools import Toolkit

if TYPE_CHECKING:
    import networkx as nx


class ArchitectureToolkit(Toolkit):
    """Toolkit that gives the Agno agent access to source code and the dependency graph.

    Parameters
    ----------
    graph:
        A pre-built NetworkX :class:`~networkx.DiGraph` of module dependencies.
    root_dir:
        The root directory of the target codebase (used to resolve file paths).
    """

    def __init__(self, graph: nx.DiGraph, root_dir: str | Path) -> None:
        super().__init__(name="architecture_toolkit", auto_register=False)
        self._graph = graph
        self._root_dir = Path(root_dir).resolve()

        # Explicitly register the tools
        self.register(self.get_module_source)
        self.register(self.get_dependency_chain)

    def get_module_source(self, filepath: str) -> str:
        """Read and return the raw source code of a Python module.

        Parameters
        ----------
        filepath:
            Path to the module file, either absolute or relative to the
            project root.

        Returns
        -------
        str
            The full source code of the file, or an error message if the
            file cannot be read.
        """
        path = Path(filepath)

        # Resolve relative paths against the project root
        if not path.is_absolute():
            path = self._root_dir / path

        path = path.resolve()

        # Security: ensure the file is within the target project
        if not str(path).startswith(str(self._root_dir)):
            return f"Error: Path '{filepath}' is outside the project root."

        if not path.exists():
            return f"Error: File '{filepath}' does not exist."

        if not path.suffix == ".py":
            return f"Error: File '{filepath}' is not a Python file."

        try:
            return path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return f"Error reading '{filepath}': {exc}"

    def get_dependency_chain(self, module_name: str) -> list[str]:
        """Query the dependency graph for a module's full dependency chain.

        Parameters
        ----------
        module_name:
            Dotted module name (e.g. ``pkg_a.utils``).

        Returns
        -------
        list[str]
            Sorted list of all modules that *module_name* transitively
            depends on.  Returns an empty list if the module is unknown.
        """
        from pytrack.core.graph import get_dependency_chain

        return get_dependency_chain(self._graph, module_name)
