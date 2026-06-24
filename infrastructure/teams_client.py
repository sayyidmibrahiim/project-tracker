"""Teams integration client (Windows-only, lazy/guarded).

This module must import cleanly on non-Windows platforms WITHOUT any Windows-only
dependency installed. Every ``pyautogui``/``pyperclip`` import is lazy and lives
inside an ``IS_WINDOWS`` branch. Off-Windows calls return a dev-skipped
Bridge_Response (``ok=true`` with a skipped indicator) and never execute any
``pyautogui`` or ``pyperclip`` action. Runtime failures on Windows surface as
``ok=false`` Bridge_Responses.

Preview_First is the default: a deep link is opened and the message text is placed
on the clipboard with no keystroke/auto-send. Auto-send only runs when the caller
explicitly opts in (``teams_auto_send=True``) and only after a visible countdown.
"""

from __future__ import annotations

import sys
import time
import webbrowser
from typing import Any

IS_WINDOWS = sys.platform == "win32"

#: Default countdown (seconds) substituted whenever the requested value is
#: missing, non-integer, or outside the inclusive 1-60 range (Req 9.3/9.4).
DEFAULT_COUNTDOWN_SECONDS = 3
MIN_COUNTDOWN_SECONDS = 1
MAX_COUNTDOWN_SECONDS = 60


def _ok(data: object | None) -> dict[str, Any]:
    """Build a successful Bridge_Response."""
    return {"ok": True, "data": data, "error": None}


def _dev_skipped(message: str) -> dict[str, Any]:
    """Build a dev-skipped Bridge_Response for non-Windows platforms."""
    return {"ok": True, "data": {"status": "dev_skipped", "message": message}, "error": None}


def _fail(message: str, code: str) -> dict[str, Any]:
    """Build a failure Bridge_Response."""
    return {"ok": False, "data": None, "error": {"code": code, "message": message}}


def normalize_countdown_seconds(value: object) -> int:
    """Normalize a countdown value to an integer in the inclusive 1-60 range.

    Missing, non-integer, or out-of-range values are replaced with the default
    of ``3`` (Req 9.3/9.4). ``bool`` is treated as non-integer because a boolean
    countdown is not a meaningful duration.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        return DEFAULT_COUNTDOWN_SECONDS
    if value < MIN_COUNTDOWN_SECONDS or value > MAX_COUNTDOWN_SECONDS:
        return DEFAULT_COUNTDOWN_SECONDS
    return value


def send_teams_message(
    message: str,
    *,
    teams_auto_send: bool = False,
    countdown_seconds: object = DEFAULT_COUNTDOWN_SECONDS,
) -> dict[str, Any]:
    """Send a Teams message (Preview_First; auto-send only when opted in).

    Returns a Bridge_Response. Off-Windows this is a dev-skipped response and no
    ``pyautogui``/``pyperclip`` action is executed (Req 9.6). Auto-send runs only
    when ``teams_auto_send`` is ``True`` and only after a visible countdown
    derived from ``countdown_seconds`` (default 3, invalid/out-of-range -> 3;
    Req 9.3/9.4). A FAILSAFE trigger or any runtime error aborts the dispatch and
    returns ``ok=false`` without mutating caller state (Req 9.5/9.7).
    """
    if not IS_WINDOWS:
        dev_message = f"[DEV] Would send Teams: {message[:80]}"
        print(dev_message)
        return _dev_skipped(dev_message)

    import pyautogui  # lazy, Windows-only
    import pyperclip  # lazy, Windows-only

    countdown = normalize_countdown_seconds(countdown_seconds)

    try:
        pyautogui.FAILSAFE = True
        pyperclip.copy(message)
        webbrowser.open("msteams://")
        if not teams_auto_send:
            return _ok(
                {
                    "status": "preview_opened",
                    "message": "Teams message copied for manual paste",
                }
            )

        # Visible countdown before any keystroke so the user can abort (Req 9.3).
        for _ in range(countdown):
            time.sleep(1)
        pyautogui.hotkey("ctrl", "v")
        pyautogui.press("enter")
        return _ok({"status": "sent", "message": "Teams message sent", "countdown_seconds": countdown})
    except pyautogui.FailSafeException:
        # Aborted via FAILSAFE: do not dispatch; caller state stays unchanged (Req 9.5/9.7).
        return _fail("Teams auto-send cancelled by failsafe", "TEAMS_SEND_FAILED")
    except Exception as exc:  # noqa: BLE001 - surfaced as ok=false Bridge_Response
        # Runtime failure: caller's auto-send setting and draft are left unchanged (Req 9.7).
        return _fail(str(exc) or exc.__class__.__name__, "TEAMS_SEND_FAILED")
