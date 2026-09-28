"""Tests for pytrack.models.schemas — Pydantic model validation."""

import pytest
from pydantic import ValidationError

from pytrack.models.schemas import RefactoringRoadmap


def test_valid_roadmap():
    """A fully valid RefactoringRoadmap should instantiate without error."""
    roadmap = RefactoringRoadmap(
        architecture_score=75,
        findings=["Circular dependency between pkg_a and pkg_b"],
        actionable_steps=["Extract shared interface into a new module"],
    )
    assert roadmap.architecture_score == 75
    assert len(roadmap.findings) == 1
    assert len(roadmap.actionable_steps) == 1


def test_score_out_of_range_low():
    """architecture_score below 1 should fail validation."""
    with pytest.raises(ValidationError):
        RefactoringRoadmap(
            architecture_score=0,
            findings=["issue"],
            actionable_steps=["fix"],
        )


def test_score_out_of_range_high():
    """architecture_score above 100 should fail validation."""
    with pytest.raises(ValidationError):
        RefactoringRoadmap(
            architecture_score=101,
            findings=["issue"],
            actionable_steps=["fix"],
        )


def test_empty_findings_rejected():
    """An empty findings list should fail validation (min_length=1)."""
    with pytest.raises(ValidationError):
        RefactoringRoadmap(
            architecture_score=50,
            findings=[],
            actionable_steps=["fix"],
        )


def test_empty_steps_rejected():
    """An empty actionable_steps list should fail validation (min_length=1)."""
    with pytest.raises(ValidationError):
        RefactoringRoadmap(
            architecture_score=50,
            findings=["issue"],
            actionable_steps=[],
        )


def test_roadmap_serialization():
    """The model should round-trip through JSON without data loss."""
    roadmap = RefactoringRoadmap(
        architecture_score=42,
        findings=["Finding A", "Finding B"],
        actionable_steps=["Step 1", "Step 2", "Step 3"],
    )
    data = roadmap.model_dump()
    restored = RefactoringRoadmap(**data)
    assert restored == roadmap
