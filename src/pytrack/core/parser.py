"""AST-based import parser for Python source files.

Walks a target directory, safely parses every .py file, and extracts
``import`` / ``from ... import`` statements into a deterministic
dependency map.
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ImportRecord:
    """A single import extracted from a source file."""

    source_module: str
    imported_name: str
    is_from_import: bool = False
    level: int = 0  # 0 = absolute, >0 = relative


@dataclass
class ParseResult:
    """Aggregated result of parsing a target directory."""

    imports: dict[str, list[ImportRecord]] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)


class _ImportVisitor(ast.NodeVisitor):
    """AST visitor that collects import statements."""

    def __init__(self) -> None:
        self.records: list[ImportRecord] = []

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        for alias in node.names:
            self.records.append(
                ImportRecord(
                    source_module="",
                    imported_name=alias.name,
                    is_from_import=False,
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        module = node.module or ""
        for alias in node.names:
            self.records.append(
                ImportRecord(
                    source_module=module,
                    imported_name=alias.name,
                    is_from_import=True,
                    level=node.level,
                )
            )
        self.generic_visit(node)


def _filepath_to_module(filepath: Path, root: Path) -> str:
    """Convert a filesystem path to a dotted module name.

    Example: ``root/pkg/sub/mod.py`` → ``pkg.sub.mod``
    """
    relative = filepath.relative_to(root)
    parts = list(relative.parts)

    # Strip .py extension from the last part
    if parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]

    # Collapse __init__ into the parent package name
    if parts[-1] == "__init__":
        parts = parts[:-1]

    return ".".join(parts)


def parse_directory(target_dir: str | Path) -> ParseResult:
    """Walk *target_dir*, parse every ``.py`` file, and collect imports.

    Parameters
    ----------
    target_dir:
        Absolute or relative path to the root of the codebase to analyse.

    Returns
    -------
    ParseResult
        A mapping of ``module_name → list[ImportRecord]`` plus any files
        that failed to parse.
    """
    root = Path(target_dir).resolve()
    result = ParseResult()

    if not root.is_dir():
        raise FileNotFoundError(f"Target directory does not exist: {root}")

    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in sorted(filenames):
            if not filename.endswith(".py"):
                continue

            filepath = Path(dirpath) / filename
            module_name = _filepath_to_module(filepath, root)

            try:
                source = filepath.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source, filename=str(filepath))
            except SyntaxError as exc:
                result.errors[module_name] = str(exc)
                continue

            visitor = _ImportVisitor()
            visitor.visit(tree)

            # Tag every record with the owning module
            for record in visitor.records:
                record.source_module = (
                    record.source_module if record.is_from_import else record.imported_name
                )

            result.imports[module_name] = visitor.records

    return result
