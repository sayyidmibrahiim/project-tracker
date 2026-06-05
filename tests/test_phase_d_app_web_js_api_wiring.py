"""Phase D-pre: app_web → JsApi wiring tests.

TDD RED: these tests fail because app_web does not yet expose a
JsApi-backed factory or delegate to JsApi from the pywebview bootstrap.
"""

from __future__ import annotations

import pytest


# ── RED 1: import safety ──────────────────────────────────────────────────

def test_app_web_import_is_linux_safe():
    """app_web.py must import without crashing on Linux (no pywebview at import)."""
    from project_tracker import app_web  # noqa: F401


# ── RED 2: factory creates JsApi ──────────────────────────────────────────

def test_app_web_exposes_create_js_api_factory():
    """app_web must expose a create_js_api() callable."""
    from project_tracker import app_web

    assert hasattr(app_web, "create_js_api"), (
        "app_web must expose create_js_api factory"
    )
    assert callable(app_web.create_js_api)


def test_create_js_api_returns_JsApi_instance():
    """create_js_api() must return a JsApi instance."""
    from project_tracker import app_web
    from project_tracker.web.js_api import JsApi

    api = app_web.create_js_api()
    assert isinstance(api, JsApi), (
        f"create_js_api() must return JsApi, got {type(api)}"
    )


# ── RED 3: factory wires dashboard service ────────────────────────────────

def test_create_js_api_wires_dashboard_service():
    """JsApi from factory must serve dashboard_list_projects without crash."""
    from project_tracker import app_web

    api = app_web.create_js_api()
    result = api.dashboard_list_projects()
    assert isinstance(result, dict)
    assert result.get("ok") is True


# ── RED 4: factory wires notification service ─────────────────────────────

def test_create_js_api_wires_notification_service():
    """JsApi from factory must serve notification_list without crash."""
    from project_tracker import app_web

    api = app_web.create_js_api()
    result = api.notification_list()
    assert isinstance(result, dict)
    assert result.get("ok") is True


# ── RED 5: factory wires settings service ─────────────────────────────────

def test_create_js_api_wires_settings_service():
    """JsApi from factory must serve settings_get without crash."""
    from project_tracker import app_web

    api = app_web.create_js_api()
    result = api.settings_get()
    assert isinstance(result, dict)
    assert result.get("ok") is True


# ── RED 6: factory wires project service ──────────────────────────────────

def test_create_js_api_wires_project_service():
    """JsApi from factory delegates project_list to adapter (wired via D-pre.2)."""
    from project_tracker import app_web

    api = app_web.create_js_api()
    result = api.project_list()
    assert isinstance(result, dict)
    assert result.get("ok") is True


# ── RED 7: factory wires automation service ───────────────────────────────

def test_create_js_api_wires_automation_service():
    """JsApi from factory must serve automation_list_rules without crash."""
    from project_tracker import app_web

    api = app_web.create_js_api()
    result = api.automation_list_rules()
    assert isinstance(result, dict)
    assert result.get("ok") is True


# ── RED 8: factory wires second brain service ─────────────────────────────

def test_create_js_api_wires_second_brain_service():
    """JsApi from factory must serve second_brain_list without crash."""
    from project_tracker import app_web

    api = app_web.create_js_api()
    result = api.second_brain_list()
    assert isinstance(result, dict)
    assert result.get("ok") is True


# ── RED 9: factory wires report service ───────────────────────────────────

def test_create_js_api_wires_report_service():
    """JsApi from factory must serve report_filter_projects without crash."""
    from project_tracker import app_web

    api = app_web.create_js_api()
    result = api.report_filter_projects()
    assert isinstance(result, dict)
    assert result.get("ok") is True


# ── RED 10: factory wires notification_dismiss_all ────────────────────────

def test_create_js_api_wires_notification_dismiss_all():
    """JsApi from factory must serve notification_dismiss_all without crash."""
    from project_tracker import app_web

    api = app_web.create_js_api()
    result = api.notification_dismiss_all()
    assert isinstance(result, dict)
    assert result.get("ok") is True
