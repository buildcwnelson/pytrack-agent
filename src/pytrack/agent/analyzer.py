"""Agno agent for architectural analysis using local Ollama models.

Initialises an Agno :class:`~agno.agent.Agent` configured to reason
about circular dependencies and produce a structured
:class:`~pytrack.models.schemas.RefactoringRoadmap`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from agno.agent import Agent
from agno.models.ollama import Ollama

from pytrack.agent.tools import ArchitectureToolkit
from pytrack.models.schemas import RefactoringRoadmap

if TYPE_CHECKING:
    import networkx as nx


SYSTEM_INSTRUCTIONS = """\
You are an expert software architect. Given a structural fault like a \
circular dependency, use your tools to analyze the source code and \
provide a step-by-step refactoring strategy to break the coupling.

When analysing a cycle:
1. Use `get_dependency_chain` to understand the full dependency tree of each module in the cycle.
2. Use `get_module_source` to read the source code of the modules involved.
3. Identify exactly which imports create the cycle and why they exist.
4. Propose concrete, actionable refactoring steps (e.g. extract an interface, \
   use dependency injection, move shared code to a new module).
5. Score the architecture from 1 (critical) to 100 (excellent).

Always provide at least one finding and one actionable step.
"""


def create_analyzer_agent(
    graph: nx.DiGraph,
    root_dir: str | Path,
    model_id: str = "llama3",
) -> Agent:
    """Create and return an Agno Agent configured for architecture analysis.

    Parameters
    ----------
    graph:
        The pre-built NetworkX dependency graph.
    root_dir:
        Root directory of the target codebase.
    model_id:
        Ollama model identifier (e.g. ``llama3``, ``qwen2.5-coder``).

    Returns
    -------
    Agent
        A fully configured Agno agent ready to analyse architectural issues.
    """
    toolkit = ArchitectureToolkit(graph=graph, root_dir=root_dir)

    agent = Agent(
        name="PytrackArchitectureAnalyzer",
        model=Ollama(id=model_id),
        tools=[toolkit],
        output_schema=RefactoringRoadmap,
        instructions=[SYSTEM_INSTRUCTIONS],
        markdown=True,
    )

    return agent


async def analyze_cycles(
    agent: Agent,
    cycles: list[list[str]],
) -> RefactoringRoadmap | None:
    """Run the agent to analyse detected circular dependencies.

    Parameters
    ----------
    agent:
        The configured Agno architecture agent.
    cycles:
        List of cycles, each being a list of module names forming a loop.

    Returns
    -------
    RefactoringRoadmap | None
        The structured analysis result, or ``None`` if the agent fails to
        produce valid output.
    """
    if not cycles:
        return None

    # Format the cycles into a clear prompt
    cycle_descriptions = []
    for i, cycle in enumerate(cycles, 1):
        path = " → ".join(cycle + [cycle[0]])
        cycle_descriptions.append(f"  Cycle {i}: {path}")

    prompt = (
        f"I have detected {len(cycles)} circular dependency cycle(s) in the codebase:\n\n"
        + "\n".join(cycle_descriptions)
        + "\n\nAnalyse these cycles using your tools and provide a "
        "complete refactoring roadmap. Read the source code of the "
        "involved modules to understand the coupling."
    )

    response = await agent.arun(prompt)

    # Extract the structured content
    if response and response.content:
        if isinstance(response.content, RefactoringRoadmap):
            return response.content
        # Try to parse if it's a dict
        if isinstance(response.content, dict):
            return RefactoringRoadmap(**response.content)

    return None
