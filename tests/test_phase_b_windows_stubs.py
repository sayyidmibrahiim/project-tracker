from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    sys.platform == "win32",
    reason="Off-Windows dev-stub behavior; on the Windows target these clients run live.",
)


def test_outlook_client_imports_without_windows_dependencies() -> None:
    from infrastructure import outlook_client

    assert outlook_client.IS_WINDOWS is False


def test_outlook_create_draft_email_returns_dev_skipped_bridge_response(tmp_path: Path) -> None:
    from infrastructure.outlook_client import create_draft_email

    result = create_draft_email(
        to="dev@example.local",
        cc="",
        subject="Deployment notice",
        body="Body",
        attachment_path=tmp_path / "evidence.txt",
    )

    assert result == {
        "ok": True,
        "data": {
            "status": "dev_skipped",
            "message": "[DEV] Would create Outlook draft to dev@example.local: Deployment notice",
        },
        "error": None,
    }


def test_outlook_get_contacts_returns_dev_contact_bridge_response() -> None:
    from infrastructure.outlook_client import get_contacts

    result = get_contacts()

    assert result == {
        "ok": True,
        "data": {"contacts": [{"name": "Dev User", "email": "dev@example.local"}]},
        "error": None,
    }


def test_teams_client_imports_without_windows_dependencies() -> None:
    from infrastructure import teams_client

    assert teams_client.IS_WINDOWS is False


def test_teams_send_message_returns_dev_skipped_bridge_response() -> None:
    from infrastructure.teams_client import send_teams_message

    result = send_teams_message("Deployment ready", teams_auto_send=False)

    assert result == {
        "ok": True,
        "data": {
            "status": "dev_skipped",
            "message": "[DEV] Would send Teams: Deployment ready",
        },
        "error": None,
    }


def test_com_thread_initializes_and_uninitializes_in_try_finally() -> None:
    """The COM background thread must CoInitialize then CoUninitialize even on error.

    This exercises the guarded COM thread pattern without any real Windows
    dependency by injecting a fake ``pythoncom`` module and forcing the worker
    to raise. COM must never be left initialized, and the error must surface as
    an ok=false Bridge_Response.
    """
    import sys
    import types

    calls: list[str] = []
    fake_pythoncom = types.ModuleType("pythoncom")
    fake_pythoncom.CoInitialize = lambda: calls.append("init")  # type: ignore[attr-defined]
    fake_pythoncom.CoUninitialize = lambda: calls.append("uninit")  # type: ignore[attr-defined]

    from infrastructure import outlook_client

    sys.modules["pythoncom"] = fake_pythoncom
    try:
        def _boom() -> None:
            raise RuntimeError("COM exploded")

        result = outlook_client._run_on_com_thread(_boom, error_code="OUTLOOK_COM_ERROR")
    finally:
        del sys.modules["pythoncom"]

    assert calls == ["init", "uninit"]
    assert result["ok"] is False
    assert result["data"] is None
    assert result["error"]["code"] == "OUTLOOK_COM_ERROR"
    assert "COM exploded" in result["error"]["message"]


def test_com_thread_success_returns_ok_bridge_response() -> None:
    """A successful COM worker returns ok=true and still uninitializes COM."""
    import sys
    import types

    calls: list[str] = []
    fake_pythoncom = types.ModuleType("pythoncom")
    fake_pythoncom.CoInitialize = lambda: calls.append("init")  # type: ignore[attr-defined]
    fake_pythoncom.CoUninitialize = lambda: calls.append("uninit")  # type: ignore[attr-defined]

    from infrastructure import outlook_client

    sys.modules["pythoncom"] = fake_pythoncom
    try:
        result = outlook_client._run_on_com_thread(
            lambda: {"status": "drafted"}, error_code="OUTLOOK_COM_ERROR"
        )
    finally:
        del sys.modules["pythoncom"]

    assert calls == ["init", "uninit"]
    assert result == {"ok": True, "data": {"status": "drafted"}, "error": None}
