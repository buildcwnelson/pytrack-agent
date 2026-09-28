# Pytrack

**Deterministic architectural analyzer with an AI explanation layer.**

Pytrack scans Python codebases using the `ast` module, builds a dependency graph with NetworkX, detects architectural faults like circular imports, and generates structured refactoring strategies using an Agno agent backed by a local Ollama model. Observability is provided via Arize Phoenix tracing.

## Features

- **AST-based import parsing** — safely parses all `.py` files in a target directory
- **Dependency graph** — constructs a directed graph of module-level dependencies
- **Cycle detection** — identifies circular imports using NetworkX
- **AI-powered analysis** — uses an Agno agent with local Ollama models to explain issues and suggest fixes
- **Structured output** — returns a `RefactoringRoadmap` with scores, findings, and action steps
- **Observability** — instruments the agent with Arize Phoenix for full tracing
- **Rich CLI** — beautiful terminal output with Typer and Rich

## Quick Start

```bash
# Install
uv sync

# Analyze a codebase
pytrack analyze --path /path/to/your/project --model llama3
```

## Development

```bash
# Run tests
uv run pytest tests/ -v

# Run the CLI
uv run pytrack analyze --path ./tests/fixtures/sample_project
```
