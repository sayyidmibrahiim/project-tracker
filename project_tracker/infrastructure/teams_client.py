from __future__ import annotations

import sys
import time
import webbrowser
from typing import Any

IS_WINDOWS = sys.platform == "win32"


def send_teams_message(
    message: str,
    *,
    teams_auto_send: bool = False,
    countdown_seconds: int = 3,
) -> dict[str, Any]:
    if not IS_WINDOWS:
        dev_message = f"[DEV] Would send Teams: {message[:80]}"
        print(dev_message)
        return {"status": "dev_skipped", "message": dev_message}

    import pyautogui
    import pyperclip

    pyautogui.FAILSAFE = True
    pyperclip.copy(message)
    webbrowser.open("msteams://")
    if not teams_auto_send:
        return {"status": "preview_opened", "message": "Teams message copied for manual paste"}

    time.sleep(countdown_seconds)
    pyautogui.hotkey("ctrl", "v")
    pyautogui.press("enter")
    return {"status": "sent", "message": "Teams message sent"}
