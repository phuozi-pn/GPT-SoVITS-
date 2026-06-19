"""API-layer trace facade — wraps voice_platform.observability.trace.

This thin facade isolates the API layer from direct observability imports,
making it easier to swap tracing backends or mock in tests.
"""

from __future__ import annotations

from voice_platform.observability.trace import ensure_trace_id, get_current_trace_id, trace_context

__all__ = ["ensure_trace_id", "get_current_trace_id", "trace_context"]
