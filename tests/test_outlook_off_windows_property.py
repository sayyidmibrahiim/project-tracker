"""Property-based test for Property 10: off-Windows guard never executes native automation.

Design Correctness Property 10 (prd-completion design.md):
    For any Outlook/Teams call on a non-Windows platform, no COM/``pyautogui``/
    ``pyperclip`` is invoked and a dev-skipped response is returned.

**Validates: Requirements 7.2, 9.6**

This suite runs on Linux, where ``IS_WINDOWS = sys.platform == "win32"`` is
``False`` for both ``outlook_client`` and ``teams_client``. Every Outlook/Teams
client function is therefore expected to take its guarded dev path and never
reach any lazy Windows-only import (``pythoncom`` / ``win32com`` for COM,
``pyautogui`` / ``pyperclip`` for Teams automation).

The property is enforced with two complementary, robust strategies:

* **Booby-trap strategy** -- before each call we install *exploding* module
  objects under the native-automation import names in ``sys.modules``. Any
  attribute access on them (which is the only way the client code could drive
  COM/keyboard/clipboard automation) records the access and raises. After the
  call we assert that nothing was ever touched, proving native automation was
  not invoked even if the modules had somehow been importable.
* **Absence strategy** -- with nothing injected, we snapshot ``sys.modules``,
  make the call, and assert the native-automation modules are still absent
  afterwards, proving the guarded path performed no lazy import at all.

The PRD v3.1 dependency baseline does not include ``hypothesis`` and the
release-candidate hard rules forbid adding dependencies, so arbitrary arguments
are produced with a deterministic, seeded ``random.Random`` generator -- the
same pattern used by the sibling property tests in this spec. No filesystem is
mutated (attachment paths are constructed but never written) and no real
dependency is added.
"""

from __future__ import annotations

import random
import sys
import types
from pathlib import Path
from typing import Any, Callable

import pytest

from project_tracker.infrastructure import outlook_client, teams_client
from project_tracker.infrastructure.outlook_client import (
    create_draft_email,
    get_contacts,
    send_email,
)
from project_tracker.infrastructure.teams_client import send_teams_message

# Number of randomized examples explored per property. Kept modest so the suite
# stays fast while still covering a broad slice of the argument space.
EXAMPLES = 200

# The lazy, Windows-only modules the client code would have to import to drive
# real native automation. On a non-Windows platform none of these may be
# imported or touched.
NATIVE_MODULE_NAMES = ("pythoncom", "win32com", "win32com.client", "pyautogui", "pyperclip")

_TEXT_POOL = (
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "
    "@.:/<>|?*\\\"'-_()[]{}#$%&+=,;~"
    "проекتمشروع项目-éüñ漢字🚀\n\t"
)


class _ExplodingAccess(Exception):
    """Raised if booby-trapped native automation is ever touched."""


def _make_exploding_module(name: str, recorder: list[tuple[str, str]]) -> types.ModuleType:
    """Build a module that records and rejects any attribute access.

    Driving COM, keyboard, or clipboard automation requires accessing an
    attribute (``win32com.client.Dispatch``, ``pythoncom.CoInitialize``,
    ``pyautogui.hotkey``, ``pyperclip.copy`` ...). Trapping every attribute
    access therefore proves no native automation was invoked. A ``__path__`` is
    provided so the object is a valid package placeholder for
    ``win32com.client`` resolution without itself triggering the trap.
    """

    class _Exploding(types.ModuleType):
        __path__: list[str] = []  # marks it as a package; not routed via __getattr__

        def __getattr__(self, attr: str) -> Any:
            recorder.append((name, attr))
            raise _ExplodingAccess(
                f"native automation touched off-Windows: {name}.{attr}"
            )

    return _Exploding(name)


def _assert_no_native_modules_present() -> None:
    """Fail if any real native-automation module is currently imported."""
    present = [n for n in NATIVE_MODULE_NAMES if n in sys.modules]
    assert not present, f"native automation modules unexpectedly imported: {present}"


def _call_with_booby_traps(call: Callable[[], dict[str, Any]]) -> tuple[dict[str, Any], list[tuple[str, str]]]:
    """Run ``call`` with exploding native modules installed; return result + accesses."""
    recorder: list[tuple[str, str]] = []
    saved: dict[str, types.ModuleType | None] = {
        name: sys.modules.get(name) for name in NATIVE_MODULE_NAMES
    }
    for name in NATIVE_MODULE_NAMES:
        sys.modules[name] = _make_exploding_module(name, recorder)
    try:
        result = call()
    finally:
        for name, module in saved.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
    return result, recorder


def _assert_dev_skipped(result: dict[str, Any], expected_prefix: str, label: str) -> None:
    """Assert ``result`` is a dev-skipped Bridge_Response for a guarded call."""
    assert result["ok"] is True, f"{label}: expected ok=true, got {result!r}"
    assert result["error"] is None, f"{label}: expected error=None, got {result!r}"
    data = result["data"]
    assert isinstance(data, dict), f"{label}: data not a dict: {result!r}"
    assert data.get("status") == "dev_skipped", f"{label}: not dev_skipped: {result!r}"
    assert str(data.get("message", "")).startswith(expected_prefix), (
        f"{label}: unexpected dev-skipped message: {result!r}"
    )


def _rand_text(rng: random.Random, *, allow_empty: bool = True) -> str:
    """Generate an arbitrary text argument from a diverse character pool."""
    low = 0 if allow_empty else 1
    length = rng.randint(low, 60)
    return "".join(rng.choice(_TEXT_POOL) for _ in range(length))


def _rand_attachment(rng: random.Random) -> Path | None:
    """Generate an arbitrary (never written) attachment path, or ``None``."""
    if rng.random() < 0.4:
        return None
    return Path("/tmp") / f"evidence_{rng.randint(0, 9999)}" / f"{_rand_text(rng, allow_empty=False)}.dat"


def _rand_countdown(rng: random.Random) -> object:
    """Generate an arbitrary countdown_seconds value (valid, out-of-range, or junk)."""
    kind = rng.randrange(6)
    if kind == 0:
        return rng.randint(1, 60)  # in range
    if kind == 1:
        return rng.randint(-100, 0)  # below range
    if kind == 2:
        return rng.randint(61, 1000)  # above range
    if kind == 3:
        return rng.choice([True, False])  # bool (treated as non-integer)
    if kind == 4:
        return rng.choice([None, "3", 3.5, [], {}])  # non-integer junk
    return None


# --- Sanity: confirm we really are exercising the non-Windows guarded path. ---

def test_clients_are_on_non_windows_guarded_path() -> None:
    """Both clients must report a non-Windows platform for this property to apply."""
    assert outlook_client.IS_WINDOWS is False
    assert teams_client.IS_WINDOWS is False


def test_property_off_windows_never_invokes_native_automation() -> None:
    """Property 10: arbitrary Outlook/Teams calls never touch native automation.

    For every generated argument set, each client call returns its guarded dev
    response AND the booby-trapped native modules are never accessed -- proving
    no COM/``pyautogui``/``pyperclip`` automation is invoked off-Windows.
    """
    for seed in range(EXAMPLES):
        rng = random.Random(seed)

        to = _rand_text(rng)
        cc = _rand_text(rng)
        subject = _rand_text(rng)
        body = _rand_text(rng)
        attachment = _rand_attachment(rng)
        message = _rand_text(rng)
        auto_send = rng.choice([True, False])
        countdown = _rand_countdown(rng)

        # Outlook draft (dev-skipped).
        result, accesses = _call_with_booby_traps(
            lambda: create_draft_email(to=to, cc=cc, subject=subject, body=body, attachment_path=attachment)
        )
        assert accesses == [], f"create_draft_email touched native automation (seed={seed}): {accesses}"
        _assert_dev_skipped(result, f"[DEV] Would create Outlook draft to {to}", f"create_draft_email seed={seed}")

        # Outlook send (dev-skipped; must never actually send).
        result, accesses = _call_with_booby_traps(
            lambda: send_email(to=to, cc=cc, subject=subject, body=body, attachment_path=attachment)
        )
        assert accesses == [], f"send_email touched native automation (seed={seed}): {accesses}"
        _assert_dev_skipped(result, f"[DEV] Would send Outlook email to {to}", f"send_email seed={seed}")

        # Outlook contacts (dev fallback: ok=true with a fallback contact).
        result, accesses = _call_with_booby_traps(get_contacts)
        assert accesses == [], f"get_contacts touched native automation (seed={seed}): {accesses}"
        assert result["ok"] is True and result["error"] is None, f"get_contacts not ok (seed={seed}): {result!r}"
        contacts = result["data"]["contacts"]
        assert contacts == [{"name": "Dev User", "email": "dev@example.local"}], (
            f"get_contacts did not return the dev fallback (seed={seed}): {result!r}"
        )

        # Teams send (dev-skipped) across arbitrary auto-send / countdown values.
        result, accesses = _call_with_booby_traps(
            lambda: send_teams_message(message, teams_auto_send=auto_send, countdown_seconds=countdown)
        )
        assert accesses == [], f"send_teams_message touched native automation (seed={seed}): {accesses}"
        _assert_dev_skipped(result, "[DEV] Would send Teams:", f"send_teams_message seed={seed}")


def test_property_off_windows_does_not_import_native_modules() -> None:
    """Property 10 (absence form): guarded calls perform no lazy native import.

    With nothing injected into ``sys.modules``, every Outlook/Teams call must
    leave the native-automation modules unimported, confirming the guarded path
    never reaches the lazy ``import`` statements.
    """
    for seed in range(EXAMPLES):
        rng = random.Random(10_000 + seed)

        to = _rand_text(rng)
        cc = _rand_text(rng)
        subject = _rand_text(rng)
        body = _rand_text(rng)
        attachment = _rand_attachment(rng)
        message = _rand_text(rng)
        auto_send = rng.choice([True, False])
        countdown = _rand_countdown(rng)

        _assert_no_native_modules_present()

        create_draft_email(to=to, cc=cc, subject=subject, body=body, attachment_path=attachment)
        _assert_no_native_modules_present()

        send_email(to=to, cc=cc, subject=subject, body=body, attachment_path=attachment)
        _assert_no_native_modules_present()

        get_contacts()
        _assert_no_native_modules_present()

        send_teams_message(message, teams_auto_send=auto_send, countdown_seconds=countdown)
        _assert_no_native_modules_present()


@pytest.mark.parametrize("module_name", NATIVE_MODULE_NAMES)
def test_native_modules_not_in_baseline(module_name: str) -> None:
    """The native-automation modules are not part of the Linux dependency baseline."""
    assert module_name not in sys.modules
