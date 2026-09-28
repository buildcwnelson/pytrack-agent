"""Pydantic models for structured agent output.

Defines the schema that the Agno agent must conform to when returning
its refactoring analysis.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RefactoringRoadmap(BaseModel):
    """Structured refactoring strategy produced by the AI agent.

    The agent populates this after analysing circular dependencies and
    reading the involved source code.
    """

    architecture_score: int = Field(
        ...,
        ge=1,
        le=100,
        description=(
            "Overall architecture health score from 1 (critical) to 100 (excellent). "
            "A lower score indicates more severe structural issues."
        ),
    )

    findings: list[str] = Field(
        ...,
        min_length=1,
        description=(
            "List of specific architectural issues discovered during analysis. "
            "Each finding should clearly describe what the problem is and where it occurs."
        ),
    )

    actionable_steps: list[str] = Field(
        ...,
        min_length=1,
        description=(
            "Ordered list of concrete refactoring steps to resolve the identified issues. "
            "Each step should be specific enough for a developer to implement directly."
        ),
    )
