"""Phase C.5g — JsApi integration surface tests (TDD: RED first)."""

import importlib
import sys

from project_tracker.web import js_api
from project_tracker.web.js_api import JsApi, poll_events


def test_js_api_surface_keeps_existing_methods_and_new_facades():
    api = JsApi(
        dashboard_service=None,
        notification_service=None,
        scanner_service=None,
        scheduler_service=None,
    )

    for name in [
        "dashboard_list_projects",
        "dashboard_summary",
        "dashboard_data",
        "notification_list",
        "notification_latest",
        "notification_count",
        "notification_dismiss",
        "scanner_rebuild_year",
        "scheduler_start",
        "scheduler_stop",
        "scheduler_run_once",
        "scheduler_status",
    ]:
        assert callable(getattr(api, name))
    assert callable(poll_events)


def test_js_api_import_still_does_not_require_pywebview():
    assert "webview" not in sys.modules
    importlib.reload(js_api)
    assert "webview" not in sys.modules
