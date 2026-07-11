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


# ── Task 3: rewrite_appcode_configs ─────────────────────────────────────────

import json

from core.models import AppCodeConfig
from services.bootstrap_service import rewrite_appcode_configs


def test_rewrite_appcode_configs_updates_cicd_shared_path(tmp_path):
    old = tmp_path / "old_root"
    new = tmp_path / "new_root"
    appcode_dir = new / "MYAPP"
    appcode_dir.mkdir(parents=True)
    config = AppCodeConfig(
        display_name="MYAPP",
        cicd_location="shared_root",
        cicd_shared_path=old / "SharedCICD",
    )
    (appcode_dir / "appcode.json").write_text(
        json.dumps(config.to_dict()), encoding="utf-8"
    )
    count = rewrite_appcode_configs(new, old)
    assert count == 1
    data = json.loads((appcode_dir / "appcode.json").read_text(encoding="utf-8"))
    assert data["cicd_shared_path"] == str(new / "SharedCICD")


def test_rewrite_appcode_configs_skips_per_appcode_mode(tmp_path):
    old = tmp_path / "old_root"
    new = tmp_path / "new_root"
    appcode_dir = new / "MYAPP"
    appcode_dir.mkdir(parents=True)
    config = AppCodeConfig(display_name="MYAPP", cicd_location="per_appcode")
    (appcode_dir / "appcode.json").write_text(
        json.dumps(config.to_dict()), encoding="utf-8"
    )
    count = rewrite_appcode_configs(new, old)
    assert count == 0


def test_rewrite_appcode_configs_skips_external_path(tmp_path):
    old = tmp_path / "old_root"
    new = tmp_path / "new_root"
    appcode_dir = new / "MYAPP"
    appcode_dir.mkdir(parents=True)
    external = tmp_path / "external_cicd"
    config = AppCodeConfig(
        display_name="MYAPP",
        cicd_location="shared_root",
        cicd_shared_path=external,
    )
    (appcode_dir / "appcode.json").write_text(
        json.dumps(config.to_dict()), encoding="utf-8"
    )
    count = rewrite_appcode_configs(new, old)
    assert count == 0
    data = json.loads((appcode_dir / "appcode.json").read_text(encoding="utf-8"))
    assert data["cicd_shared_path"] == str(external)


# ── Task 4: migrate_cache ───────────────────────────────────────────────────

from infrastructure.cache_db import CacheDb
from core.models import Notification, local_now
from services.bootstrap_service import migrate_cache


def test_migrate_cache_rewrites_notification_paths(tmp_path):
    old = tmp_path / "old_root"
    new = tmp_path / "new_root"
    old.mkdir()
    new.mkdir()
    db = CacheDb(tmp_path / "test_cache.db")
    db.initialize()
    notif = Notification(
        id="n1",
        type="t10",
        title="Test",
        message="msg",
        timestamp=local_now(),
        project_path=old / "APP" / "2026" / "CR" / "UAT_PREPARE" / "Proj",
        dismissed=False,
    )
    db.insert_notification(notif)
    migrate_cache(db, old, new)
    notifs = db.list_notifications()
    assert len(notifs) == 1
    assert str(notifs[0].project_path).startswith(str(new))
    assert not notifs[0].project_path.is_relative_to(old)


def test_migrate_cache_rewrites_approval_job_paths(tmp_path):
    old = tmp_path / "old_root"
    new = tmp_path / "new_root"
    old.mkdir()
    new.mkdir()
    db = CacheDb(tmp_path / "test_cache2.db")
    db.initialize()
    db.upsert_approval_job({
        "job_id": "j1",
        "project_path": str(old / "APP" / "2026" / "CR" / "UAT_PREPARE" / "Proj"),
        "request_type": "approval",
        "cr_number": "CR001",
        "email_subject": "test",
        "sent_at": "2026-07-11T00:00:00+00:00",
        "status": "polling",
        "reply_received_at": None,
    })
    migrate_cache(db, old, new)
    with db._connect() as conn:
        row = conn.execute("SELECT project_path FROM approval_polling_jobs WHERE job_id = ?", ("j1",)).fetchone()
    assert row is not None
    assert str(new) in row[0]


def test_migrate_cache_deletes_rebuildable_tables(tmp_path):
    old = tmp_path / "old_root"
    new = tmp_path / "new_root"
    old.mkdir()
    new.mkdir()
    db = CacheDb(tmp_path / "test_cache3.db")
    db.initialize()
    with db._connect() as conn:
        conn.execute(
            "INSERT INTO project_index (path, name, year, folder_state) VALUES (?, ?, ?, ?)",
            (str(old / "Proj"), "Proj", "2026", "UAT_PREPARE"),
        )
    migrate_cache(db, old, new)
    with db._connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM project_index").fetchone()[0]
    assert count == 0
