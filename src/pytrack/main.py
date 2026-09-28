"""Pytrack main execution pipeline.

Connects the deterministic graph engine to the Agno agent:
1. Parse the target codebase with the AST parser
2. Build the NetworkX dependency graph
3. Detect cycles
4. If cycles are found, invoke the Agno agent to analyse and suggest fixes
5. Report results
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx

from pytrack.agent.analyzer import analyze_cycles, create_analyzer_agent
from pytrack.core.graph import build_graph, detect_cycles
from pytrack.core.parser import ParseResult, parse_directory
from pytrack.models.schemas import RefactoringRoadmap
from pytrack.observability import setup_phoenix_tracing

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """Complete result of a Pytrack analysis run."""

    target_dir: str
    module_count: int = 0
    edge_count: int = 0
    parse_errors: dict[str, str] = field(default_factory=dict)
    cycles: list[list[str]] = field(default_factory=list)
    roadmap: RefactoringRoadmap | None = None
    tracing_enabled: bool = False


async def run_analysis(
    target_dir: str | Path,
    model_id: str = "llama3",
    enable_tracing: bool = True,
    phoenix_endpoint: str = "http://localhost:6006/v1/traces",
) -> AnalysisResult:
    """Execute the full Pytrack analysis pipeline.

    Parameters
    ----------
    target_dir:
        Path to the codebase to analyse.
    model_id:
        Ollama model identifier for the AI agent.
    enable_tracing:
        Whether to enable Arize Phoenix tracing.
    phoenix_endpoint:
        The OTLP endpoint for the Phoenix collector.

    Returns
    -------
    AnalysisResult
        Complete analysis result including cycles and optional roadmap.
    """
    target_path = Path(target_dir).resolve()
    result = AnalysisResult(target_dir=str(target_path))

    # Step 0: Configure observability
    if enable_tracing:
        result.tracing_enabled = setup_phoenix_tracing(
            project_name="pytrack",
            endpoint=phoenix_endpoint,
        )

    # Step 1: Parse the target codebase
    logger.info("Parsing codebase at %s", target_path)
    parse_result: ParseResult = parse_directory(target_path)
    result.module_count = len(parse_result.imports)
    result.parse_errors = parse_result.errors

    if result.parse_errors:
        logger.warning(
            "Failed to parse %d file(s): %s",
            len(result.parse_errors),
            list(result.parse_errors.keys()),
        )

    # Step 2: Build the dependency graph
    logger.info("Building dependency graph (%d modules)", result.module_count)
    graph: nx.DiGraph = build_graph(parse_result)
    result.edge_count = graph.number_of_edges()

    # Step 3: Detect cycles
    logger.info("Running cycle detection")
    cycles = detect_cycles(graph)
    result.cycles = cycles

    if not cycles:
        logger.info("No circular dependencies detected")
        return result

    logger.warning("Detected %d circular dependency cycle(s)", len(cycles))

    # Step 4: Invoke the Agno agent
    logger.info("Initialising Agno agent with model '%s'", model_id)
    agent = create_analyzer_agent(
        graph=graph,
        root_dir=target_path,
        model_id=model_id,
    )

    logger.info("Running AI analysis on detected cycles")
    try:
        roadmap = await analyze_cycles(agent, cycles)
        result.roadmap = roadmap
    except Exception as exc:
        logger.error("Agent analysis failed: %s", exc)

    return result


def run_analysis_sync(
    target_dir: str | Path,
    model_id: str = "llama3",
    enable_tracing: bool = True,
    phoenix_endpoint: str = "http://localhost:6006/v1/traces",
) -> AnalysisResult:
    """Synchronous wrapper for :func:`run_analysis`.

    Convenience function for use in CLI entry points and scripts.
    """
    return asyncio.run(
        run_analysis(
            target_dir=target_dir,
            model_id=model_id,
            enable_tracing=enable_tracing,
            phoenix_endpoint=phoenix_endpoint,
        )
    )
