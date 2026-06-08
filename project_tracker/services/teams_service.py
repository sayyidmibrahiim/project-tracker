"""Teams service — orchestrates Preview_First / opt-in auto-send Teams messaging.

This service layer owns the Teams orchestration rules and delegates all native,
Windows-only automation to :mod:`project_tracker.infrastructure.teams_client`
(``services -> infrastructure``). It never imports ``pyautogui``/``pyperclip``
directly so it stays import-clean on Linux.

Behavior (Req 9.2-9.7):

* Preview_First is the default — :meth:`TeamsService.preview_message` opens the
  deep link and copies text with no keystroke/auto-send.
* ``teams_auto_send`` is treated as ``False`` whenever it is absent/unset
  (Req 9.2); auto-send happens only on an explicit ``True``.
* Auto-send runs only after a visible countdown derived from ``countdown_seconds``
  (default ``3``, invalid/out-of-range -> ``3``; Req 9.3/9.4), normalized by the
  client.
* FAILSAFE aborts and runtime failures surface as ``ok=false`` Bridge_Responses
  and leave the caller's auto-send setting and draft unchanged (Req 9.5/9.7).
* Off-Windows calls return a dev-skipped Bridge_Response (Req 9.6).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from project_tracker.infrastructure.teams_client import (
    DEFAULT_COUNTDOWN_SECONDS,
    normalize_countdown_seconds,
    send_teams_message,
)

SendTeamsMessage = Callable[..., dict[str, Any]]


@dataclass(slots=True)
class TeamsMessage:
    """Teams message ready to be previewed or sent."""

    target_email: str
    target_group: str
    mentions: list[str]
    message: str
    auto_send: bool = False


def normalize_auto_send(value: object) -> bool:
    """Resolve the ``teams_auto_send`` setting, defaulting to ``False``.

    Any absent/unset value (``None``) or non-``True`` value resolves to ``False``
    so auto-send only ever runs on an explicit opt-in (Req 9.2).
    """
    return value is True


def build_message_text(message: TeamsMessage) -> str:
    """Compose the message body, prefixing any @mentions."""
    mentions = " ".join(f"@{mention.strip()}" for mention in message.mentions if mention.strip())
    body = message.message.strip()
    if mentions and body:
        return f"{mentions} {body}"
    return mentions or body


class TeamsService:
    """Service for Teams automation (Preview_First by default, opt-in auto-send)."""

    def __init__(self, sender: SendTeamsMessage | None = None) -> None:
        # Injectable for testing; defaults to the guarded infrastructure client.
        self._send: SendTeamsMessage = sender or send_teams_message

    def preview_message(self, message: TeamsMessage) -> dict[str, Any]:
        """Preview_First: open the deep link and copy text, never auto-send (Req 9.1)."""
        text = build_message_text(message)
        return self._send(text, teams_auto_send=False)

    def send_message(
        self,
        message: TeamsMessage,
        *,
        teams_auto_send: object = None,
        countdown_seconds: object = DEFAULT_COUNTDOWN_SECONDS,
    ) -> dict[str, Any]:
        """Send a Teams message, auto-sending only on an explicit opt-in.

        ``teams_auto_send`` defaults to the message's own flag when not provided,
        and resolves to ``False`` whenever absent/unset (Req 9.2). Auto-send runs
        only after the client's visible countdown (Req 9.3/9.4). When auto-send is
        not enabled this behaves as Preview_First.
        """
        opt_in = teams_auto_send if teams_auto_send is not None else message.auto_send
        auto_send = normalize_auto_send(opt_in)
        countdown = normalize_countdown_seconds(countdown_seconds)
        text = build_message_text(message)
        return self._send(text, teams_auto_send=auto_send, countdown_seconds=countdown)
