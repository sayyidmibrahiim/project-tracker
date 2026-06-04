"""Phase C.4b — AutoTransitionService scheduler integration tests."""

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


class FakeScheduler:
    def __init__(self) -> None:
        self.jobs: list[dict[str, object]] = []
        self.start_calls = 0
        self.shutdown_calls: list[dict[str, object]] = []
        self.running = False

    def add_job(self, func, **kwargs):
        self.jobs.append({"func": func, **kwargs})

    def start(self) -> None:
        self.start_calls += 1
        self.running = True

    def shutdown(self, wait: bool = True) -> None:
        self.shutdown_calls.append({"wait": wait})
        self.running = False


class FakeProjectService:
    def __init__(self, result: bool = True) -> None:
        self.result = result
        self.calls: list[tuple] = []

    def auto_transition_in_progress(self, project_path, settings, current_time=None):
        self.calls.append((project_path, settings, current_time))
        return self.result


def _service(
    *,
    fake_scheduler: FakeScheduler | None = None,
    interval_seconds: int = 60,
    event_publisher=None,
) -> AutoTransitionService:
    scheduler = fake_scheduler or FakeScheduler()
    service = AutoTransitionService(
        AppSettings(),
        event_publisher=event_publisher,
        scheduler=scheduler,
    )
    return service


def test_start_delegates_to_scheduler_service():
    scheduler = FakeScheduler()
    service = _service(fake_scheduler=scheduler, interval_seconds=60)

    service.start()

    assert scheduler.start_calls == 1
    assert len(scheduler.jobs) == 1
    job = scheduler.jobs[0]
    assert job["trigger"] == "interval"
    assert job["id"] == "auto_transition_check"
    assert job["replace_existing"] is True


def test_stop_delegates_to_scheduler_shutdown():
    scheduler = FakeScheduler()
    service = _service(fake_scheduler=scheduler)
    service.start()

    service.stop()

    assert scheduler.shutdown_calls == [{"wait": False}]


def test_stop_safe_if_not_started():
    scheduler = FakeScheduler()
    service = _service(fake_scheduler=scheduler)

    service.stop()

    assert scheduler.shutdown_calls == []


def test_repeated_start_does_not_duplicate_jobs():
    scheduler = FakeScheduler()
    service = _service(fake_scheduler=scheduler)

    service.start()
    service.start()

    assert len(scheduler.jobs) == 1
    assert scheduler.start_calls == 1


def test_set_interval_rebuilds_scheduler_service():
    scheduler = FakeScheduler()
    service = _service(fake_scheduler=scheduler, interval_seconds=60)

    service.set_interval(30000)

    assert service._scheduler_service._interval_seconds == 30


def test_check_and_transition_remains_callable():
    service = _service()
    service.settings = AppSettings(root_folder=None)

    service._check_and_transition()


def test_start_job_func_calls_check_and_transition():
    scheduler = FakeScheduler()
    service = _service(fake_scheduler=scheduler)
    service.settings = AppSettings(root_folder=None)
    service.start()

    job_func = scheduler.jobs[0]["func"]
    job_func()


def test_event_emission_still_works_through_scheduler_path():
    scheduler = FakeScheduler()
    calls: list[tuple[str, dict[str, object] | None]] = []
    service = AutoTransitionService(
        AppSettings(),
        event_publisher=lambda event_type, payload: calls.append((event_type, payload)),
        scheduler=scheduler,
    )
    fake_ps = FakeProjectService(result=True)
    service._project_service = fake_ps
    project_path = Path("/tmp/project")
    metadata = SimpleNamespace(cr_state=CRState.APPROVED)

    service._transition_project(project_path, metadata)

    assert len(calls) == 1
    assert calls[0][0] == "AUTO_IN_PROGRESS"
