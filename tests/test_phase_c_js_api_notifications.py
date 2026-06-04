"""Phase C.5d — JsApi notification method tests (TDD: RED first)."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from project_tracker.web.js_api import JsApi


@dataclass(frozen=True)
class FakeNotification:
    id: str
    type: str
    title: str
    message: str
    timestamp: datetime
    project_path: Path | None
    dismissed: bool


class FakeNotificationService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []
        self.notification = FakeNotification(
            id="n-1",
            type="INFO",
            title="Ready",
            message="Project ready",
            timestamp=datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
            project_path=Path("/tmp/projects/2026/UAT_PREPARE/P-1"),
            dismissed=False,
        )

    def get_all(self) -> list[FakeNotification]:
        self.calls.append(("get_all", None))
        return [self.notification]

    def get_undismissed(self) -> list[FakeNotification]:
        self.calls.append(("get_undismissed", None))
        return [self.notification]

    def get_latest(self, limit: int = 3, undismissed_only: bool = False) -> list[FakeNotification]:
        self.calls.append(("get_latest", (limit, undismissed_only)))
        return [self.notification]

    def count(self, undismissed_only: bool = False) -> int:
        self.calls.append(("count", undismissed_only))
        return 1

    def dismiss(self, notification_id: str) -> None:
        self.calls.append(("dismiss", notification_id))


class ExplodingNotificationService(FakeNotificationService):
    def get_all(self) -> list[FakeNotification]:
        raise RuntimeError("list unavailable")

    def get_latest(self, limit: int = 3, undismissed_only: bool = False) -> list[FakeNotification]:
        raise RuntimeError("latest unavailable")

    def count(self, undismissed_only: bool = False) -> int:
        raise RuntimeError("count unavailable")

    def dismiss(self, notification_id: str) -> None:
        raise RuntimeError("dismiss unavailable")


def test_notification_list_returns_converted_notifications():
    service = FakeNotificationService()
    api = JsApi(dashboard_service=None, notification_service=service)

    response = api.notification_list()

    assert response == {
        "ok": True,
        "data": [
            {
                "id": "n-1",
                "type": "INFO",
                "title": "Ready",
                "message": "Project ready",
                "timestamp": "2026-01-02T03:04:05+00:00",
                "project_path": "/tmp/projects/2026/UAT_PREPARE/P-1",
                "dismissed": False,
            }
        ],
        "error": None,
    }
    assert service.calls == [("get_all", None)]


def test_notification_list_can_request_undismissed_only():
    service = FakeNotificationService()
    api = JsApi(dashboard_service=None, notification_service=service)

    response = api.notification_list(undismissed_only=True)

    assert response["ok"] is True
    assert service.calls == [("get_undismissed", None)]


def test_notification_latest_passes_limit_and_undismissed_args():
    service = FakeNotificationService()
    api = JsApi(dashboard_service=None, notification_service=service)

    response = api.notification_latest(limit=5, undismissed_only=True)

    assert response["ok"] is True
    assert response["data"][0]["id"] == "n-1"
    assert service.calls == [("get_latest", (5, True))]


def test_notification_count_returns_count():
    service = FakeNotificationService()
    api = JsApi(dashboard_service=None, notification_service=service)

    response = api.notification_count(undismissed_only=True)

    assert response == {"ok": True, "data": 1, "error": None}
    assert service.calls == [("count", True)]


def test_notification_dismiss_calls_service_and_returns_ok():
    service = FakeNotificationService()
    api = JsApi(dashboard_service=None, notification_service=service)

    response = api.notification_dismiss("n-1")

    assert response == {"ok": True, "data": None, "error": None}
    assert service.calls == [("dismiss", "n-1")]


def test_notification_exception_returns_fail_response():
    api = JsApi(dashboard_service=None, notification_service=ExplodingNotificationService())

    response = api.notification_list()

    assert response == {
        "ok": False,
        "data": None,
        "error": {
            "code": "NOTIFICATION_LIST_FAILED",
            "message": "list unavailable",
            "details": None,
        },
    }
