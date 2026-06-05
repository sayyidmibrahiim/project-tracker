"""Phase C.9 — JsApi app/util/year facade tests (TDD: RED first)."""

import importlib
import sys
from pathlib import Path

from project_tracker.web import js_api
from project_tracker.web.js_api import JsApi


class FakeYearService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def list_years(self) -> list[str]:
        self.calls.append("list_years")
        return ["2025", "2026"]


class ExplodingYearService(FakeYearService):
    def list_years(self) -> list[str]:
        raise RuntimeError("years unavailable")


class FakeNotification:
    def __init__(self, notification_id: str) -> None:
        self.id = notification_id


class FakeNotificationDismissAllService:
    def __init__(self) -> None:
        self.calls: list[object] = []

    def dismiss_all(self) -> int:
        self.calls.append("dismiss_all")
        return 3


class FakeNotificationFallbackService:
    def __init__(self) -> None:
        self.calls: list[object] = []
        self.notifications = [FakeNotification("n-1"), {"id": "n-2"}]

    def get_undismissed(self) -> list[object]:
        self.calls.append("get_undismissed")
        return self.notifications

    def dismiss(self, notification_id: str) -> None:
        self.calls.append(("dismiss", notification_id))


class ExplodingNotificationFallbackService(FakeNotificationFallbackService):
    def get_undismissed(self) -> list[object]:
        raise RuntimeError("dismiss all unavailable")


def test_app_get_status_returns_safe_static_status():
    api = JsApi(dashboard_service=None)

    response = api.app_get_status()

    assert response == {
        "ok": True,
        "data": {
            "app_name": "Project Tracker DBS",
            "backend": "python",
            "phase": "phase_c_js_api",
        },
        "error": None,
    }


def test_util_validate_windows_folder_name_returns_validation_result():
    api = JsApi(dashboard_service=None)

    valid = api.util_validate_windows_folder_name("Valid Folder")
    invalid = api.util_validate_windows_folder_name("CON")

    assert valid == {"ok": True, "data": {"valid": True, "error": None}, "error": None}
    assert invalid["ok"] is True
    assert invalid["data"]["valid"] is False
    assert "reserved" in invalid["data"]["error"]


def test_year_list_delegates_to_injected_service():
    service = FakeYearService()
    api = JsApi(dashboard_service=None, year_service=service)

    response = api.year_list()

    assert response == {"ok": True, "data": ["2025", "2026"], "error": None}
    assert service.calls == ["list_years"]


def test_year_list_missing_service_returns_fail():
    api = JsApi(dashboard_service=None)

    response = api.year_list()

    assert response == {
        "ok": False,
        "data": None,
        "error": {
            "code": "YEAR_LIST_FAILED",
            "message": "year_service is not configured",
            "details": None,
        },
    }


def test_year_list_exception_returns_fail():
    api = JsApi(dashboard_service=None, year_service=ExplodingYearService())

    response = api.year_list()

    assert response == {
        "ok": False,
        "data": None,
        "error": {
            "code": "YEAR_LIST_FAILED",
            "message": "years unavailable",
            "details": None,
        },
    }


def test_notification_dismiss_all_uses_service_method_when_available():
    service = FakeNotificationDismissAllService()
    api = JsApi(dashboard_service=None, notification_service=service)

    response = api.notification_dismiss_all()

    assert response == {"ok": True, "data": {"dismissed": 3}, "error": None}
    assert service.calls == ["dismiss_all"]


def test_notification_dismiss_all_falls_back_to_undismissed_iteration():
    service = FakeNotificationFallbackService()
    api = JsApi(dashboard_service=None, notification_service=service)

    response = api.notification_dismiss_all()

    assert response == {"ok": True, "data": {"dismissed": 2}, "error": None}
    assert service.calls == [
        "get_undismissed",
        ("dismiss", "n-1"),
        ("dismiss", "n-2"),
    ]


def test_notification_dismiss_all_exception_returns_fail():
    api = JsApi(dashboard_service=None, notification_service=ExplodingNotificationFallbackService())

    response = api.notification_dismiss_all()

    assert response == {
        "ok": False,
        "data": None,
        "error": {
            "code": "NOTIFICATION_DISMISS_ALL_FAILED",
            "message": "dismiss all unavailable",
            "details": None,
        },
    }


def test_js_api_app_util_year_import_does_not_require_pywebview():
    assert "webview" not in sys.modules
    importlib.reload(js_api)
    assert "webview" not in sys.modules
