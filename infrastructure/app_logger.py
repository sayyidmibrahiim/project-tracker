"""Application file logging for backend and frontend activity.

Logs are written under the user AppData config folder:
``%APPDATA%/ProjectTrackerDBS/logs`` on Windows.

Each line is JSON so the files stay grep-friendly and machine-parseable.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from logging import Logger
from pathlib import Path
from typing import Mapping

from infrastructure.settings_store import app_config_dir

APP_LOG_PREFIX = "personal_workspace"
_REDACT_KEYS = {
    "content",
    "html",
    "notes",
    "note",
    "data_uri",
    "base64",
    "password",
    "token",
    "secret",
    "authorization",
}
_MAX_STRING = 300
_backend_logger: Logger | None = None
_frontend_logger: Logger | None = None


def get_logs_dir() -> Path:
    logs = app_config_dir() / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return logs


def _date_suffix() -> str:
    return datetime.now().strftime("%Y%m%d")


def _log_path(channel: str) -> Path:
    return get_logs_dir() / f"{APP_LOG_PREFIX}_{channel}_{_date_suffix()}.log"


def _json_default(value: object) -> str:
    if isinstance(value, Path):
        return str(value)
    return repr(value)


def _redact(value: object, key: str = "") -> object:
    key_l = key.casefold()
    if key_l in _REDACT_KEYS or any(part in key_l for part in _REDACT_KEYS):
        if isinstance(value, str):
            return f"<redacted len={len(value)}>"
        return "<redacted>"
    if isinstance(value, Mapping):
        return {str(k): _redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_redact(item, key) for item in value[:50]]
    if isinstance(value, str):
        if len(value) > _MAX_STRING:
            return f"{value[:_MAX_STRING]}...<truncated len={len(value)}>"
        return value
    return value


def safe_json_line(payload: Mapping[str, object]) -> str:
    redacted = _redact(payload)
    return json.dumps(redacted, ensure_ascii=False, default=_json_default, separators=(",", ":"))


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = getattr(record, "payload", None)
        data: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created).astimezone().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        if isinstance(payload, Mapping):
            data["payload"] = dict(payload)
        elif payload is not None:
            data["payload"] = payload
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)
        return safe_json_line(data)


def _make_logger(name: str, path: Path) -> Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    current = str(path)
    for handler in logger.handlers:
        if isinstance(handler, logging.FileHandler) and handler.baseFilename == current:
            return logger
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(JsonLineFormatter())
    logger.addHandler(handler)
    return logger


def setup_backend_logging() -> Logger:
    global _backend_logger, _frontend_logger
    _backend_logger = _make_logger("personal_workspace.backend", _log_path("backend"))
    _frontend_logger = _make_logger("personal_workspace.frontend", _log_path("frontend"))
    _backend_logger.info("backend.logging.ready", extra={"payload": {"logs_dir": str(get_logs_dir())}})
    return _backend_logger


def get_backend_logger() -> Logger:
    global _backend_logger
    if _backend_logger is None:
        _backend_logger = setup_backend_logging()
    return _backend_logger


def get_frontend_logger() -> Logger:
    global _frontend_logger
    if _frontend_logger is None:
        setup_backend_logging()
    assert _frontend_logger is not None
    return _frontend_logger


def log_backend_event(event: str, payload: Mapping[str, object] | None = None) -> None:
    get_backend_logger().info(event, extra={"payload": dict(payload or {})})


def log_frontend_event(event: Mapping[str, object]) -> None:
    get_frontend_logger().info("frontend.event", extra={"payload": dict(event)})
