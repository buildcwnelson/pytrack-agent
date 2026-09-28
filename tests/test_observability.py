"""Tests for pytrack.observability — Phoenix tracing setup."""

from unittest.mock import MagicMock, patch

from pytrack.observability import setup_phoenix_tracing


def test_setup_phoenix_tracing_success():
    """setup_phoenix_tracing should return True when Phoenix is available."""
    with (
        patch("phoenix.otel.register") as mock_register,
        patch("openinference.instrumentation.agno.AgnoInstrumentor") as mock_instrumentor,
    ):
        mock_register.return_value = MagicMock()
        mock_instrumentor.return_value.instrument = MagicMock()

        result = setup_phoenix_tracing(project_name="test", endpoint="http://localhost:6006/v1/traces")

    assert result is True
    mock_register.assert_called_once()
    mock_instrumentor.return_value.instrument.assert_called_once()


def test_setup_phoenix_tracing_import_error():
    """setup_phoenix_tracing should return False when Phoenix is unavailable."""
    with patch.dict("sys.modules", {"phoenix": None, "phoenix.otel": None}):
        result = setup_phoenix_tracing()

    assert result is False


def test_setup_phoenix_tracing_connection_error():
    """setup_phoenix_tracing should return False on connection errors."""
    with patch("phoenix.otel.register", side_effect=ConnectionError("refused")):
        result = setup_phoenix_tracing()

    assert result is False
