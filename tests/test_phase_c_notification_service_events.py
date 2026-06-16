"""Phase C.3b — NotificationService event queue integration tests."""

from datetime import datetime
from pathlib import Path

import pytest

from project_tracker.core.models import Notification
from project_tracker.services.notification_service import NotificationService
from project_tracker.web.event_queue import clear_events, drain_events


@pytest.fixture(autouse=True)
def _isolate_event_queue():
    clear_events()
    yield
    clear_events()


def test_add_returns_notification_and_stores_it():
    service = NotificationService(event_publisher=None)

    notification = service.add("INFO", "Title", "Message")

    assert isinstance(notification, Notification)
    assert service.get_all() == [notification]


def test_add_pushes_notification_event_to_queue():
    service = NotificationService()

    notification = service.add("INFO", "Title", "Message")
    events = drain_events()

    assert len(events) == 1
    assert events[0]["type"] == "NOTIFICATION"
    assert events[0]["payload"]["id"] == notification.id


def test_notification_event_payload_contains_frontend_safe_fields(tmp_path):
    project_path = tmp_path / "2026" / "UAT_PREPARE" / "PROJECT_A"
    service = NotificationService()

    notification = service.add("WARNING", "Heads up", "Check project", project_path)
    event = drain_events()[0]
    payload = event["payload"]

    assert payload == {
        "id": notification.id,
        "type": "WARNING",
        "title": "Heads up",
        "message": "Check project",
        "timestamp": notification.timestamp.isoformat(),
        "project_path": project_path.as_posix(),
        "dismissed": False,
    }


def test_notification_event_payload_project_path_none_stays_none():
    service = NotificationService()

    service.add("INFO", "Title", "Message")
    payload = drain_events()[0]["payload"]

    assert payload["project_path"] is None


def test_notification_event_payload_timestamp_is_timezone_aware_iso():
    service = NotificationService()

    service.add("INFO", "Title", "Message")
    payload = drain_events()[0]["payload"]
    parsed = datetime.fromisoformat(payload["timestamp"])

    assert parsed.tzinfo is not None


def test_notification_added_signal_still_emits_notification():
    service = NotificationService(event_publisher=None)
    emitted: list[Notification] = []
    service.notification_added.connect(emitted.append)

    notification = service.add("INFO", "Title", "Message")

    assert emitted == [notification]


def test_dismiss_marks_notification_and_emits_signal_without_queue_event():
    service = NotificationService()
    dismissed_ids: list[str] = []
    service.notification_dismissed.connect(dismissed_ids.append)
    notification = service.add("INFO", "Title", "Message")
    clear_events()

    service.dismiss(notification.id)

    assert notification.dismissed is True
    assert dismissed_ids == [notification.id]
    assert drain_events() == []


def test_injected_publisher_receives_notification_event():
    calls: list[tuple[str, dict[str, object] | None]] = []
    service = NotificationService(event_publisher=lambda event_type, payload: calls.append((event_type, payload)))

    notification = service.add("INFO", "Title", "Message", Path("/tmp/project"))

    assert len(calls) == 1
    event_type, payload = calls[0]
    assert event_type == "NOTIFICATION"
    assert payload == {
        "id": notification.id,
        "type": "INFO",
        "title": "Title",
        "message": "Message",
        "timestamp": notification.timestamp.isoformat(),
        "project_path": "/tmp/project",
        "dismissed": False,
    }
