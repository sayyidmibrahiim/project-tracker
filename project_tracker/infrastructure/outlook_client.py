from __future__ import annotations

import sys
import threading
from pathlib import Path
from typing import Any

IS_WINDOWS = sys.platform == "win32"


def create_draft_email(
    to: str,
    cc: str,
    subject: str,
    body: str,
    attachment_path: Path | None = None,
) -> dict[str, Any]:
    if not IS_WINDOWS:
        message = f"[DEV] Would create Outlook draft to {to}: {subject}"
        print(message)
        return {"status": "dev_skipped", "message": message}

    thread = threading.Thread(
        target=_create_draft_email_windows,
        args=(to, cc, subject, body, attachment_path),
        daemon=True,
    )
    thread.start()
    return {"status": "queued", "message": "Outlook draft creation queued"}


def get_contacts() -> list[dict[str, str]]:
    if not IS_WINDOWS:
        return [{"name": "Dev User", "email": "dev@example.local"}]

    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        contacts_folder = namespace.GetDefaultFolder(10)
        contacts: list[dict[str, str]] = []
        for item in contacts_folder.Items:
            name = str(getattr(item, "FullName", "") or "")
            email = str(getattr(item, "Email1Address", "") or "")
            if name or email:
                contacts.append({"name": name, "email": email})
        return contacts
    finally:
        pythoncom.CoUninitialize()


def _create_draft_email_windows(
    to: str,
    cc: str,
    subject: str,
    body: str,
    attachment_path: Path | None,
) -> None:
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)
        mail.To = to
        mail.CC = cc
        mail.Subject = subject
        mail.Body = body
        if attachment_path:
            mail.Attachments.Add(str(attachment_path))
        mail.Display()
    finally:
        pythoncom.CoUninitialize()
