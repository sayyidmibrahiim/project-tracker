from __future__ import annotations

from pathlib import Path


def test_outlook_client_imports_without_windows_dependencies() -> None:
    from project_tracker.infrastructure import outlook_client

    assert outlook_client.IS_WINDOWS is False


def test_outlook_create_draft_email_returns_dev_result_on_linux(tmp_path: Path) -> None:
    from project_tracker.infrastructure.outlook_client import create_draft_email

    result = create_draft_email(
        to="dev@example.local",
        cc="",
        subject="Deployment notice",
        body="Body",
        attachment_path=tmp_path / "evidence.txt",
    )

    assert result == {
        "status": "dev_skipped",
        "message": "[DEV] Would create Outlook draft to dev@example.local: Deployment notice",
    }


def test_outlook_get_contacts_returns_dev_contact_on_linux() -> None:
    from project_tracker.infrastructure.outlook_client import get_contacts

    assert get_contacts() == [{"name": "Dev User", "email": "dev@example.local"}]


def test_teams_client_imports_without_windows_dependencies() -> None:
    from project_tracker.infrastructure import teams_client

    assert teams_client.IS_WINDOWS is False


def test_teams_send_message_returns_dev_result_on_linux() -> None:
    from project_tracker.infrastructure.teams_client import send_teams_message

    result = send_teams_message("Deployment ready", teams_auto_send=False)

    assert result == {
        "status": "dev_skipped",
        "message": "[DEV] Would send Teams: Deployment ready",
    }
