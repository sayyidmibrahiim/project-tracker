"""Teams service — Windows Teams automation integration."""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass
from urllib.parse import quote


@dataclass(slots=True)
class TeamsMessage:
    """Teams message ready to be sent."""

    target_email: str
    target_group: str
    mentions: list[str]
    message: str
    auto_send: bool = False


class TeamsService:
    """Service for Teams automation (Windows only)."""

    def __init__(self) -> None:
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Initialize pyautogui on first use (Windows only)."""
        if not self._initialized:
            if sys.platform != "win32":
                raise RuntimeError("Teams automation (pyautogui) is only available on Windows")
            import pyautogui
            pyautogui.FAILSAFE = True
            self._initialized = True

    def send_teams_message(self, message: TeamsMessage, countdown_seconds: int = 3) -> None:
        """Send Teams message via deep link and pyautogui on Windows."""
        self._ensure_initialized()

        import pyautogui

        recipient = message.target_email.strip() or message.target_group.strip()
        body = message.message.strip()
        if not recipient:
            raise ValueError("Teams target email or group is required")
        if not body:
            raise ValueError("Teams message is required")

        deeplink = f"https://teams.microsoft.com/l/chat/0/0?users={quote(recipient)}"
        subprocess.Popen(["cmd", "/c", "start", deeplink], shell=True)

        time.sleep(max(0, countdown_seconds))
        pyautogui.hotkey("ctrl", "m")
        time.sleep(0.1)
        pyautogui.press("tab")
        time.sleep(0.1)
        pyautogui.write(body, interval=0.03)
        if message.auto_send:
            pyautogui.press("enter")
