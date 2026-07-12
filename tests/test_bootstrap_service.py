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


# ── Task 5: bootstrap_root ──────────────────────────────────────────────────

from infrastructure.settings_store import SettingsStore
from infrastructure.metadata_store import MetadataStore
from services.scanner_service import ScannerService
from services.bootstrap_service import BootstrapResult, bootstrap_root


def test_bootstrap_creates_default_root_when_none(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    store = SettingsStore(config_dir=config_dir)
    db = CacheDb(tmp_path / "db1.db")
    db.initialize()
    scanner = ScannerService(db)
    result = bootstrap_root(store, db, scanner)
    assert result.action == "created"
    expected = fake_home / "Documents" / "Project Tracker"
    assert expected.exists()
    saved = store.read()
    assert saved.root_folder == expected
    assert saved.second_brain_folder == expected / "Second Brain"
    assert (expected / "Second Brain").is_dir()


def test_bootstrap_none_action_when_already_default(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    expected = fake_home / "Documents" / "Project Tracker"
    expected.mkdir(parents=True)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    store = SettingsStore(config_dir=config_dir)
    settings = store.read()
    settings.root_folder = expected
    store.write(settings)
    db = CacheDb(tmp_path / "db2.db")
    db.initialize()
    scanner = ScannerService(db)
    result = bootstrap_root(store, db, scanner)
    assert result.action == "none"


def test_bootstrap_migrates_existing_root(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    old_root = tmp_path / "old_cr"
    old_root.mkdir()
    (old_root / "MYAPP").mkdir()
    (old_root / "MYAPP" / "appcode.json").write_text(
        '{"display_name":"MYAPP","cicd_location":"per_appcode","cicd_shared_path":"","created_at":null}',
        encoding="utf-8",
    )
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    store = SettingsStore(config_dir=config_dir)
    settings = store.read()
    settings.root_folder = old_root
    store.write(settings)
    db = CacheDb(tmp_path / "db3.db")
    db.initialize()
    scanner = ScannerService(db, MetadataStore())
    result = bootstrap_root(store, db, scanner)
    assert result.action == "migrated"
    expected = fake_home / "Documents" / "Project Tracker"
    assert expected.exists()
    assert (expected / "MYAPP" / "appcode.json").exists()
    assert not old_root.exists()
    saved = store.read()
    assert saved.root_folder == expected
    assert saved.second_brain_folder == expected / "Second Brain"
    assert (expected / "Second Brain").is_dir()


def test_bootstrap_orphan_old_root_missing(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    store = SettingsStore(config_dir=config_dir)
    settings = store.read()
    settings.root_folder = tmp_path / "nonexistent"
    store.write(settings)
    db = CacheDb(tmp_path / "db4.db")
    db.initialize()
    scanner = ScannerService(db)
    result = bootstrap_root(store, db, scanner)
    assert result.action == "created_orphan"
    expected = fake_home / "Documents" / "Project Tracker"
    assert expected.exists()
    assert store.read().root_folder == expected


def test_bootstrap_migration_failure_rollback(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    old_root = tmp_path / "old_cr"
    old_root.mkdir()
    (old_root / "MYAPP").mkdir()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    store = SettingsStore(config_dir=config_dir)
    settings = store.read()
    settings.root_folder = old_root
    store.write(settings)
    db = CacheDb(tmp_path / "db5.db")
    db.initialize()
    scanner = ScannerService(db)
    # Pre-create the default root so direct move target exists,
    # then sabotage move to force failure.
    expected = fake_home / "Documents" / "Project Tracker"
    expected.mkdir(parents=True)
    (expected / "blocker").mkdir()
    import services.bootstrap_service as bs

    def fail_move(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(bs.shutil, "move", fail_move)
    result = bootstrap_root(store, db, scanner)
    assert result.action == "failed"
    assert old_root.exists()  # old data preserved
    assert store.read().second_brain_folder is None  # settings untouched on failure


# ── Task 1: default_second_brain / ensure_second_brain_folder ──────────────

from services.bootstrap_service import default_second_brain, ensure_second_brain_folder


def test_default_second_brain_is_root_slash_second_brain(tmp_path):
    root = tmp_path / "Project Tracker"
    assert default_second_brain(root) == root / "Second Brain"


def test_ensure_second_brain_folder_creates_default_when_unset(tmp_path):
    root = tmp_path / "Project Tracker"
    root.mkdir()
    settings = AppSettings(root_folder=root, second_brain_folder=None)
    changed = ensure_second_brain_folder(settings, root)
    assert changed is True
    assert settings.second_brain_folder == root / "Second Brain"
    assert (root / "Second Brain").is_dir()


def test_ensure_second_brain_folder_preserves_existing_override(tmp_path):
    root = tmp_path / "Project Tracker"
    root.mkdir()
    override = tmp_path / "External" / "Notes"
    settings = AppSettings(root_folder=root, second_brain_folder=override)
    changed = ensure_second_brain_folder(settings, root)
    assert changed is False
    assert settings.second_brain_folder == override
    assert not (root / "Second Brain").exists()


def test_bootstrap_none_action_repairs_unset_second_brain_folder(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    expected = fake_home / "Documents" / "Project Tracker"
    expected.mkdir(parents=True)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    store = SettingsStore(config_dir=config_dir)
    settings = store.read()
    settings.root_folder = expected
    settings.second_brain_folder = None
    store.write(settings)
    db = CacheDb(tmp_path / "db6.db")
    db.initialize()
    scanner = ScannerService(db)
    result = bootstrap_root(store, db, scanner)
    assert result.action == "none"
    saved = store.read()
    assert saved.second_brain_folder == expected / "Second Brain"
    assert (expected / "Second Brain").is_dir()


def test_bootstrap_none_action_preserves_second_brain_override(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)
    expected = fake_home / "Documents" / "Project Tracker"
    expected.mkdir(parents=True)
    override = tmp_path / "External" / "Notes"
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    store = SettingsStore(config_dir=config_dir)
    settings = store.read()
    settings.root_folder = expected
    settings.second_brain_folder = override
    store.write(settings)
    db = CacheDb(tmp_path / "db7.db")
    db.initialize()
    scanner = ScannerService(db)
    result = bootstrap_root(store, db, scanner)
    assert result.action == "none"
    saved = store.read()
    assert saved.second_brain_folder == override
    assert not (expected / "Second Brain").exists()
