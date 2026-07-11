from __future__ import annotations

from pathlib import Path

from services.bootstrap_service import rewrite_path


def test_rewrite_path_inside_root():
    old = Path("D:/WORK/CR")
    new = Path("C:/Users/user/Documents/Project Tracker")
    result = rewrite_path(Path("D:/WORK/CR/SSID/2026"), old, new)
    assert result == Path("C:/Users/user/Documents/Project Tracker/SSID/2026")


def test_rewrite_path_outside_root():
    old = Path("D:/WORK/CR")
    new = Path("C:/Users/user/Documents/Project Tracker")
    external = Path("D:/Other/Vault")
    result = rewrite_path(external, old, new)
    assert result == external


def test_rewrite_path_none():
    result = rewrite_path(None, Path("D:/WORK"), Path("C:/New"))
    assert result is None


def test_rewrite_path_is_old_root_itself():
    old = Path("D:/WORK/CR")
    new = Path("C:/Users/user/Documents/Project Tracker")
    result = rewrite_path(old, old, new)
    assert result == new


# ── Task 2: rewrite_settings_paths ──────────────────────────────────────────

from core.models import AppSettings, EmailSettings, EmailCategorySettings, TeamsAutomation, TeamsSettings
from services.bootstrap_service import rewrite_settings_paths


def test_rewrite_settings_paths_updates_all_in_root_fields():
    old = Path("D:/WORK/CR")
    new = Path("C:/Users/user/Documents/Project Tracker")
    settings = AppSettings(
        root_folder=old,
        second_brain_folder=old / "SecondBrain",
        file_template_folder=old / "Templates",
        email=EmailSettings(
            template_folder_path=old / "EmailTemplates",
            categories={"ACK_UAT": EmailCategorySettings()},
        ),
        teams=TeamsSettings(
            automations=[TeamsAutomation(
                name="test",
                attachment_paths=[old / "att1.pdf", Path("D:/External/file.pdf")],
            )]
        ),
    )
    result = rewrite_settings_paths(settings, old, new)
    assert result.root_folder == new
    assert result.second_brain_folder == new / "SecondBrain"
    assert result.file_template_folder == new / "Templates"
    assert result.email.template_folder_path == new / "EmailTemplates"
    assert result.teams.automations[0].attachment_paths[0] == new / "att1.pdf"
    assert result.teams.automations[0].attachment_paths[1] == Path("D:/External/file.pdf")


def test_rewrite_settings_paths_preserves_none():
    settings = AppSettings(root_folder=None, second_brain_folder=None)
    result = rewrite_settings_paths(settings, Path("D:/old"), Path("C:/new"))
    assert result.root_folder is None
    assert result.second_brain_folder is None
