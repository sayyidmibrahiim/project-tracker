"""Phase C.3c1 — AutoTransitionService event queue integration tests."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from project_tracker.core.enums import CRState
from project_tracker.core.models import AppSettings
from project_tracker.services.auto_transition_service import AutoTransitionService
from project_tracker.web.event_queue import clear_events, drain_events


@pytest.fixture(autouse=True)
def _isolate_event_queue():
    clear_events()
    yield
    clear_events()


class FakeProjectService:
    def __init__(self, result: bool = True, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[Path, AppSettings, object]] = []

    def auto_transition_in_progress(self, project_path, settings, current_time=None):
        self.calls.append((project_path, settings, current_time))
        if self.error is not None:
            raise self.error
        return self.result


class FakeNotificationService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def add(self, **kwargs):
        self.calls.append(kwargs)


_DEFAULT_PUBLISHER = object()


def _service(
    *,
    project_service: FakeProjectService,
    notification_service: FakeNotificationService | None = None,
    event_publisher=_DEFAULT_PUBLISHER,
) -> AutoTransitionService:
    if event_publisher is _DEFAULT_PUBLISHER:
        service = AutoTransitionService(
            AppSettings(),
            notification_service=notification_service,
        )
    else:
        service = AutoTransitionService(
            AppSettings(),
            notification_service=notification_service,
            event_publisher=event_publisher,
        )
    service._project_service = project_service
    return service


def _metadata(cr_state: CRState = CRState.APPROVED):
    return SimpleNamespace(cr_state=cr_state)


def test_constructor_keeps_existing_zero_publisher_usage():
    service = AutoTransitionService(AppSettings())

    assert service.settings.root_folder is None


def test_successful_transition_pushes_auto_in_progress_event_through_injected_publisher():
    calls: list[tuple[str, dict[str, object] | None]] = []
    project_path = Path("/tmp/project")
    service = _service(
        project_service=FakeProjectService(result=True),
        event_publisher=lambda event_type, payload: calls.append((event_type, payload)),
    )

    service._transition_project(project_path, _metadata())

    assert len(calls) == 1
    event_type, payload = calls[0]
    assert event_type == "AUTO_IN_PROGRESS"
    assert payload == {
        "project_path": str(project_path),
        "project_name": "project",
        "old_state": "APPROVED",
        "new_state": "IN-PROGRESS",
    }


def test_successful_transition_pushes_real_queue_event_by_default():
    project_path = Path("/tmp/project")
    service = _service(project_service=FakeProjectService(result=True))

    service._transition_project(project_path, _metadata())
    events = drain_events()

    assert len(events) == 1
    assert events[0]["type"] == "AUTO_IN_PROGRESS"
    assert events[0]["payload"] == {
        "project_path": str(project_path),
        "project_name": "project",
        "old_state": "APPROVED",
        "new_state": "IN-PROGRESS",
    }


def test_successful_transition_preserves_transition_completed_signal():
    project_path = Path("/tmp/project")
    service = _service(
        project_service=FakeProjectService(result=True),
        event_publisher=None,
    )
    emitted: list[tuple[Path, str, str]] = []
    service.transition_completed.connect(lambda path, old, new: emitted.append((path, old, new)))

    service._transition_project(project_path, _metadata())

    assert emitted == [(project_path, "APPROVED", "IN-PROGRESS")]


def test_successful_transition_preserves_notification_service_behavior():
    project_path = Path("/tmp/project")
    notifications = FakeNotificationService()
    service = _service(
        project_service=FakeProjectService(result=True),
        notification_service=notifications,
        event_publisher=None,
    )

    service._transition_project(project_path, _metadata())

    assert notifications.calls == [
        {
            "type": "INFO",
            "title": "Auto IN-PROGRESS",
            "message": "Project project auto-transitioned to IN-PROGRESS",
            "project_path": project_path,
        }
    ]


def test_false_transition_emits_no_signal_notification_or_event():
    project_path = Path("/tmp/project")
    notifications = FakeNotificationService()
    calls: list[tuple[str, dict[str, object] | None]] = []
    service = _service(
        project_service=FakeProjectService(result=False),
        notification_service=notifications,
        event_publisher=lambda event_type, payload: calls.append((event_type, payload)),
    )
    emitted: list[tuple[Path, str, str]] = []
    service.transition_completed.connect(lambda path, old, new: emitted.append((path, old, new)))

    service._transition_project(project_path, _metadata())

    assert emitted == []
    assert notifications.calls == []
    assert calls == []


def test_failed_transition_preserves_error_signal_and_pushes_no_event():
    project_path = Path("/tmp/project")
    calls: list[tuple[str, dict[str, object] | None]] = []
    service = _service(
        project_service=FakeProjectService(error=RuntimeError("boom")),
        event_publisher=lambda event_type, payload: calls.append((event_type, payload)),
    )
    errors: list[str] = []
    service.error_occurred.connect(errors.append)

    service._transition_project(project_path, _metadata())

    assert errors == ["Auto-transition failed for project: boom"]
    assert calls == []


def test_event_publisher_none_does_not_error_on_success():
    project_path = Path("/tmp/project")
    service = _service(
        project_service=FakeProjectService(result=True),
        event_publisher=None,
    )

    service._transition_project(project_path, _metadata())

    assert drain_events() == []
