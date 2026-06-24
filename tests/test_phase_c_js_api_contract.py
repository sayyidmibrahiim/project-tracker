"""Phase C.5a — JsApi response contract tests (TDD: RED first)."""

import importlib
import json
import sys
from dataclasses import FrozenInstanceError

import pytest

from web import js_api
from web.event_queue import clear_events, push_event
from web.js_api import BridgeResponse, fail, ok, poll_events


def test_ok_default_returns_success_shape():
    response = ok()

    assert response == {"ok": True, "data": None, "error": None}


def test_ok_with_data_returns_success_shape_with_data():
    data = {"project_id": "P-1", "count": 2}

    response = ok(data)

    assert response == {"ok": True, "data": data, "error": None}


def test_fail_default_code_returns_error_shape():
    response = fail("boom")

    assert response == {
        "ok": False,
        "data": None,
        "error": {"code": "ERROR", "message": "boom", "details": None},
    }


def test_fail_custom_code_and_details_returns_error_shape():
    details = {"field": "cr_link", "reason": "missing"}

    response = fail("invalid request", code="VALIDATION_ERROR", details=details)

    assert response == {
        "ok": False,
        "data": None,
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "invalid request",
            "details": details,
        },
    }


def test_response_is_json_serializable_for_primitive_payload():
    payload = {"name": "Project", "count": 1, "active": True, "items": ["a", "b"]}

    encoded = json.dumps(ok(payload))

    assert json.loads(encoded) == {"ok": True, "data": payload, "error": None}


def test_bridge_response_is_frozen_dto():
    response = BridgeResponse(ok=True, data=None, error=None)

    with pytest.raises(FrozenInstanceError):
        response.ok = False  # type: ignore[misc]


def test_module_import_does_not_require_pywebview():
    assert "webview" not in sys.modules
    importlib.reload(js_api)
    assert "webview" not in sys.modules


def test_poll_events_returns_ok_response_and_drains_events():
    clear_events()
    push_event("TEST_EVENT", {"key": "value"})

    response = poll_events()

    assert response["ok"] is True
    assert response["error"] is None
    assert response["data"] == [
        {
            "type": "TEST_EVENT",
            "payload": {"key": "value"},
            "timestamp": response["data"][0]["timestamp"],
        }
    ]
    assert poll_events() == {"ok": True, "data": [], "error": None}


def test_poll_events_respects_limit():
    clear_events()
    push_event("FIRST")
    push_event("SECOND")

    response = poll_events(limit=1)

    assert response["ok"] is True
    assert [event["type"] for event in response["data"]] == ["FIRST"]
    remaining = poll_events()
    assert [event["type"] for event in remaining["data"]] == ["SECOND"]


def test_poll_events_exception_returns_fail(monkeypatch):
    def boom(limit=None):
        raise RuntimeError("queue unavailable")

    monkeypatch.setattr(js_api, "drain_events", boom)

    assert poll_events() == {
        "ok": False,
        "data": None,
        "error": {
            "code": "EVENT_POLL_FAILED",
            "message": "queue unavailable",
            "details": None,
        },
    }
