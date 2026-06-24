from __future__ import annotations

from pathlib import Path
from collections.abc import Callable
from typing import TYPE_CHECKING
import uuid

from core.models import Notification, local_now
from core.signal import Signal
from web.event_queue import push_event

if TYPE_CHECKING:
    from infrastructure.cache_db import CacheDb


class NotificationService:
    def __init__(
        self,
        event_publisher: Callable[[str, dict[str, object] | None], None] | None = push_event,
        cache: "CacheDb | None" = None,
    ) -> None:
        self.notification_added = Signal()  # emits Notification
        self.notification_dismissed = Signal()  # emits notification_id
        self.write_failed = Signal()  # emits (str description, Exception)
        self._event_publisher = event_publisher
        self._cache = cache
        self._notifications: list[Notification] = []

    def load_persisted(self) -> None:
        """Load all persisted notifications, preserving stored dismissed state.

        Called once on startup. Notifications survive restarts with their prior
        dismissed state intact. No-op when no cache is configured.
        """
        if self._cache is None:
            return
        self._notifications = list(self._cache.list_notifications())

    def add(
        self,
        type: str,
        title: str,
        message: str,
        project_path: Path | None = None,
    ) -> Notification:
        notification = Notification(
            id=str(uuid.uuid4()),
            type=type,
            title=title,
            message=message,
            timestamp=local_now(),
            project_path=project_path,
            dismissed=False,
        )
        self._notifications.append(notification)
        self.notification_added.emit(notification)
        if self._event_publisher is not None:
            self._event_publisher("NOTIFICATION", self._to_event_payload(notification))
        # Persist after the in-memory result is established. A single-statement
        # write leaves the prior persisted state unchanged on failure (no
        # partial update); the error is surfaced via ``write_failed`` rather
        # than crashing notification delivery, retaining the in-memory result.
        if self._cache is not None:
            try:
                self._cache.insert_notification(notification)
            except Exception as exc:  # noqa: BLE001 - retain result, surface error
                self.write_failed.emit("notification create persistence failed", exc)
        return notification

    @staticmethod
    def _to_event_payload(notification: Notification) -> dict[str, object]:
        return {
            "id": notification.id,
            "type": notification.type,
            "title": notification.title,
            "message": notification.message,
            "timestamp": notification.timestamp.isoformat(),
            "project_path": notification.project_path.as_posix() if notification.project_path else None,
            "dismissed": notification.dismissed,
        }

    def get_all(self) -> list[Notification]:
        return list(self._notifications)

    def get_undismissed(self) -> list[Notification]:
        return [n for n in self._notifications if not n.dismissed]

    def get_latest(self, limit: int = 3, undismissed_only: bool = False) -> list[Notification]:
        source = self.get_undismissed() if undismissed_only else self._notifications
        # Latest first
        return sorted(source, key=lambda n: n.timestamp, reverse=True)[:limit]

    def dismiss(self, notification_id: str) -> None:
        for n in self._notifications:
            if n.id == notification_id:
                # Persist the dismissed state before mutating the in-memory
                # flag. If the write fails, retain the prior persisted state
                # with no partial update and surface the error, leaving the
                # in-memory state unchanged so memory and cache stay aligned.
                if self._cache is not None:
                    try:
                        self._cache.set_notification_dismissed(notification_id, True)
                    except Exception as exc:  # noqa: BLE001 - retain state, surface error
                        self.write_failed.emit("notification dismiss persistence failed", exc)
                        return
                n.dismissed = True
                self.notification_dismissed.emit(notification_id)
                break

    def count(self, undismissed_only: bool = False) -> int:
        source = self.get_undismissed() if undismissed_only else self._notifications
        return len(source)
