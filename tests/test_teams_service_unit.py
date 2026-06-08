"""Unit tests for Teams preview/send orchestration (Task 17.3).

Covers Req 9.2-9.6 at the service + client layer on Linux:

* ``teams_auto_send`` defaults to ``False`` whenever absent/unset (Req 9.2).
* ``countdown_seconds`` clamps/normalizes invalid or out-of-range values to ``3``
  (Req 9.3/9.4).
* A ``pyautogui`` FAILSAFE trigger aborts auto-send and returns ``ok=false``
  without dispatching (Req 9.5).
* Off-Windows calls are dev-skipped and never invoke ``pyautogui``/``pyperclip``
  (Req 9.6) — asserted here directly in addition to the P10 property test.

The FAILSAFE/keystroke paths are exercised by simulating ``IS_WINDOWS`` and
injecting fake ``pyautogui``/``pyperclip`` modules; no real native automation runs
and no dependency is added.
"""

from __future__ import annotations

import sys
import types

from project_tracker.infrastructure import teams_client
from project_tracker.infrastructure.teams_client import (
    DEFAULT_COUNTDOWN_SECONDS,
    normalize_countdown_seconds,
    send_teams_message,
)
from project_tracker.services.teams_service import (
    TeamsMessage,
    TeamsService,
    build_message_text,
    normalize_auto_send,
)


# --- normalize_auto_send (Req 9.2) -------------------------------------------

def test_auto_send_defaults_false_for_absent_or_non_true() -> None:
    assert normalize_auto_send(None) is False
    assert normalize_auto_send("true") is False
    assert normalize_auto_send(1) is False
    assert normalize_auto_send(False) is False
    assert normalize_auto_send(True) is True


# --- normalize_countdown_seconds (Req 9.3/9.4) -------------------------------

def test_countdown_clamps_invalid_and_out_of_range_to_default() -> None:
    assert normalize_countdown_seconds(0) == DEFAULT_COUNTDOWN_SECONDS  # below min
    assert normalize_countdown_seconds(61) == DEFAULT_COUNTDOWN_SECONDS  # above max
    assert normalize_countdown_seconds(True) == DEFAULT_COUNTDOWN_SECONDS  # bool
    assert normalize_countdown_seconds("3") == DEFAULT_COUNTDOWN_SECONDS  # non-int
    assert normalize_countdown_seconds(None) == DEFAULT_COUNTDOWN_SECONDS
    assert normalize_countdown_seconds(1) == 1  # in-range low
    assert normalize_countdown_seconds(60) == 60  # in-range high


# --- TeamsService orchestration ----------------------------------------------

def _capturing_service() -> tuple[TeamsService, list[dict[str, object]]]:
    calls: list[dict[str, object]] = []

    def fake_sender(text: str, **kwargs: object) -> dict[str, object]:
        calls.append({"text": text, **kwargs})
        return {"ok": True, "data": None, "error": None}

    return TeamsService(sender=fake_sender), calls


def test_preview_message_is_preview_first_even_when_auto_send_flag_set() -> None:
    service, calls = _capturing_service()
    service.preview_message(TeamsMessage("", "", [], "hello", auto_send=True))
    assert calls == [{"text": "hello", "teams_auto_send": False}]


def test_send_message_defaults_auto_send_false_when_unset() -> None:
    service, calls = _capturing_service()
    service.send_message(TeamsMessage("", "", [], "hi", auto_send=False))
    assert calls[0]["teams_auto_send"] is False


def test_send_message_opt_in_true_and_countdown_normalized() -> None:
    service, calls = _capturing_service()
    service.send_message(
        TeamsMessage("", "", [], "hi"), teams_auto_send=True, countdown_seconds=999
    )
    assert calls[0]["teams_auto_send"] is True
    assert calls[0]["countdown_seconds"] == DEFAULT_COUNTDOWN_SECONDS


def test_send_message_falls_back_to_message_flag_when_opt_in_none() -> None:
    service, calls = _capturing_service()
    service.send_message(TeamsMessage("", "", [], "hi", auto_send=True))
    assert calls[0]["teams_auto_send"] is True


def test_build_message_text_prefixes_mentions() -> None:
    assert build_message_text(TeamsMessage("", "", ["alice", " bob "], "ping")) == "@alice @bob ping"


# --- off-Windows dev-skip (Req 9.6) ------------------------------------------

def test_off_windows_send_is_dev_skipped(monkeypatch) -> None:
    monkeypatch.setattr(teams_client, "IS_WINDOWS", False)
    resp = send_teams_message("hello", teams_auto_send=True, countdown_seconds=3)
    assert resp["ok"] is True
    assert resp["data"]["status"] == "dev_skipped"


# --- simulated-Windows preview + FAILSAFE abort (Req 9.5) --------------------


class _FakeFailSafeException(Exception):
    """Stand-in for ``pyautogui.FailSafeException`` so the FailSafe branch is hit."""


def _install_fake_native(monkeypatch, *, raise_failsafe_on_hotkey: bool = False) -> dict[str, list]:
    calls: dict[str, list] = {"hotkey": [], "press": [], "copy": []}

    fake_pyautogui = types.ModuleType("pyautogui")
    fake_pyautogui.FailSafeException = _FakeFailSafeException
    fake_pyautogui.FAILSAFE = False

    def _hotkey(*args: object, **_: object) -> None:
        calls["hotkey"].append(args)
        if raise_failsafe_on_hotkey:
            raise _FakeFailSafeException("moved to corner")

    fake_pyautogui.hotkey = _hotkey
    fake_pyautogui.press = lambda *a, **_: calls["press"].append(a)

    fake_pyperclip = types.ModuleType("pyperclip")
    fake_pyperclip.copy = lambda text: calls["copy"].append(text)

    monkeypatch.setitem(sys.modules, "pyautogui", fake_pyautogui)
    monkeypatch.setitem(sys.modules, "pyperclip", fake_pyperclip)
    monkeypatch.setattr(teams_client, "IS_WINDOWS", True)
    monkeypatch.setattr(teams_client, "webbrowser", types.SimpleNamespace(open=lambda *a, **k: None))
    monkeypatch.setattr(teams_client.time, "sleep", lambda *_: None)
    return calls


def test_simulated_windows_preview_first_never_presses_keys(monkeypatch) -> None:
    calls = _install_fake_native(monkeypatch)
    resp = send_teams_message("hi", teams_auto_send=False)
    assert resp["ok"] is True
    assert resp["data"]["status"] == "preview_opened"
    assert calls["hotkey"] == [] and calls["press"] == []


def test_simulated_windows_failsafe_abort_returns_ok_false(monkeypatch) -> None:
    calls = _install_fake_native(monkeypatch, raise_failsafe_on_hotkey=True)
    resp = send_teams_message("hi", teams_auto_send=True, countdown_seconds=1)
    assert resp["ok"] is False
    assert resp["error"]["code"] == "TEAMS_SEND_FAILED"
    assert calls["press"] == []  # never reached the enter keystroke
