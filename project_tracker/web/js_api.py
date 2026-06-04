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


class NotificationServiceProtocol(Protocol):
    """Read-only notification service surface used by JsApi."""

    def get_all(self) -> object:
        """Return all notifications."""

    def get_undismissed(self) -> object:
        """Return undismissed notifications."""

    def get_latest(self, limit: int = 3, undismissed_only: bool = False) -> object:
        """Return latest notifications."""

    def count(self, undismissed_only: bool = False) -> int:
        """Return notification count."""

    def dismiss(self, notification_id: str) -> None:
        """Dismiss notification."""


class JsApi:
    """pywebview-safe API facade without importing pywebview."""

    def __init__(
        self,
        dashboard_service: DashboardServiceProtocol | None,
        notification_service: NotificationServiceProtocol | None = None,
    ) -> None:
        self._dashboard_service = dashboard_service
        self._notification_service = notification_service

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

    def notification_list(self, undismissed_only: bool = False) -> dict[str, object]:
        """Return notifications."""
        try:
            source = (
                self._notification_service.get_undismissed()
                if undismissed_only
                else self._notification_service.get_all()
            )
            return ok(_to_frontend_safe(source))
        except Exception as exc:
            return fail(str(exc), code="NOTIFICATION_LIST_FAILED")

    def notification_latest(
        self,
        limit: int = 3,
        undismissed_only: bool = False,
    ) -> dict[str, object]:
        """Return latest notifications."""
        try:
            return ok(
                _to_frontend_safe(
                    self._notification_service.get_latest(limit, undismissed_only)
                )
            )
        except Exception as exc:
            return fail(str(exc), code="NOTIFICATION_LATEST_FAILED")

    def notification_count(self, undismissed_only: bool = False) -> dict[str, object]:
        """Return notification count."""
        try:
            return ok(self._notification_service.count(undismissed_only))
        except Exception as exc:
            return fail(str(exc), code="NOTIFICATION_COUNT_FAILED")

    def notification_dismiss(self, notification_id: str) -> dict[str, object]:
        """Dismiss notification by id."""
        try:
            self._notification_service.dismiss(notification_id)
            return ok()
        except Exception as exc:
            return fail(str(exc), code="NOTIFICATION_DISMISS_FAILED")


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
