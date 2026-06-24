"""Phase C — JsApi ``util_choose_folder`` native folder picker bridge tests.

The bridge wraps pywebview's ``create_file_dialog(FileDialog.FOLDER)`` and must
be defensive: it must not crash when pywebview/windows are unavailable (Linux
dev, tests, headless), and it must return the chosen path (or null on cancel)
inside the standard ``{ok, data, error}`` bridge envelope.
"""

import sys
import types
from unittest.mock import MagicMock

import pytest

from web.js_api import JsApi


def _api() -> JsApi:
    return JsApi(dashboard_service=None)


def _install_fake_webview(monkeypatch, *, windows=None, dialog_result=None, raises=None):
    """Install a fake ``webview`` module so js_api can import it lazily."""
    fake = types.ModuleType("webview")
    fake.FileDialog = types.SimpleNamespace(FOLDER="FileDialog.FOLDER")
    fake.FOLDER_DIALOG = "FOLDER_DIALOG"
    fake.windows = windows if windows is not None else []
    if dialog_result is not None or raises is not None:
        call = MagicMock()
        if raises is not None:
            call.side_effect = raises
        else:
            call.return_value = dialog_result
        # create_file_dialog lives on each window object.
        for w in fake.windows:
            w.create_file_dialog = call
    monkeypatch.setitem(sys.modules, "webview", fake)
    return fake


def test_util_choose_folder_exists_and_is_callable():
    api = _api()
    assert callable(getattr(api, "util_choose_folder", None)), \
        "util_choose_folder bridge method must exist"


def test_util_choose_folder_returns_fail_when_no_webview_window(monkeypatch):
    """When no pywebview window exists (Linux/dev/headless), fail cleanly."""
    _install_fake_webview(monkeypatch, windows=[])
    api = _api()
    result = api.util_choose_folder()
    assert result["ok"] is False
    assert result["error"]["code"] == "FOLDER_PICKER_UNAVAILABLE"


def test_util_choose_folder_returns_chosen_path(monkeypatch):
    """When the user picks a folder, return it in the data field."""
    win = MagicMock()
    fake = _install_fake_webview(monkeypatch, windows=[win], dialog_result=["D:\\WORK\\CR"])
    api = _api()
    result = api.util_choose_folder()
    assert result["ok"] is True
    assert result["data"] == {"path": "D:\\WORK\\CR"}
    win.create_file_dialog.assert_called_once_with(fake.FileDialog.FOLDER)


def test_util_choose_folder_falls_back_to_legacy_constant(monkeypatch):
    """Older pywebview versions without FileDialog still work."""
    win = MagicMock()
    fake = _install_fake_webview(monkeypatch, windows=[win], dialog_result=["D:\\WORK\\CR"])
    delattr(fake, "FileDialog")
    api = _api()
    result = api.util_choose_folder()
    assert result["ok"] is True
    assert result["data"] == {"path": "D:\\WORK\\CR"}
    win.create_file_dialog.assert_called_once_with(fake.FOLDER_DIALOG)


def test_util_choose_folder_returns_null_on_cancel(monkeypatch):
    """Cancel/empty selection must round-trip as ok with null path."""
    win = MagicMock()
    _install_fake_webview(monkeypatch, windows=[win], dialog_result=[])
    api = _api()
    result = api.util_choose_folder()
    assert result["ok"] is True
    assert result["data"] == {"path": None}


def test_util_choose_folder_fails_on_dialog_exception(monkeypatch):
    """A raised exception from the dialog must surface as a fail envelope."""
    win = MagicMock()
    _install_fake_webview(
        monkeypatch, windows=[win], raises=RuntimeError("dialog crashed")
    )
    api = _api()
    result = api.util_choose_folder()
    assert result["ok"] is False
    assert "dialog crashed" in result["error"]["message"]
