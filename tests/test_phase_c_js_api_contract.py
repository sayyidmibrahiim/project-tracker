"""Phase C.5a — JsApi response contract tests (TDD: RED first)."""

import importlib
import json
import sys
from dataclasses import FrozenInstanceError

import pytest

from project_tracker.web import js_api
from project_tracker.web.js_api import BridgeResponse, fail, ok


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
