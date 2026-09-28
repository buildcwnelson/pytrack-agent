"""Tests for pytrack.core.parser — AST import extraction."""

from pathlib import Path

from pytrack.core.parser import parse_directory


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "sample_project"


def test_parse_directory_finds_all_modules():
    """All .py files in the fixture directory should be discovered."""
    result = parse_directory(FIXTURES)
    module_names = set(result.imports.keys())

    assert "pkg_a" in module_names
    assert "pkg_b" in module_names
    assert "pkg_a.utils" in module_names
    assert "pkg_b.helper" in module_names


def test_parse_directory_extracts_from_imports():
    """from-import statements should be captured as ImportRecords."""
    result = parse_directory(FIXTURES)
    pkg_a_imports = result.imports.get("pkg_a", [])

    from_imports = [r for r in pkg_a_imports if r.is_from_import]
    assert len(from_imports) >= 1
    assert any(r.source_module == "pkg_b" for r in from_imports)


def test_parse_directory_no_errors_on_valid_code():
    """The fixture directory contains only valid Python — expect no errors."""
    result = parse_directory(FIXTURES)
    assert len(result.errors) == 0


def test_parse_directory_invalid_path_raises():
    """Passing a non-existent directory should raise FileNotFoundError."""
    import pytest

    with pytest.raises(FileNotFoundError):
        parse_directory("/nonexistent/path")
