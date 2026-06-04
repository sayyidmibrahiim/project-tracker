"""Phase C.4a — SchedulerService foundation tests."""

from project_tracker.services.scheduler_service import SchedulerService


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


def test_construct_service_without_starting_scheduler():
    scheduler = FakeScheduler()
    calls: list[str] = []

    service = SchedulerService(job=lambda: calls.append("run"), scheduler=scheduler)

    assert service.is_running is False
    assert scheduler.jobs == []
    assert scheduler.start_calls == 0
    assert calls == []


def test_run_once_calls_job_once():
    calls: list[str] = []
    service = SchedulerService(job=lambda: calls.append("run"), scheduler=FakeScheduler())

    service.run_once()

    assert calls == ["run"]


def test_start_adds_interval_job_and_starts_scheduler():
    scheduler = FakeScheduler()
    service = SchedulerService(job=lambda: None, interval_seconds=30, scheduler=scheduler)

    service.start()

    assert service.is_running is True
    assert scheduler.start_calls == 1
    assert len(scheduler.jobs) == 1
    job = scheduler.jobs[0]
    assert job["trigger"] == "interval"
    assert job["seconds"] == 30
    assert job["id"] == "scheduler_service_interval_job"
    assert job["replace_existing"] is True


def test_start_uses_custom_job_id():
    scheduler = FakeScheduler()
    service = SchedulerService(job=lambda: None, interval_seconds=30, scheduler=scheduler, job_id="custom_job")

    service.start()

    assert scheduler.jobs[0]["id"] == "custom_job"


def test_repeated_start_does_not_duplicate_job_or_restart_scheduler():
    scheduler = FakeScheduler()
    service = SchedulerService(job=lambda: None, interval_seconds=60, scheduler=scheduler)

    service.start()
    service.start()

    assert len(scheduler.jobs) == 1
    assert scheduler.start_calls == 1


def test_stop_shuts_down_running_scheduler_without_waiting():
    scheduler = FakeScheduler()
    service = SchedulerService(job=lambda: None, scheduler=scheduler)
    service.start()

    service.stop()

    assert service.is_running is False
    assert scheduler.shutdown_calls == [{"wait": False}]


def test_stop_safe_if_not_started():
    scheduler = FakeScheduler()
    service = SchedulerService(job=lambda: None, scheduler=scheduler)

    service.stop()

    assert service.is_running is False
    assert scheduler.shutdown_calls == []


def test_job_exception_from_run_once_propagates_to_caller():
    service = SchedulerService(job=lambda: (_ for _ in ()).throw(RuntimeError("boom")), scheduler=FakeScheduler())

    try:
        service.run_once()
    except RuntimeError as exc:
        assert str(exc) == "boom"
    else:
        raise AssertionError("RuntimeError was not raised")
