"""Unit tests confirming DownloadEmailService stores attachments under the
target project folder (Requirement 8.8). These exercise the path-construction
logic without a live Outlook COM object."""

from __future__ import annotations

from pathlib import Path

from core.models import DownloadEmailJob, local_now
from services.download_email_service import DownloadEmailWorker


class FakeAttachment:
    def __init__(self, filename: str) -> None:
        self.FileName = filename
        self.saved_to: str | None = None

    def SaveAsFile(self, path: str) -> None:  # noqa: N802 - mimics COM API
        self.saved_to = path
        Path(path).write_text("attachment-bytes", encoding="utf-8")


class FakeAttachments:
    """Mimics the Outlook Attachments collection (1-indexed Count + Item)."""

    def __init__(self, attachments: list[FakeAttachment]) -> None:
        self._items = attachments
        self.Count = len(attachments)

    def Item(self, index: int) -> FakeAttachment:  # noqa: N802 - mimics COM API
        return self._items[index - 1]


class FakeMailItem:
    def __init__(self, attachments: list[FakeAttachment]) -> None:
        self.Attachments = FakeAttachments(attachments)


def _worker(project_path: Path) -> DownloadEmailWorker:
    job = DownloadEmailJob(
        job_id="job-1",
        cr_number="CR-2026-001",
        project_name="Alpha",
        project_path=project_path,
        start_time=local_now(),
        status="active",
    )
    return DownloadEmailWorker(job)


def test_attachments_saved_under_project_folder(tmp_path: Path):
    worker = _worker(tmp_path)
    att = FakeAttachment("report.pdf")
    item = FakeMailItem([att])

    worker._save_attachments(item)

    saved = Path(att.saved_to)
    assert saved.parent == tmp_path
    assert saved.name == "report.pdf"
    assert saved.exists()


def test_attachment_filename_is_basenamed_into_project_folder(tmp_path: Path):
    """Even a filename with path separators lands directly under the project folder."""
    worker = _worker(tmp_path)
    att = FakeAttachment("subdir/evil.txt")
    item = FakeMailItem([att])

    worker._save_attachments(item)

    saved = Path(att.saved_to)
    assert saved.parent == tmp_path
    assert saved.name == "evil.txt"


def test_no_attachments_is_noop(tmp_path: Path):
    worker = _worker(tmp_path)
    item = FakeMailItem([])

    worker._save_attachments(item)

    assert list(tmp_path.iterdir()) == []


def test_item_without_attachments_attr_is_noop(tmp_path: Path):
    worker = _worker(tmp_path)

    worker._save_attachments(object())

    assert list(tmp_path.iterdir()) == []
