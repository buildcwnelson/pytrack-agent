"""Pytrack CLI — Typer-based command-line interface with Rich formatting.

Provides the ``pytrack analyze`` command that runs the full analysis
pipeline and renders results with Rich tables, panels, and colour.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from pytrack.main import AnalysisResult, run_analysis

app = typer.Typer(
    name="pytrack",
    help="Deterministic architectural analyzer with AI-powered refactoring suggestions.",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()


def _render_header(result: AnalysisResult) -> None:
    """Render the analysis header with summary stats."""
    header = Text()
    header.append("Pytrack Analysis Report\n", style="bold magenta")
    header.append(f"Target: ", style="dim")
    header.append(f"{result.target_dir}\n", style="cyan")
    header.append(f"Modules: ", style="dim")
    header.append(f"{result.module_count}", style="green")
    header.append(f"  │  Edges: ", style="dim")
    header.append(f"{result.edge_count}", style="green")
    header.append(f"  │  Cycles: ", style="dim")
    cycle_style = "red bold" if result.cycles else "green"
    header.append(f"{len(result.cycles)}", style=cycle_style)

    if result.tracing_enabled:
        header.append("\n🔭 ", style="dim")
        header.append("Phoenix tracing active", style="blue italic")

    console.print(Panel(header, border_style="bright_blue", padding=(1, 2)))


def _render_parse_errors(result: AnalysisResult) -> None:
    """Render any parse errors as a warning panel."""
    if not result.parse_errors:
        return

    table = Table(title="Parse Errors", border_style="yellow")
    table.add_column("Module", style="yellow")
    table.add_column("Error", style="dim")

    for module, error in result.parse_errors.items():
        table.add_row(module, error)

    console.print(table)
    console.print()


def _render_cycles(result: AnalysisResult) -> None:
    """Render detected cycles as a red warning block."""
    if not result.cycles:
        console.print(
            Panel(
                "✅ [green bold]No circular dependencies detected.[/green bold]\n"
                "[dim]The dependency graph is acyclic — great architecture![/dim]",
                border_style="green",
                title="Cycle Detection",
                padding=(1, 2),
            )
        )
        return

    lines: list[str] = []
    for i, cycle in enumerate(result.cycles, 1):
        path = " → ".join(cycle + [cycle[0]])
        lines.append(f"[red bold]Cycle {i}:[/red bold] [white]{path}[/white]")

    content = "\n".join(lines)
    console.print(
        Panel(
            f"⚠️  [red bold]Detected {len(result.cycles)} circular dependency cycle(s)[/red bold]\n\n"
            + content,
            border_style="red",
            title="[red bold]⛔ Circular Dependencies[/red bold]",
            padding=(1, 2),
        )
    )
    console.print()


def _render_roadmap(result: AnalysisResult) -> None:
    """Render the RefactoringRoadmap as a formatted table."""
    if result.roadmap is None:
        if result.cycles:
            console.print(
                Panel(
                    "[yellow]AI analysis was not available.[/yellow]\n"
                    "[dim]Ensure Ollama is running with the specified model.[/dim]",
                    border_style="yellow",
                    title="AI Analysis",
                    padding=(1, 2),
                )
            )
        return

    roadmap = result.roadmap

    # Architecture score with colour coding
    score = roadmap.architecture_score
    if score >= 75:
        score_style = "green bold"
        score_emoji = "🟢"
    elif score >= 50:
        score_style = "yellow bold"
        score_emoji = "🟡"
    elif score >= 25:
        score_style = "red bold"
        score_emoji = "🟠"
    else:
        score_style = "red bold blink"
        score_emoji = "🔴"

    console.print(
        Panel(
            f"{score_emoji} Architecture Score: [{score_style}]{score}/100[/{score_style}]",
            border_style="bright_blue",
            title="[bold bright_blue]AI Architecture Assessment[/bold bright_blue]",
            padding=(1, 2),
        )
    )
    console.print()

    # Findings table
    findings_table = Table(
        title="🔍 Findings",
        border_style="bright_red",
        show_lines=True,
        pad_edge=True,
    )
    findings_table.add_column("#", style="dim", width=4, justify="right")
    findings_table.add_column("Issue", style="white")

    for i, finding in enumerate(roadmap.findings, 1):
        findings_table.add_row(str(i), finding)

    console.print(findings_table)
    console.print()

    # Actionable steps table
    steps_table = Table(
        title="🛠️  Refactoring Roadmap",
        border_style="bright_green",
        show_lines=True,
        pad_edge=True,
    )
    steps_table.add_column("Step", style="bold cyan", width=6, justify="right")
    steps_table.add_column("Action", style="white")

    for i, step in enumerate(roadmap.actionable_steps, 1):
        steps_table.add_row(str(i), step)

    console.print(steps_table)
    console.print()


@app.command()
def analyze(
    path: str = typer.Option(
        ".",
        "--path",
        "-p",
        help="Path to the target codebase to analyse.",
    ),
    model: str = typer.Option(
        "llama3",
        "--model",
        "-m",
        help="Ollama model name for AI analysis (e.g. llama3, qwen2.5-coder).",
    ),
    no_ai: bool = typer.Option(
        False,
        "--no-ai",
        help="Skip AI analysis — only run deterministic cycle detection.",
    ),
    no_tracing: bool = typer.Option(
        False,
        "--no-tracing",
        help="Disable Arize Phoenix tracing.",
    ),
    phoenix_endpoint: str = typer.Option(
        "http://localhost:6006/v1/traces",
        "--phoenix-endpoint",
        help="OTLP endpoint for the Phoenix collector.",
    ),
) -> None:
    """Analyse a Python codebase for architectural issues.

    Scans all .py files, builds a dependency graph, detects circular
    imports, and optionally uses an AI agent to generate a refactoring
    roadmap.
    """
    target = Path(path).resolve()

    if not target.is_dir():
        console.print(f"[red bold]Error:[/red bold] Directory not found: {target}")
        raise typer.Exit(code=1)

    console.print()
    with console.status("[bold blue]Analysing codebase...[/bold blue]", spinner="dots"):
        if no_ai:
            # Run only the deterministic parts
            from pytrack.core.graph import build_graph, detect_cycles
            from pytrack.core.parser import parse_directory

            parse_result = parse_directory(target)
            graph = build_graph(parse_result)
            cycles = detect_cycles(graph)

            result = AnalysisResult(
                target_dir=str(target),
                module_count=len(parse_result.imports),
                edge_count=graph.number_of_edges(),
                parse_errors=parse_result.errors,
                cycles=cycles,
                roadmap=None,
                tracing_enabled=False,
            )
        else:
            result = asyncio.run(
                run_analysis(
                    target_dir=target,
                    model_id=model,
                    enable_tracing=not no_tracing,
                    phoenix_endpoint=phoenix_endpoint,
                )
            )

    console.print()
    _render_header(result)
    console.print()
    _render_parse_errors(result)
    _render_cycles(result)
    _render_roadmap(result)


def main() -> None:
    """Entry point for the pytrack CLI."""
    app()
