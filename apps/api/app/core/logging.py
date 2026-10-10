"""Structured JSON logging with correlation ids and secret redaction."""

import json
import logging
import re
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)

_REDACT_KEYS = re.compile(
    r"(authorization|access_token|client_secret|password|cookie|csrf|secret|token)", re.I
)


def redact(value: Any) -> Any:
    """Recursively replace values whose keys look sensitive."""
    if isinstance(value, dict):
        return {
            k: "[REDACTED]" if _REDACT_KEYS.search(str(k)) else redact(v) for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "correlation_id": correlation_id_var.get(),
        }
        extra = getattr(record, "data", None)
        if isinstance(extra, dict):
            payload["data"] = redact(extra)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # httpx logs full URLs at INFO; keep it quiet so query strings never leak.
    logging.getLogger("httpx").setLevel(logging.WARNING)
