"""Structured observability: logging setup and JSONL event tracking."""

from __future__ import annotations

import contextvars
import json
import logging
import logging.handlers
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

from runtime_paths import LOG_DIR, ensure_runtime_dirs


_LOG_LOCK = threading.Lock()
_LOGGING_INITIALIZED = False
_EVENT_LOGGER = logging.getLogger("observability")

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")
task_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("task_id", default="")
trigger_source_var: contextvars.ContextVar[str] = contextvars.ContextVar("trigger_source", default="")


def configure_logging(service_name: str, level: int = logging.INFO):
    """Configure console + rotating file logging once per process."""
    global _LOGGING_INITIALIZED
    if _LOGGING_INITIALIZED:
        return

    ensure_runtime_dirs()
    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)

    file_path = LOG_DIR / f"{service_name}.log"
    rotating = logging.handlers.RotatingFileHandler(
        file_path,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    rotating.setFormatter(formatter)
    root.addHandler(rotating)

    _LOGGING_INITIALIZED = True
    _EVENT_LOGGER.info("logging configured: service=%s file=%s", service_name, file_path)


def _event_file(day: str | None = None) -> Path:
    ensure_runtime_dirs()
    stamp = day or datetime.now().strftime("%Y%m%d")
    return LOG_DIR / f"events-{stamp}.jsonl"


def set_request_context(request_id: str):
    return request_id_var.set(request_id)


def set_task_context(task_id: str):
    return task_id_var.set(task_id)


def set_trigger_source(source: str):
    return trigger_source_var.set(source)


def reset_context(token):
    if token is not None:
        token.var.reset(token)


def emit_event(name: str, level: str = "info", **fields: Any):
    """Write one structured event line and mirror a compact log message."""
    now = time.time()
    payload = {
        "ts": now,
        "iso_ts": datetime.fromtimestamp(now).isoformat(timespec="milliseconds"),
        "event": name,
        "level": level,
        "request_id": fields.pop("request_id", "") or request_id_var.get(),
        "task_id": fields.pop("task_id", "") or task_id_var.get(),
        "trigger_source": fields.pop("trigger_source", "") or trigger_source_var.get(),
        **fields,
    }

    with _LOG_LOCK:
        path = _event_file()
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    msg = f"{name} req={payload['request_id']} task={payload['task_id']} src={payload['trigger_source']}"
    log_fn = getattr(_EVENT_LOGGER, level, _EVENT_LOGGER.info)
    log_fn(msg)


def read_recent_events(limit: int = 200) -> list[dict[str, Any]]:
    """Read most recent structured events from JSONL files."""
    ensure_runtime_dirs()
    limit = max(1, min(limit, 2000))
    buf: deque[dict[str, Any]] = deque(maxlen=limit)

    files = sorted(LOG_DIR.glob("events-*.jsonl"))
    for path in files:
        try:
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        buf.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            continue
    return list(buf)[-limit:]
