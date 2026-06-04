"""JsApi response contract helpers."""

from collections.abc import Mapping
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from project_tracker.web.event_queue import drain_events


@dataclass(frozen=True)
class BridgeResponse:
    """Frontend-safe bridge response DTO."""

    ok: bool
    data: object | None
    error: dict[str, object] | None

    def to_dict(self) -> dict[str, object]:
        """Return JSON/frontend-safe dict shape."""
        return asdict(self)


def ok(data: object | None = None) -> dict[str, object]:
    """Return success bridge response."""
    return BridgeResponse(ok=True, data=data, error=None).to_dict()


def fail(
    error: str,
    code: str = "ERROR",
    details: object | None = None,
) -> dict[str, object]:
    """Return failure bridge response."""
    error_payload: dict[str, object] = {
        "code": code,
        "message": error,
        "details": details,
    }
    return BridgeResponse(ok=False, data=None, error=error_payload).to_dict()


def poll_events(limit: int | None = None) -> dict[str, object]:
    """Drain queued bridge events."""
    try:
        return ok(drain_events(limit))
    except Exception as exc:
        return fail(str(exc), code="EVENT_POLL_FAILED")


class DashboardServiceProtocol(Protocol):
    """Read-only dashboard service surface used by JsApi."""

    def list_projects(self, year: str | None = None) -> object:
        """Return dashboard project DTOs."""

    def get_summary(self, year: str | None = None) -> object:
        """Return dashboard summary DTO."""

    def get_dashboard(self, year: str | None = None) -> object:
        """Return dashboard data DTO."""


class JsApi:
    """pywebview-safe API facade without importing pywebview."""

    def __init__(self, dashboard_service: DashboardServiceProtocol) -> None:
        self._dashboard_service = dashboard_service

    def dashboard_list_projects(self, year: str | None = None) -> dict[str, object]:
        """Return dashboard project rows."""
        try:
            return ok(_to_frontend_safe(self._dashboard_service.list_projects(year)))
        except Exception as exc:
            return fail(str(exc), code="DASHBOARD_LIST_PROJECTS_FAILED")

    def dashboard_summary(self, year: str | None = None) -> dict[str, object]:
        """Return dashboard summary."""
        try:
            return ok(_to_frontend_safe(self._dashboard_service.get_summary(year)))
        except Exception as exc:
            return fail(str(exc), code="DASHBOARD_SUMMARY_FAILED")

    def dashboard_data(self, year: str | None = None) -> dict[str, object]:
        """Return dashboard rows plus summary."""
        try:
            return ok(_to_frontend_safe(self._dashboard_service.get_dashboard(year)))
        except Exception as exc:
            return fail(str(exc), code="DASHBOARD_DATA_FAILED")


def _to_frontend_safe(value: object) -> object:
    """Convert DTO data to JSON/frontend-safe primitives."""
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _to_frontend_safe(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        return {
            str(_to_frontend_safe(key)): _to_frontend_safe(item)
            for key, item in value.items()
        }
    if isinstance(value, tuple | list):
        return [_to_frontend_safe(item) for item in value]
    return value
