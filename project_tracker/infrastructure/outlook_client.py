"""Outlook integration client (Windows-only, lazy/guarded).

This module must import cleanly on non-Windows platforms WITHOUT any Windows-only
dependency installed. Every ``win32com``/``pythoncom`` import is lazy and lives
inside an ``IS_WINDOWS`` branch. Off-Windows calls return a dev-skipped
Bridge_Response and never execute COM. COM calls on Windows run on a dedicated
background thread that calls ``CoInitialize`` before any COM access and
``CoUninitialize`` before the thread terminates, in try/finally, including on
error — COM is never left initialized, and errors surface as ``ok=false``.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Any, Callable

IS_WINDOWS = sys.platform == "win32"


def _ok(data: object | None) -> dict[str, Any]:
    """Build a successful Bridge_Response."""
    return {"ok": True, "data": data, "error": None}


def _dev_skipped(message: str) -> dict[str, Any]:
    """Build a dev-skipped Bridge_Response for non-Windows platforms."""
    return {"ok": True, "data": {"status": "dev_skipped", "message": message}, "error": None}


def _fail(message: str, code: str) -> dict[str, Any]:
    """Build a failure Bridge_Response."""
    return {"ok": False, "data": None, "error": {"code": code, "message": message}}


def _run_on_com_thread(work: Callable[[], Any], *, error_code: str) -> dict[str, Any]:
    """Run a COM callable on a dedicated background thread.

    The worker thread calls ``CoInitialize`` before any COM access and always
    calls ``CoUninitialize`` before terminating — in try/finally — so COM is
    never left initialized, even when ``work`` raises. Any error is captured and
    returned as an ``ok=false`` Bridge_Response; success is returned as
    ``ok=true`` carrying the worker's result in ``data``.
    """
    captured: dict[str, Any] = {}

    def _runner() -> None:
        import pythoncom  # lazy, Windows-only

        pythoncom.CoInitialize()
        try:
            captured["data"] = work()
        except Exception as exc:  # noqa: BLE001 - surfaced as ok=false Bridge_Response
            captured["error"] = str(exc) or exc.__class__.__name__
        finally:
            pythoncom.CoUninitialize()

    thread = threading.Thread(target=_runner, daemon=True)
    thread.start()
    thread.join()

    if "error" in captured:
        return _fail(captured["error"], error_code)
    return _ok(captured.get("data"))


def create_draft_email(
    to: str,
    cc: str,
    subject: str,
    body: str,
    attachment_path: Path | None = None,
) -> dict[str, Any]:
    """Create an Outlook draft email (Draft_First; never sends).

    Returns a Bridge_Response. Off-Windows this is a dev-skipped response and no
    COM is executed.
    """
    if not IS_WINDOWS:
        message = f"[DEV] Would create Outlook draft to {to}: {subject}"
        print(message)
        return _dev_skipped(message)

    def _work() -> dict[str, Any]:
        import win32com.client  # lazy, Windows-only

        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)  # 0 = olMailItem
        mail.To = to
        mail.CC = cc
        mail.Subject = subject
        mail.Body = body
        if attachment_path:
            mail.Attachments.Add(str(attachment_path))
        mail.Display()
        return {"status": "drafted", "subject": subject}

    return _run_on_com_thread(_work, error_code="OUTLOOK_COM_ERROR")


def send_email(
    to: str,
    cc: str,
    subject: str,
    body: str,
    attachment_path: Path | None = None,
) -> dict[str, Any]:
    """Send an Outlook email (the explicit send path; only called after confirm).

    Mirrors :func:`create_draft_email` but calls ``Send`` instead of ``Display``.
    Returns a Bridge_Response. Off-Windows this is a dev-skipped response and no
    COM is executed. A runtime failure surfaces as ``ok=false`` without claiming
    the email was sent.
    """
    if not IS_WINDOWS:
        message = f"[DEV] Would send Outlook email to {to}: {subject}"
        print(message)
        return _dev_skipped(message)

    def _work() -> dict[str, Any]:
        import win32com.client  # lazy, Windows-only

        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)  # 0 = olMailItem
        mail.To = to
        mail.CC = cc
        mail.Subject = subject
        mail.Body = body
        if attachment_path:
            mail.Attachments.Add(str(attachment_path))
        mail.Send()
        return {"status": "sent", "subject": subject}

    return _run_on_com_thread(_work, error_code="OUTLOOK_COM_ERROR")


def get_contacts() -> dict[str, Any]:
    """Return Outlook contacts as a Bridge_Response.

    Off-Windows returns a dev fallback contact; no COM is executed.
    """
    if not IS_WINDOWS:
        return _ok({"contacts": [{"name": "Dev User", "email": "dev@example.local"}]})

    def _work() -> dict[str, Any]:
        import win32com.client  # lazy, Windows-only

        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        contacts_folder = namespace.GetDefaultFolder(10)  # 10 = olFolderContacts
        contacts: list[dict[str, str]] = []
        for item in contacts_folder.Items:
            name = str(getattr(item, "FullName", "") or "")
            email = str(getattr(item, "Email1Address", "") or "")
            if name or email:
                contacts.append({"name": name, "email": email})
        return {"contacts": contacts}

    return _run_on_com_thread(_work, error_code="OUTLOOK_COM_ERROR")
