"""Phase C.5f — JsApi scheduler facade tests (TDD: RED first)."""

from web.js_api import JsApi


class FakeSchedulerService:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.is_running = False

    def start(self) -> None:
        self.calls.append("start")
        self.is_running = True

    def stop(self) -> None:
        self.calls.append("stop")
        self.is_running = False

    def run_once(self) -> None:
        self.calls.append("run_once")


class ExplodingSchedulerService(FakeSchedulerService):
    def start(self) -> None:
        raise RuntimeError("scheduler unavailable")


def test_scheduler_start_calls_service_and_returns_status():
    service = FakeSchedulerService()
    api = JsApi(dashboard_service=None, scheduler_service=service)

    response = api.scheduler_start()

    assert response == {"ok": True, "data": {"is_running": True}, "error": None}
    assert service.calls == ["start"]


def test_scheduler_stop_calls_service_and_returns_status():
    service = FakeSchedulerService()
    service.is_running = True
    api = JsApi(dashboard_service=None, scheduler_service=service)

    response = api.scheduler_stop()

    assert response == {"ok": True, "data": {"is_running": False}, "error": None}
    assert service.calls == ["stop"]


def test_scheduler_run_once_calls_service_and_returns_status():
    service = FakeSchedulerService()
    api = JsApi(dashboard_service=None, scheduler_service=service)

    response = api.scheduler_run_once()

    assert response == {"ok": True, "data": {"is_running": False}, "error": None}
    assert service.calls == ["run_once"]


def test_scheduler_status_returns_is_running():
    service = FakeSchedulerService()
    service.is_running = True
    api = JsApi(dashboard_service=None, scheduler_service=service)

    response = api.scheduler_status()

    assert response == {"ok": True, "data": {"is_running": True}, "error": None}


def test_scheduler_exception_returns_fail():
    api = JsApi(dashboard_service=None, scheduler_service=ExplodingSchedulerService())

    response = api.scheduler_start()

    assert response == {
        "ok": False,
        "data": None,
        "error": {
            "code": "SCHEDULER_START_FAILED",
            "message": "scheduler unavailable",
            "details": None,
        },
    }
