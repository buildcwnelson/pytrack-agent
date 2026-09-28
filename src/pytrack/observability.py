"""Arize Phoenix observability configuration for Pytrack.

Sets up OpenTelemetry tracing with Phoenix as the collector, and
instruments the Agno agent to capture tool calls, payloads, and
inference reasoning.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def setup_phoenix_tracing(
    project_name: str = "pytrack",
    endpoint: str = "http://localhost:6006/v1/traces",
) -> bool:
    """Configure Arize Phoenix tracing for the Agno agent.

    This instruments the Agno framework with OpenTelemetry spans that
    are exported to a local Phoenix collector.

    Parameters
    ----------
    project_name:
        Name of the Phoenix project to log traces under.
    endpoint:
        The OTLP HTTP endpoint of the Phoenix collector.

    Returns
    -------
    bool
        ``True`` if tracing was successfully configured, ``False`` if
        Phoenix or the instrumentor is unavailable.
    """
    try:
        from phoenix.otel import register

        tracer_provider = register(
            project_name=project_name,
            endpoint=endpoint,
            batch=True,
        )

        from openinference.instrumentation.agno import AgnoInstrumentor

        AgnoInstrumentor().instrument(tracer_provider=tracer_provider)

        logger.info(
            "Phoenix tracing enabled — project=%s endpoint=%s",
            project_name,
            endpoint,
        )
        return True

    except ImportError as exc:
        logger.warning("Phoenix tracing unavailable: %s", exc)
        return False
    except Exception as exc:
        logger.warning("Failed to initialise Phoenix tracing: %s", exc)
        return False
