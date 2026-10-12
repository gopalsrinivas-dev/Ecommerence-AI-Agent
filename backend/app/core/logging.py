import json
import logging
import re
import traceback
from contextvars import ContextVar
from datetime import UTC, datetime
from uuid import UUID

request_id: ContextVar[str] = ContextVar("request_id", default="system")
request_context: ContextVar[dict] = ContextVar("request_context", default={})
logger = logging.getLogger("support")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())


class ConsoleFormatter(logging.Formatter):
    def format(self, record):
        return " ".join(f"{k}={json.dumps(v)}" for k, v in json.loads(record.getMessage()).items())


def configure_logging(config):
    mode = config.log_format
    if mode == "auto":
        mode = "json" if config.app_env == "production" else "console"
    for handler in logger.handlers:
        handler.setFormatter(ConsoleFormatter() if mode == "console" else logging.Formatter("%(message)s"))


def metadata(fields):
    result = {}
    for key, value in fields.items():
        if key in {"status_code", "duration_ms", "count"} and type(value) in {int, float}:
            result[key] = value
        elif key == "replay" and type(value) is bool:
            result[key] = value
        elif key in {"actor_id", "conversation_id", "action_id"}:
            try:
                result[key] = str(UUID(str(value)))
            except (ValueError, TypeError, AttributeError):
                pass
        elif key == "order_id" and isinstance(value, str) and re.fullmatch(r"ORD\d{1,16}", value):
            result[key] = value
        elif key in {"tool_name", "outcome", "error_code"} and isinstance(value, str):
            if re.fullmatch(r"[A-Za-z0-9_]{1,64}", value):
                result[key] = value
    return result


def bind_context(**fields):
    # Each request owns its dictionary, shared with its worker-thread context copies.
    try:
        if request_id.get() != "system":
            request_context.get().update(metadata(fields))
    except Exception:
        pass


def emit(name, level, fields, extra=None):
    try:
        data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": level,
            "event": name,
            "request_id": request_id.get(),
            **request_context.get(),
            **metadata(fields),
            **(extra or {}),
        }
        logger.log(logging.ERROR if level == "ERROR" else logging.INFO, json.dumps(data))
    except Exception:
        pass  # Logging must never change request or transaction outcomes.


def event(name: str, **fields):
    emit(name, "INFO", fields)


def after_commit(db, name, **fields):
    try:
        db.info.setdefault("log_events", []).append((name, metadata(fields)))
    except Exception:
        pass


def failure(name: str, exc: Exception, code: str):
    # Exception messages, source lines and locals may contain SQL parameters,
    # credentials or customer/provider text. Retain frames, never those values.
    try:
        frames = [
            {"file": frame.f_code.co_filename, "line": line, "function": frame.f_code.co_name}
            for frame, line in traceback.walk_tb(exc.__traceback__)
        ]
        emit(
            name,
            "ERROR",
            {"error_code": code},
            {
                "exception_type": type(exc).__name__,
                "stack_trace": frames,
            },
        )
    except Exception:
        pass
