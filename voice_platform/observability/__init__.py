"""W4 observability: trace context, job failure alerts, structured logging."""

from voice_platform.observability.alerts import maybe_alert_job_failed
from voice_platform.observability.trace import (
    ensure_trace_id,
    get_current_trace_id,
    set_trace_id,
    trace_context,
)

__all__ = [
    "ensure_trace_id",
    "get_current_trace_id",
    "maybe_alert_job_failed",
    "set_trace_id",
    "trace_context",
]
