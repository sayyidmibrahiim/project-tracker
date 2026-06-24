"""Outlook service — Windows Outlook COM integration."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class OutlookDraftEmail:
    """Email draft ready to be created in Outlook."""

    to: str
    cc: str
    subject: str
    body: str
    attachment_path: Path | None = None


class OutlookService:
    """Service for Outlook COM integration (Windows only)."""

    def __init__(self) -> None:
        self._outlook = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Initialize Outlook COM on first use (Windows only)."""
        if not self._initialized:
            if sys.platform != "win32":
                raise RuntimeError("Outlook COM is only available on Windows")
            import win32com.client
            self._outlook = win32com.client.Dispatch("Outlook.Application")
            self._initialized = True

    def create_draft_email(self, email: OutlookDraftEmail) -> None:
        """Create an Outlook draft email.

        Args:
            email: OutlookDraftEmail with to/cc/subject/body/attachment.

        Raises:
            RuntimeError: If not running on Windows or Outlook not available.
        """
        self._ensure_initialized()

        mail = self._outlook.CreateItem(0)  # 0 = olMailItem
        mail.To = email.to
        mail.CC = email.cc
        mail.Subject = email.subject
        mail.Body = email.body

        if email.attachment_path:
            mail.Attachments.Add(str(email.attachment_path))

        mail.Save()  # Save as draft

    def send_email(self, email: OutlookDraftEmail) -> None:
        """Send an email via Outlook.

        Args:
            email: OutlookDraftEmail with to/cc/subject/body/attachment.

        Raises:
            RuntimeError: If not running on Windows or Outlook not available.
        """
        self._ensure_initialized()

        mail = self._outlook.CreateItem(0)  # 0 = olMailItem
        mail.To = email.to
        mail.CC = email.cc
        mail.Subject = email.subject
        mail.Body = email.body

        if email.attachment_path:
            mail.Attachments.Add(str(email.attachment_path))

        mail.Send()  # Send immediately
