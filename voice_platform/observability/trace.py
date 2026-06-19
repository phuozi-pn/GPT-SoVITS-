from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from uuid import uuid4

_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)


def get_current_trace_id() -> str | None:
    return _trace_id.get()


def set_trace_id(trace_id: str) -> None:
    _trace_id.set(trace_id)


def ensure_trace_id(candidate: str | None = None) -> str:
    current = candidate or get_current_trace_id()
    if current:
        set_trace_id(current)
        return current
    new_id = str(uuid4())
    set_trace_id(new_id)
    return new_id


@contextmanager
def trace_context(trace_id: str):
    token = _trace_id.set(trace_id)
    try:
        yield trace_id
    finally:
        _trace_id.reset(token)
