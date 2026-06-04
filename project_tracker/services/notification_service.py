from pathlib import Path
from collections.abc import Callable
import uuid

from project_tracker.core.models import Notification, local_now
from project_tracker.web.event_queue import push_event


class Signal:
    def __init__(self) -> None:
        self._callbacks: list[Callable[..., None]] = []

    def connect(self, callback: Callable[..., None]) -> None:
        self._callbacks.append(callback)

    def emit(self, *args: object) -> None:
        for callback in list(self._callbacks):
            callback(*args)


class NotificationService:
    def __init__(
        self,
        event_publisher: Callable[[str, dict[str, object] | None], None] | None = push_event,
    ) -> None:
        self.notification_added = Signal()  # emits Notification
        self.notification_dismissed = Signal()  # emits notification_id
        self._event_publisher = event_publisher
        self._notifications: list[Notification] = []

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
        return notification

    @staticmethod
    def _to_event_payload(notification: Notification) -> dict[str, object]:
        return {
            "id": notification.id,
            "type": notification.type,
            "title": notification.title,
            "message": notification.message,
            "timestamp": notification.timestamp.isoformat(),
            "project_path": str(notification.project_path) if notification.project_path else None,
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
                n.dismissed = True
                self.notification_dismissed.emit(notification_id)
                break

    def count(self, undismissed_only: bool = False) -> int:
        source = self.get_undismissed() if undismissed_only else self._notifications
        return len(source)
