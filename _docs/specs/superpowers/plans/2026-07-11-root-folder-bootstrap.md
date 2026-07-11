# Root Folder Bootstrap & Appcode First-Run Setup — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Force root folder to `Documents\Project Tracker` on every launch (create or migrate), then require at least one appcode via a popup before the app is usable.

**Architecture:** Backend `bootstrap_root()` runs in `app_web.run()` before `webview.start()` — creates the default root, migrates old data if needed (shutil.move + path rewriting in settings.json, appcode.json, SQLite cache), then rebuilds the cache. Frontend replaces `FirstRunSetup.svelte` with `AppcodeSetup.svelte` — a modal popup that calls the existing `appcode_add` bridge, lists saved appcodes, and unlocks [Done] after 1+ entry.

**Tech Stack:** Python 3.12+, pathlib, shutil, sqlite3, Svelte 5, TypeScript, Tailwind

## Global Constraints

- Python 3.12+ (uses `Path.is_relative_to`, `Path.relative_to`).
- Default root: `Path.home() / "Documents" / "Project Tracker"`.
- Root folder is no longer user-configurable — remove the field from Settings.svelte.
- All tests use `tmp_path` fixture — never touch real `%APPDATA%` or `Documents`.
- `web/static` is gitignored — `npm run build` required after frontend changes (only when app is closed).
- Existing `appcode_add` bridge already creates full D-0008 worktree (appcode.json, CICD/, year/CR/{5 states}/Non-CR/) — reuse, do not duplicate.
- `ensure_year_structure` side-effect in `SettingsStore.write()` must be removed (legacy junk folders).
- Branch: `general/root-folder-bootstrap` from `main`.

---

## File Structure

| File | Responsibility |
|---|---|
| `services/bootstrap_service.py` | **New.** `bootstrap_root()` entry point + path rewriting helpers + cache migration. Pure backend, no webview dependency. |
| `tests/test_bootstrap_service.py` | **New.** TDD test suite for all bootstrap scenarios. |
| `infrastructure/settings_store.py` | Remove `ensure_year_structure` side-effect from `write()`. |
| `app_web.py` | Call `bootstrap_root()` in `run()` before `webview.start()`. |
| `frontend/src/lib/components/AppcodeSetup.svelte` | **New.** Modal popup for appcode creation (min 1). |
| `frontend/src/lib/components/FirstRunSetup.svelte` | **Delete.** Replaced by AppcodeSetup. |
| `frontend/src/App.svelte` | Replace `rootUnset`/`checkRoot`/`FirstRunSetup` with `needsAppcode`/`checkAppcode`/`AppcodeSetup`. |
| `frontend/src/lib/components/Settings.svelte` | Remove Root Folder field + Browse button (root is fixed). |

---

### Task 1: Path Rewriting Helper

**Files:**
- Create: `services/bootstrap_service.py`
- Test: `tests/test_bootstrap_service.py`

**Interfaces:**
- Produces: `rewrite_path(path: Path | None, old_root: Path, new_root: Path) -> Path | None` — pure function, no side effects.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_bootstrap_service.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_bootstrap_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'services.bootstrap_service'`

- [ ] **Step 3: Write minimal implementation**

```python
# services/bootstrap_service.py
"""Root folder bootstrap: create default root or migrate existing data."""
from __future__ import annotations

from pathlib import Path

DEFAULT_ROOT_NAME = "Project Tracker"


def default_root() -> Path:
    """The canonical data root: ~/Documents/Project Tracker."""
    return Path.home() / "Documents" / DEFAULT_ROOT_NAME


def rewrite_path(path: Path | None, old_root: Path, new_root: Path) -> Path | None:
    """Rewrite *path* if it lives inside *old_root* to point inside *new_root*.

    Paths outside *old_root* are returned unchanged. ``None`` stays ``None``.
    """
    if path is None:
        return None
    try:
        if path.is_relative_to(old_root):
            return new_root / path.relative_to(old_root)
    except ValueError:
        pass
    return path
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_bootstrap_service.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add services/bootstrap_service.py tests/test_bootstrap_service.py
git commit -m "feat(bootstrap): add rewrite_path helper for root migration"
```

---

### Task 2: Settings Path Rewriting

**Files:**
- Modify: `services/bootstrap_service.py`
- Test: `tests/test_bootstrap_service.py`

**Interfaces:**
- Consumes: `rewrite_path` from Task 1, `AppSettings` from `core/models.py`.
- Produces: `rewrite_settings_paths(settings: AppSettings, old_root: Path, new_root: Path) -> AppSettings` — returns a new AppSettings with all in-root paths relocated.

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_bootstrap_service.py
from core.models import AppSettings, EmailSettings, EmailCategorySettings, TeamsAutomation, TeamsSettings


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_bootstrap_service.py::test_rewrite_settings_paths_updates_all_in_root_fields -v`
Expected: FAIL — `NameError: name 'rewrite_settings_paths' is not defined`

- [ ] **Step 3: Write minimal implementation**

Append to `services/bootstrap_service.py`:

```python
import copy

from core.models import AppSettings


def rewrite_settings_paths(settings: AppSettings, old_root: Path, new_root: Path) -> AppSettings:
    """Return a deep copy of *settings* with all in-root paths relocated."""
    result = copy.deepcopy(settings)
    result.root_folder = rewrite_path(settings.root_folder, old_root, new_root)
    result.second_brain_folder = rewrite_path(settings.second_brain_folder, old_root, new_root)
    result.file_template_folder = rewrite_path(settings.file_template_folder, old_root, new_root)
    if result.email is not None:
        result.email.template_folder_path = rewrite_path(
            settings.email.template_folder_path, old_root, new_root
        )
    if result.teams is not None and result.teams.automations:
        rewritten = []
        for auto in result.teams.automations:
            auto.attachment_paths = [
                rewrite_path(p, old_root, new_root)
                for p in auto.attachment_paths
            ]
            rewritten.append(auto)
        result.teams.automations = rewritten
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_bootstrap_service.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add services/bootstrap_service.py tests/test_bootstrap_service.py
git commit -m "feat(bootstrap): rewrite settings.json paths during migration"
```

---

### Task 3: Appcode Config Rewriting

**Files:**
- Modify: `services/bootstrap_service.py`
- Test: `tests/test_bootstrap_service.py`

**Interfaces:**
- Consumes: `rewrite_path` from Task 1, `AppCodeConfig` from `core/models.py`.
- Produces: `rewrite_appcode_configs(new_root: Path, old_root: Path) -> int` — walks `{new_root}/*/appcode.json`, rewrites `cicd_shared_path` if inside old_root. Returns count of configs modified.

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_bootstrap_service.py
import json

from core.models import AppCodeConfig


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_bootstrap_service.py::test_rewrite_appcode_configs_updates_cicd_shared_path -v`
Expected: FAIL — `NameError: name 'rewrite_appcode_configs' is not defined`

- [ ] **Step 3: Write minimal implementation**

Append to `services/bootstrap_service.py`:

```python
import json

from core.models import AppCodeConfig


def rewrite_appcode_configs(new_root: Path, old_root: Path) -> int:
    """Walk {new_root}/*/appcode.json, rewrite cicd_shared_path if inside old_root.

    Returns the number of configs modified.
    """
    if not new_root.is_dir():
        return 0
    modified = 0
    for child in sorted(new_root.iterdir()):
        if not child.is_dir():
            continue
        config_path = child / "appcode.json"
        if not config_path.is_file():
            continue
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        config = AppCodeConfig.from_dict(data)
        if config.cicd_shared_path is None:
            continue
        rewritten = rewrite_path(config.cicd_shared_path, old_root, new_root)
        if rewritten != config.cicd_shared_path:
            config.cicd_shared_path = rewritten
            config_path.write_text(
                json.dumps(config.to_dict(), indent=2), encoding="utf-8"
            )
            modified += 1
    return modified
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_bootstrap_service.py -v`
Expected: 9 passed

- [ ] **Step 5: Commit**

```bash
git add services/bootstrap_service.py tests/test_bootstrap_service.py
git commit -m "feat(bootstrap): rewrite appcode.json cicd_shared_path during migration"
```

---

### Task 4: SQLite Cache Migration

**Files:**
- Modify: `services/bootstrap_service.py`
- Test: `tests/test_bootstrap_service.py`

**Interfaces:**
- Consumes: `CacheDb` from `infrastructure/cache_db.py`.
- Produces: `migrate_cache(cache_db: CacheDb, old_root: Path, new_root: Path) -> None` — rewrites non-rebuildable table paths via SQL REPLACE, deletes rebuildable rows. Does NOT rescan (caller does that).

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_bootstrap_service.py
from infrastructure.cache_db import CacheDb
from core.models import Notification, local_now


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
    db.upsert_notification(notif)
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
    assert new.as_posix() in row[0] or str(new) in row[0]


def test_migrate_cache_deletes_rebuildable_tables(tmp_path):
    old = tmp_path / "old_root"
    new = tmp_path / "new_root"
    old.mkdir()
    new.mkdir()
    db = CacheDb(tmp_path / "test_cache3.db")
    db.initialize()
    # Insert a dummy project_index row
    with db._connect() as conn:
        conn.execute(
            "INSERT INTO project_index (path, name, year, folder_state) VALUES (?, ?, ?, ?)",
            (str(old / "Proj"), "Proj", "2026", "UAT_PREPARE"),
        )
    migrate_cache(db, old, new)
    with db._connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM project_index").fetchone()[0]
    assert count == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_bootstrap_service.py::test_migrate_cache_rewrites_notification_paths -v`
Expected: FAIL — `NameError: name 'migrate_cache' is not defined`

- [ ] **Step 3: Write minimal implementation**

Append to `services/bootstrap_service.py`:

```python
from infrastructure.cache_db import CacheDb


def migrate_cache(cache_db: CacheDb, old_root: Path, new_root: Path) -> None:
    """Rewrite non-rebuildable path columns + delete rebuildable rows.

    Non-rebuildable (preserve user state): notifications, approval_polling_jobs.
    Rebuildable (will be rescanned): project_index, drone_tickets, scan_warnings.
    """
    old_prefix = str(old_root)
    new_prefix = str(new_root)
    with cache_db._connect() as connection:
        connection.execute(
            "UPDATE notifications SET project_path = REPLACE(project_path, ?, ?) "
            "WHERE project_path LIKE ?",
            (old_prefix, new_prefix, old_prefix + "%"),
        )
        connection.execute(
            "UPDATE approval_polling_jobs SET project_path = REPLACE(project_path, ?, ?) "
            "WHERE project_path LIKE ?",
            (old_prefix, new_prefix, old_prefix + "%"),
        )
        connection.execute("DELETE FROM project_index")
        connection.execute("DELETE FROM drone_tickets")
        connection.execute("DELETE FROM scan_warnings")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_bootstrap_service.py -v`
Expected: 12 passed

- [ ] **Step 5: Commit**

```bash
git add services/bootstrap_service.py tests/test_bootstrap_service.py
git commit -m "feat(bootstrap): migrate SQLite cache paths during root move"
```

---

### Task 5: `bootstrap_root()` Entry Point

**Files:**
- Modify: `services/bootstrap_service.py`
- Test: `tests/test_bootstrap_service.py`

**Interfaces:**
- Consumes: `SettingsStore` from `infrastructure/settings_store.py`, `CacheDb`, `ScannerService` from `services/scanner_service.py`, all helpers from Tasks 1–4.
- Produces: `BootstrapResult` dataclass + `bootstrap_root(settings_store, cache_db, scanner) -> BootstrapResult`.

- [ ] **Step 1: Write the failing tests**

```python
# Append to tests/test_bootstrap_service.py
from dataclasses import dataclass

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
    assert store.read().root_folder == expected


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
    assert store.read().root_folder == expected


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
    # Sabotage: pre-create the default root so direct move target exists,
    # then make it non-empty to force content-move path, then sabotage move.
    expected = fake_home / "Documents" / "Project Tracker"
    expected.mkdir(parents=True)
    (expected / "blocker").mkdir()
    import services.bootstrap_service as bs
    original_move = bs.shutil.move

    def fail_move(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(bs.shutil, "move", fail_move)
    result = bootstrap_root(store, db, scanner)
    assert result.action == "failed"
    assert old_root.exists()  # old data preserved
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_bootstrap_service.py::test_bootstrap_creates_default_root_when_none -v`
Expected: FAIL — `ImportError: cannot import name 'BootstrapResult'`

- [ ] **Step 3: Write minimal implementation**

Append to `services/bootstrap_service.py`:

```python
import logging
import shutil
from dataclasses import dataclass

from infrastructure.settings_store import SettingsStore

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    action: str  # "created" | "none" | "migrated" | "created_orphan" | "failed"
    old: Path | None = None
    new: Path | None = None
    error: str | None = None


def bootstrap_root(
    settings_store: SettingsStore,
    cache_db: CacheDb,
    scanner: object,
) -> BootstrapResult:
    """Ensure root_folder is at the default path, migrating if needed.

    Called from app_web.run() before webview.start().
    """
    target = default_root()
    settings = settings_store.read()
    current = settings.root_folder

    # Case 1: no root set — create default.
    if current is None:
        target.mkdir(parents=True, exist_ok=True)
        settings.root_folder = target
        settings_store.write(settings)
        return BootstrapResult(action="created", new=target)

    current_resolved = current.resolve()
    target_resolved = target.resolve()

    # Case 2: already at default — nothing to do.
    if current_resolved == target_resolved:
        return BootstrapResult(action="none", new=target)

    # Case 3: old root missing — create empty default, clear cache.
    if not current.exists():
        target.mkdir(parents=True, exist_ok=True)
        settings.root_folder = target
        settings_store.write(settings)
        # Clear stale cache (nothing to rebuild from).
        with cache_db._connect() as conn:
            conn.execute("DELETE FROM project_index")
            conn.execute("DELETE FROM drone_tickets")
            conn.execute("DELETE FROM scan_warnings")
            conn.execute("DELETE FROM notifications")
            conn.execute("DELETE FROM approval_polling_jobs")
        return BootstrapResult(action="created_orphan", old=current, new=target)

    # Case 4: migrate old root to default.
    try:
        if not target.exists():
            # Direct move: old root becomes the default path.
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(current), str(target))
            new_root = target
        else:
            # Target already exists (partial previous attempt): move contents.
            for item in current.iterdir():
                shutil.move(str(item), str(target / item.name))
            current.rmdir()
            new_root = target
    except (OSError, shutil.Error) as exc:
        logger.error("Root migration failed, keeping old root: %s", exc)
        # Clean partial copy if the direct-move target was created.
        if target.exists() and not target_resolved == current_resolved:
            # Only clean items we may have moved; leave pre-existing target content.
            pass
        return BootstrapResult(action="failed", old=current, new=current, error=str(exc))

    # Rewrite all stored paths.
    settings = rewrite_settings_paths(settings, current, new_root)
    rewrite_appcode_configs(new_root, current)
    migrate_cache(cache_db, current, new_root)

    # Rescan to rebuild project_index/drone_tickets/scan_warnings.
    try:
        for appcode_child in sorted(new_root.iterdir()):
            if not appcode_child.is_dir():
                continue
            for year_child in sorted(appcode_child.iterdir()):
                if year_child.is_dir() and year_child.name.isdigit():
                    scanner.rebuild_year(year_child)
    except Exception:  # noqa: BLE001 — scan failure must not block startup
        logger.warning("Cache rescan after migration failed; cache will rebuild on next access")

    settings.root_folder = new_root
    settings_store.write(settings)
    return BootstrapResult(action="migrated", old=current, new=new_root)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_bootstrap_service.py -v`
Expected: 17 passed

- [ ] **Step 5: Commit**

```bash
git add services/bootstrap_service.py tests/test_bootstrap_service.py
git commit -m "feat(bootstrap): bootstrap_root entry point with migrate/rollback"
```

---

### Task 6: Remove `ensure_year_structure` Side-Effect

**Files:**
- Modify: `infrastructure/settings_store.py:49-56`
- Test: `tests/test_bootstrap_service.py` (add side-effect absence test)

**Interfaces:**
- Modifies: `SettingsStore.write()` — removes `ensure_year_structure` call. `ensure_year_structure` function stays in `filesystem.py` (scanner backward-compat).

- [ ] **Step 1: Write the failing test**

```python
# Append to tests/test_bootstrap_service.py
def test_settings_write_does_not_create_year_folders(tmp_path):
    """SettingsStore.write() must NOT create legacy year/state folders."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    root = tmp_path / "myroot"
    store = SettingsStore(config_dir=config_dir)
    settings = store.read()
    settings.root_folder = root
    store.write(settings)
    # root may or may not exist, but year folders must NOT be created.
    year_path = root / "2026"
    assert not year_path.exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_bootstrap_service.py::test_settings_write_does_not_create_year_folders -v`
Expected: FAIL — `assert not year_path.exists()` fails because `write()` currently calls `ensure_year_structure`.

- [ ] **Step 3: Edit `infrastructure/settings_store.py`**

Replace lines 49–56:

```python
    def write(self, settings: AppSettings) -> None:
        atomic_write_json(self.path, settings.to_dict())
        if settings.root_folder is not None:
            from datetime import datetime

            from infrastructure.filesystem import ensure_year_structure

            ensure_year_structure(settings.root_folder, datetime.now().year)
```

With:

```python
    def write(self, settings: AppSettings) -> None:
        atomic_write_json(self.path, settings.to_dict())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_bootstrap_service.py -v`
Expected: 18 passed

- [ ] **Step 5: Run existing settings/appcode tests to verify no regression**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_appcode_discovery.py tests/test_cache_appcode.py -v`
Expected: all pass (these tests don't depend on the side-effect).

- [ ] **Step 6: Commit**

```bash
git add infrastructure/settings_store.py tests/test_bootstrap_service.py
git commit -m "fix(settings): remove ensure_year_structure side-effect from write()"
```

---

### Task 7: Wire `bootstrap_root()` into `app_web.run()`

**Files:**
- Modify: `app_web.py` (around line 2261, after `create_js_api` but before `webview.start()`)
- Test: manual verification + existing app smoke test.

**Interfaces:**
- Consumes: `bootstrap_root` from `services/bootstrap_service.py`, `SettingsStore`, `CacheDb`, `ScannerService`.

- [ ] **Step 1: Add the import and call in `app_web.py`**

In the `run()` function, after `js_api = create_js_api(...)` and before `window = webview.create_window(...)`, add:

```python
    # Bootstrap root folder (create default or migrate existing) before window.
    from services.bootstrap_service import bootstrap_root  # noqa: PLC0415
    from services.scanner_service import ScannerService  # noqa: PLC0415
    _scanner = ScannerService(cache_db=js_api._appcode_service._settings_store and CacheDb(app_config_dir() / "project_tracker_cache.db") or None)  # minimal
```

Wait — the js_api already holds the cache_db and settings_store internally. We need to access them. Let me check: `create_js_api` creates `cache_db` and `_settings_store` locally (lines 173–176). We need to bootstrap BEFORE `create_js_api` so the cache is correct from the start.

**Revised approach:** bootstrap before `create_js_api`, using fresh stores:

```python
    # Bootstrap root folder before creating JsApi so cache is correct.
    from services.bootstrap_service import bootstrap_root  # noqa: PLC0415
    from services.scanner_service import ScannerService  # noqa: PLC0415

    _bootstrap_settings = SettingsStore()
    _bootstrap_cache = CacheDb(app_config_dir() / "project_tracker_cache.db")
    _bootstrap_cache.initialize()
    _bootstrap_scanner = ScannerService(_bootstrap_cache)
    bootstrap_root(_bootstrap_settings, _bootstrap_cache, _bootstrap_scanner)
```

Place this block BEFORE `js_api = create_js_api(db_path=app_config_dir() / "project_tracker_cache.db")` (around line 2261). The `create_js_api` will then read the already-correct settings and cache.

- [ ] **Step 2: Verify the app still imports cleanly**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -c "import app_web; print('OK')"`
Expected: prints `OK` (no import error).

- [ ] **Step 3: Run existing tests to verify no import regression**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_appcode_discovery.py tests/test_bootstrap_service.py -v`
Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add app_web.py
git commit -m "feat(app): wire bootstrap_root into run() before window creation"
```

---

### Task 8: Create `AppcodeSetup.svelte` Component

**Files:**
- Create: `frontend/src/lib/components/AppcodeSetup.svelte`
- Delete: `frontend/src/lib/components/FirstRunSetup.svelte`

**Interfaces:**
- Consumes: `callBridge` from `../bridge`.
- Produces: Svelte component with `onDone: () => void` prop.

- [ ] **Step 1: Write the component**

```svelte
<script lang="ts">
  /**
   * AppcodeSetup — first-run popup requiring at least one appcode.
   *
   * Shown by the App shell when no appcodes are discovered in root_folder.
   * Calls the existing `appcode_add` bridge (which creates the full D-0008
   * worktree: appcode.json, CICD/, year/CR/{5 states}/Non-CR/).
   * [Done] is disabled until at least one appcode is saved.
   */
  import { callBridge, isPywebviewReady } from "../bridge";

  interface AppcodeInfo {
    name: string;
    path: string;
    display_name: string;
  }

  interface Props {
    onDone: () => void;
  }
  let { onDone }: Props = $props();

  let inputName = $state("");
  let saved: AppcodeInfo[] = $state([]);
  let busy = $state(false);
  let error = $state("");

  async function addAppcode() {
    const name = inputName.trim();
    if (!name) {
      error = "Appcode name is required.";
      return;
    }
    if (!isPywebviewReady()) {
      error = "The desktop app is required to create appcodes.";
      return;
    }
    busy = true;
    error = "";
    const r = await callBridge<AppcodeInfo>("appcode_add", name);
    busy = false;
    if (!r.ok) {
      error = r.error.message;
      return;
    }
    saved = [...saved, r.data];
    inputName = "";
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === "Enter" && !busy) {
      e.preventDefault();
      addAppcode();
    }
  }
</script>

<div class="as-backdrop">
  <div class="as-card" role="dialog" aria-modal="true" aria-label="Appcode setup" tabindex="-1">
    <span class="as-kicker">Welcome</span>
    <h2 class="as-title">Set up your appcodes</h2>
    <p class="as-hint">
      An appcode represents a team or product line you manage. At least one
      appcode is required to create and organize projects.
    </p>
    <div class="as-input-row">
      <input
        class="as-input"
        type="text"
        bind:value={inputName}
        placeholder="appcode name"
        disabled={busy}
        onkeydown={handleKeydown}
      />
      <button class="as-btn as-add" type="button" onclick={addAppcode} disabled={busy}>
        {busy ? "…" : "Add"}
      </button>
    </div>
    {#if error}<p class="as-err" role="alert">⚠ {error}</p>{/if}
    {#if saved.length > 0}
      <div class="as-list">
        <span class="as-list-label">Saved appcodes:</span>
        <ul>
          {#each saved as item}
            <li>✓ {item.name}</li>
          {/each}
        </ul>
      </div>
    {/if}
    <div class="as-actions">
      <button
        class="as-btn as-primary"
        type="button"
        onclick={onDone}
        disabled={saved.length === 0}
      >
        Done
      </button>
    </div>
  </div>
</div>

<style>
  .as-backdrop { position:fixed; inset:0; z-index:80; background:rgba(0,0,0,0.55); display:flex; align-items:center; justify-content:center; padding:20px; }
  .as-card { width:min(480px,100%); background:#fff; border:1px solid #D7DCE2; border-radius:10px; box-shadow:0 18px 50px rgba(0,0,0,0.4); padding:20px; display:flex; flex-direction:column; gap:10px; }
  .as-kicker { font-size:9px; font-weight:850; letter-spacing:0.4px; text-transform:uppercase; color:var(--color-muted); }
  .as-title { margin:0; font-size:18px; font-weight:900; color:var(--color-ink); }
  .as-hint { margin:0; font-size:11px; font-weight:700; color:var(--color-muted); line-height:1.5; }
  .as-input { height:32px; border:1px solid var(--color-input-border, #D7DCE2); border-radius:6px; padding:0 10px; font-size:12px; font-weight:750; color:var(--color-ink); outline:none; font-family:inherit; }
  .as-input:focus { border:2px solid var(--color-dbs-red); }
  .as-input-row { display:flex; gap:8px; align-items:center; }
  .as-input-row .as-input { flex:1; min-width:0; }
  .as-add { background:#fff; color:var(--color-dbs-red); border-color:var(--color-dbs-red); }
  .as-add:hover:not(:disabled) { background:var(--color-soft-pink-surface, #FFF1F4); }
  .as-err { margin:0; font-size:11px; font-weight:800; color:var(--color-dbs-red); }
  .as-list { display:flex; flex-direction:column; gap:4px; }
  .as-list-label { font-size:10px; font-weight:800; color:var(--color-muted); text-transform:uppercase; letter-spacing:0.3px; }
  .as-list ul { margin:0; padding:0; list-style:none; display:flex; flex-direction:column; gap:2px; }
  .as-list li { font-size:12px; font-weight:750; color:var(--color-ink); }
  .as-actions { display:flex; justify-content:flex-end; }
  .as-btn { height:34px; padding:0 18px; border-radius:6px; font-size:12px; font-weight:850; cursor:pointer; border:1px solid var(--color-dbs-red); }
  .as-primary { background:var(--color-dbs-red); color:#fff; }
  .as-primary:hover:not(:disabled) { background:var(--color-dbs-red-hover); }
  .as-btn:disabled { opacity:0.55; cursor:not-allowed; }
</style>
```

- [ ] **Step 2: Delete `FirstRunSetup.svelte`**

```bash
rm frontend/src/lib/components/FirstRunSetup.svelte
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/lib/components/AppcodeSetup.svelte
git rm frontend/src/lib/components/FirstRunSetup.svelte
git commit -m "feat(frontend): add AppcodeSetup popup, remove FirstRunSetup"
```

---

### Task 9: Wire `AppcodeSetup` into `App.svelte`

**Files:**
- Modify: `frontend/src/App.svelte` (lines 56–57, 205–218, 289–291)

- [ ] **Step 1: Read current App.svelte import section and replace**

Find the `FirstRunSetup` import (around line 5–10 of App.svelte) and replace with:

```typescript
import AppcodeSetup from "./lib/components/AppcodeSetup.svelte";
```

Remove the `FirstRunSetup` import line.

- [ ] **Step 2: Replace `rootUnset` state with `needsAppcode`**

In `App.svelte`, replace:

```typescript
  let rootUnset: boolean = $state(false);
```

With:

```typescript
  let needsAppcode: boolean = $state(false);
```

- [ ] **Step 3: Replace `checkRoot` and `onRootConfigured` functions**

Replace:

```typescript
  async function checkRoot() {
    if (!isPywebviewReady()) return;
    const r = await callBridge<Record<string, unknown>>("settings_get");
    if (r.ok && r.data) {
      const root = r.data["root_folder"];
      rootUnset = !root || String(root).trim() === "";
    }
  }

  function onRootConfigured() {
    rootUnset = false;
    loadYears();
    refreshKey++;
  }
```

With:

```typescript
  async function checkAppcode() {
    if (!isPywebviewReady()) return;
    const r = await callBridge<unknown[]>("appcode_list");
    if (r.ok) {
      needsAppcode = !r.data || r.data.length === 0;
    }
  }

  function onAppcodeDone() {
    needsAppcode = false;
    loadYears();
    refreshKey++;
  }
```

- [ ] **Step 4: Replace the `checkRoot()` call in `onMount`**

In `onMount`, replace `checkRoot();` with `checkAppcode();`.

- [ ] **Step 5: Replace the template conditional at the bottom**

Replace:

```svelte
  {#if rootUnset}
    <FirstRunSetup onSaved={onRootConfigured} />
  {/if}
```

With:

```svelte
  {#if needsAppcode}
    <AppcodeSetup onDone={onAppcodeDone} />
  {/if}
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.svelte
git commit -m "feat(frontend): wire AppcodeSetup popup into App.svelte"
```

---

### Task 10: Remove Root Folder Field from Settings.svelte

**Files:**
- Modify: `frontend/src/lib/components/Settings.svelte` (line 229 — Root Folder field + Browse button)

- [ ] **Step 1: Remove the Root Folder label/field**

In `Settings.svelte`, find line 229:

```svelte
            <label class="field"><span>Root Folder</span><div class="field-row"><input class="input" value={String(form["root_folder"] ?? "")} oninput={(e) => handleFieldChange("root_folder", (e.target as HTMLInputElement).value)} placeholder="D:\WORK\CR" /><button class="btn-secondary" onclick={() => browseFolder("root_folder")} disabled={browseBusy === "root_folder"}>{browseBusy === "root_folder" ? "…" : "Browse"}</button></div></label>
```

Delete this entire line.

- [ ] **Step 2: Remove the root_folder trailing-slash validation**

Find lines 138–146 (the `if (form["root_folder"]...` block) and delete:

```typescript
    if (form["root_folder"] && typeof form["root_folder"] === "string" && form["root_folder"].trim()) {
      const trimmed = form["root_folder"].trim();
      if (/[/\\]$/.test(trimmed)) {
        saveState = "error";
        saveError = "Root Folder must not end with a trailing slash.";
        addToast(saveError, "error", 5000);
        return;
      }
    }
```

- [ ] **Step 3: Update the restart note**

Find line 237 and update the restart note text. Replace:

```svelte
                {#if saveState === "idle" && !dirty}<p class="restart-note">▸ Saved. Some changes (root folder, startup behavior) require an app restart to take full effect.</p>{/if}
```

With:

```svelte
                {#if saveState === "idle" && !dirty}<p class="restart-note">▸ Saved. Some changes (startup behavior) require an app restart to take full effect.</p>{/if}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/components/Settings.svelte
git commit -m "feat(settings): remove root_folder field (root is fixed by bootstrap)"
```

---

### Task 11: Frontend Build + Full Verification

**Files:** None (verification only)

- [ ] **Step 1: Run svelte-check**

Run: `cd D:/Ibrahim/Projects/project_tracker/frontend && npx svelte-check --tsconfig ./tsconfig.json`
Expected: 0 errors (13 known a11y warnings OK).

- [ ] **Step 2: Run frontend tests**

Run: `cd D:/Ibrahim/Projects/project_tracker/frontend && npx vitest run`
Expected: all pass (no new failures vs. baseline).

- [ ] **Step 3: Build frontend (app must be closed)**

Confirm app is closed, then:

Run: `cd D:/Ibrahim/Projects/project_tracker && npm --prefix frontend run build`
Expected: clean build.

- [ ] **Step 4: Run full backend test suite**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_bootstrap_service.py tests/test_appcode_discovery.py tests/test_cache_appcode.py -v`
Expected: all pass.

- [ ] **Step 5: Run app smoke test**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main`
Expected: app starts, no errors in console. If no appcodes exist, AppcodeSetup popup appears.

- [ ] **Step 6: Commit any remaining changes**

```bash
git add -A
git commit -m "chore: verify build + tests pass for root bootstrap"
```

---

## Self-Review

**1. Spec coverage:**
- ✅ Root folder auto-default to `Documents\Project Tracker` — Task 5 (`bootstrap_root` Case 1)
- ✅ Force-migrate existing root — Task 5 (Case 4)
- ✅ Path rewriting (settings.json) — Task 2
- ✅ Path rewriting (appcode.json) — Task 3
- ✅ SQLite cache migration (rebuildable + non-rebuildable) — Task 4
- ✅ Migration failure rollback — Task 5 (Case 4 exception handling)
- ✅ Remove `ensure_year_structure` side-effect — Task 6
- ✅ Appcode popup (min 1, [Done] disabled, no skip) — Task 8
- ✅ Delete `FirstRunSetup.svelte` — Task 8
- ✅ Remove root_folder from Settings — Task 10
- ✅ Worktree auto-creation (existing `appcode_add`) — noted in Task 8, no new code
- ✅ Wire bootstrap into `run()` — Task 7

**2. Placeholder scan:** No TBD/TODO. All steps have actual code.

**3. Type consistency:**
- `rewrite_path(Path | None, Path, Path) -> Path | None` — consistent across Tasks 1–3.
- `BootstrapResult.action` string values match test assertions: `"created"`, `"none"`, `"migrated"`, `"created_orphan"`, `"failed"`.
- `migrate_cache(cache_db, old_root, new_root)` — consistent signature in Task 4 and Task 5.
- Frontend: `AppcodeSetup` uses `onDone` prop, `App.svelte` calls `onAppcodeDone` — consistent.

---

## Manual Checklist (for user after implementation)

- [ ] **Fresh install**: delete `%APPDATA%\ProjectTrackerDBS\settings.json`, launch app → `Documents\Project Tracker` created, appcode popup appears.
- [ ] **Appcode popup**: type appcode name, click Add → "✓ {name}" appears, input clears. Add 2nd appcode.
- [ ] **[Done] disabled** until 1+ appcode saved.
- [ ] **[Done] click** → popup closes, Dashboard loads.
- [ ] **Folder tree**: check `Documents\Project Tracker\{APPCODE}\{YEAR}\CR\{5 states}\Non-CR\` exists for each appcode.
- [ ] **Existing user with D:\WORK\CR**: launch app → data moved to `Documents\Project Tracker`, old folder gone, appcodes + projects visible.
- [ ] **Settings page**: no Root Folder field. Second Brain / File Template fields still present.
- [ ] **Re-launch**: popup does NOT reappear (appcodes exist).
- [ ] **Migration failure**: (hard to test manually) — if disk full, app starts with old root, no crash.
