from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

from voice_platform.observability.trace import get_current_trace_id


class TraceFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        trace_id = get_current_trace_id()
        if trace_id:
            record.trace_id = trace_id  # type: ignore[attr-defined]
        else:
            record.trace_id = "-"  # type: ignore[attr-defined]
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": getattr(record, "trace_id", "-"),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(*, json_logs: bool = False, level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(TraceFilter())
    if json_logs:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s [%(trace_id)s] %(name)s: %(message)s"
            )
        )
    root.addHandler(handler)
    root.setLevel(level)
