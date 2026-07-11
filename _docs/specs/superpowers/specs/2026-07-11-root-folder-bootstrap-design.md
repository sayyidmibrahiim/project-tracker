# Root Folder Bootstrap & Appcode First-Run Setup

**Date:** 2026-07-11
**Status:** Design — pending user review
**Branch:** `general/root-folder-bootstrap`

## Problem

Current state:
1. `AppSettings.root_folder` defaults to `None`. First-run requires user to manually pick a folder via `FirstRunSetup.svelte`.
2. `SettingsStore.write()` has a side-effect calling `ensure_year_structure()` — creates legacy `{root}/{year}/{states}` tree (no appcode wrapper). This is inconsistent with the canonical D-0008 appcode tree and leaves junk folders.
3. No appcode auto-check. User can land on the app with root set but zero appcodes — no way to create projects until they manually add one.

## Goal

On first install of the `.exe`:
- Root folder auto-defaults to `C:\Users\<user>\Documents\Project Tracker\`.
- No folder picker prompt.
- App UI shows a small popup requiring at least one appcode.
- After adding appcode(s), full worktree (D-0008) is created automatically.
- Popup never reappears as long as appcodes exist.

For existing users whose `root_folder` is not at the default path:
- Force-migrate data (move) to the default path.
- Rewrite all absolute path references in settings, appcode configs, and SQLite cache.

## Non-Goals

- Appcode auto-creation without user input (user must enter appcode name(s)).
- Migration wizard UI with choices (migration is forced, no options).
- Multi-user / network share support.
- Path customization after migration. Root folder is always `Documents\Project Tracker`. The root_folder field in Settings is removed — no user override.

## Design

### Section 1: Bootstrap & Migration Engine (Backend)

#### New file: `services/bootstrap_service.py`

```
bootstrap_root(settings_store, cache_db, scanner) -> BootstrapResult:
    1. default_root = Path.home() / "Documents" / "Project Tracker"
    2. current = settings.root_folder
    3. IF current is None:
         - default_root.mkdir(parents=True, exist_ok=True)
         - settings.root_folder = default_root
         - settings_store.write(settings)
         - return BootstrapResult(action="created")
    4. IF current.resolve() == default_root.resolve():
         - return BootstrapResult(action="none")
    5. IF current != default_root:
         - IF not current.exists():
             - default_root.mkdir(parents=True, exist_ok=True)
             - settings.root_folder = default_root
             - settings_store.write(settings)
             - cache_db.clear_all()
             - return BootstrapResult(action="created_orphan")
         - MIGRATE:
           a. If default_root does not exist:
                - Move old root directly to default_root path:
                  shutil.move(str(current), str(default_root))
                - new_root = default_root
              Else (default_root already exists, e.g. partial previous attempt):
                - Move contents into default_root:
                  for item in current.iterdir():
                      shutil.move(str(item), str(default_root / item.name))
                  shutil.rmtree(current)
                - new_root = default_root
           b. _rewrite_settings_paths(settings, current, new_root)
           c. _rewrite_appcode_configs(new_root, current)
           d. _migrate_cache(cache_db, current, new_root)
           e. scanner.rebuild_all_years()
           f. settings.root_folder = new_root
           g. settings_store.write(settings)
         - return BootstrapResult(action="migrated", old=current, new=new_root)
```

#### Migration failure rollback

`shutil.move` cross-drive = copy + delete. If it fails mid-copy:
- Catch `OSError` / `shutil.Error`.
- Delete partial copy at `new_root` (`shutil.rmtree(new_root, ignore_errors=True)` if `new_root` was the direct-move target; for content-move, clean only the moved items).
- Keep `settings.root_folder` at old root.
- Log error.
- Return `BootstrapResult(action="failed", old=current, error=str(e))`.
- App starts normally with old root. User can free space and retry on next launch.

#### Path rewriting helper

```python
def _rewrite_path(path: Path | None, old_root: Path, new_root: Path) -> Path | None:
    if path is None:
        return None
    try:
        if path.is_relative_to(old_root):
            return new_root / path.relative_to(old_root)
    except ValueError:
        pass
    return path  # outside root, leave as-is
```

Applied to these settings.json fields (only if inside old root):
- `AppSettings.root_folder`
- `AppSettings.second_brain_folder`
- `AppSettings.file_template_folder`
- `EmailSettings.template_folder_path`
- `TeamsAutomation.attachment_paths[]` (per-entry)

#### Appcode config rewriting

For each `{appcode}/appcode.json` under new root:
- If `cicd_shared_path` is set and `is_relative_to(old_root)` → rewrite to new root.
- Otherwise leave unchanged.

#### SQLite cache migration

Two strategies by rebuildability:

**Non-rebuildable** (rewrite paths, preserve user state):
```sql
UPDATE notifications
SET project_path = REPLACE(project_path, :old_prefix, :new_prefix)
WHERE project_path LIKE :old_pattern;

UPDATE approval_polling_jobs
SET project_path = REPLACE(project_path, :old_prefix, :new_prefix)
WHERE project_path LIKE :old_pattern;
```

**Rebuildable** (delete + rescan):
```sql
DELETE FROM project_index;
DELETE FROM drone_tickets;
DELETE FROM scan_warnings;
```

Then `scanner.rebuild_all_years()` repopulates from filesystem scan.

All SQL runs in a single transaction. Rescan runs after commit.

#### Call site

`app_web.py` `run()`, before `webview.start()`:
```python
bootstrap_root(self._settings_store, self._cache_db, self._scanner)
```

Blocking — migration completes before window appears. Cross-drive move may take time (one-time). Acceptable.

### Section 2: Appcode Check & Popup Flow (Frontend)

#### Backend bridge methods

Reuse existing — no new bridge methods:
- `appcode_list` — check if any appcode exists (returns list).
- `appcode_add(name)` — create appcode + full worktree (already auto-creates `appcode.json`, `CICD/`, `{year}/CR/{5 states}/Non-CR/`).

#### Frontend — `App.svelte` changes

Remove existing `rootUnset` / `FirstRunSetup.svelte` logic. Replace with appcode check:

```typescript
let needsAppcode: boolean = $state(false);

async function checkAppcode() {
    const r = await callBridge<AppcodeInfo[]>("appcode_list");
    if (r.ok && r.data) {
        needsAppcode = r.data.length === 0;
    }
}
// called from onMount
```

#### New component: `AppcodeSetup.svelte`

Replaces `FirstRunSetup.svelte` (delete the old file).

Layout:
```
┌─────────────────────────────────────┐
│  Welcome to Project Tracker         │
│                                     │
│  An appcode represents a team or    │
│  product line you manage. At least  │
│  one appcode is required to create  │
│  and organize projects.             │
│                                     │
│  ┌─────────────────────┐  [ Add ]   │
│  │ appcode name         │           │
│  └─────────────────────┘            │
│                                     │
│  Saved appcodes:                    │
│  ✓ APPCODE_A                        │
│  ✓ WGID                             │
│                                     │
│              [ Done ]               │
└─────────────────────────────────────┘
```

Behavior:
- Input + [Add] → call `appcode_add(name)` → refresh list.
- List below shows `✓ {name}` per saved appcode.
- Input clears after add, ready for next appcode.
- [Done] **disabled** until list has 1+ entry.
- [Done] click → `needsAppcode = false` → popup closes permanently.
- No [Skip], no [X] close button — modal, cannot bypass.
- Error handling: duplicate name / invalid chars → error text below input, input stays focused, list unchanged.

#### Worktree auto-creation (existing behavior, no new code)

`appcode_add` already creates the full D-0008 worktree per appcode:
```
{APPCODE}\
  appcode.json
  CICD\
  {YEAR}\
    CR\
      UAT_PREPARE\
      PROD_READY\
      IMPLEMENTED\
      POSTPONED\
      CANCELED\
    Non-CR\
```

User adds 3 appcodes in popup → 3 full worktrees created. Year = `local_now().year`.

### Section 3: Edge Cases & Legacy Cleanup

#### Edge: old root missing

User set `root_folder` before, folder deleted manually. Bootstrap:
- `current != default_root` AND `not current.exists()`.
- Create empty `default_root`, update settings, clear cache.
- App starts with empty root → appcode popup appears.

#### Edge: move failure mid-copy

- `shutil.move` raises → catch, delete partial copy, keep old root, log error.
- App starts with old root. No force-close. User retries next launch.

#### Edge: default_root already has data (reinstall)

- `current == default_root` → `action="none"` → skip.
- Appcode check runs normally. If appcodes exist → popup skips. If none → popup appears.

#### Edge: appcode_add fails in popup

- Backend returns error (duplicate / invalid chars).
- Frontend shows error message below input (red).
- Input stays focused, list unchanged.
- [Done] stays disabled if list empty.

#### Legacy cleanup: remove `ensure_year_structure` side-effect

**File:** `infrastructure/settings_store.py`, `write()` method.

**Before:**
```python
def write(self, settings: AppSettings) -> None:
    ...
    tmp.replace(self.path)
    ensure_year_structure(settings.root_folder, datetime.now().year)
```

**After:**
```python
def write(self, settings: AppSettings) -> None:
    ...
    tmp.replace(self.path)
```

`ensure_year_structure` function stays in `filesystem.py` (scanner needs it for backward-compat legacy layout reads). Only the side-effect call is removed.

Reason: appcode creation (`add_appcode`) already calls `ensure_appcode_year_structure` itself. The side-effect in `write()` creates junk legacy folders at root level that don't match the D-0008 tree.

### Testing Strategy

| Test | Scope |
|---|---|
| `test_bootstrap_creates_default_root` | root_folder=None → default created, settings updated |
| `test_bootstrap_migrates_existing_root` | root at custom path → moved to Documents, paths rewritten |
| `test_bootstrap_migration_failure_rollback` | shutil.move raises → old root kept, partial cleaned |
| `test_bootstrap_orphan_old_root` | old root missing → default created, cache cleared |
| `test_bootstrap_default_already_exists` | root already at default → action="none" |
| `test_bootstrap_migrate_direct_when_default_empty` | default_root not exist → old root moved directly to default path (no nesting) |
| `test_bootstrap_migrate_contents_when_default_exists` | default_root exists → contents moved in, old root removed |
| `test_rewrite_path_inside_root` | path inside old_root → rewritten |
| `test_rewrite_path_outside_root` | path outside old_root → unchanged |
| `test_cache_sqlite_path_rewrite` | notifications/approval_polling_jobs paths rewritten |
| `test_cache_rebuild_after_migration` | project_index/drone_tickets rescanned correctly |
| `test_appcode_json_cicd_shared_path_rewritten` | appcode with shared_root mode → path rewritten |
| `test_settings_write_no_side_effect` | write() does NOT create year folders |

## Path Audit (Reference)

Stores with absolute paths that break after root move:

| Store | Location | Action |
|---|---|---|
| `AppSettings.root_folder` | settings.json | Rewrite (anchor) |
| `AppSettings.second_brain_folder` | settings.json | Rewrite if inside old root |
| `AppSettings.file_template_folder` | settings.json | Rewrite if inside old root |
| `EmailSettings.template_folder_path` | settings.json | Rewrite if inside old root |
| `TeamsAutomation.attachment_paths[]` | settings.json | Rewrite entries inside old root |
| `AppCodeConfig.cicd_shared_path` | appcode.json | Rewrite if inside old root |
| `project_index.path` | SQLite cache | Delete + rebuild |
| `drone_tickets.project_path` | SQLite cache | Delete + rebuild |
| `scan_warnings.project_path` | SQLite cache | Delete + rebuild |
| `notifications.project_path` | SQLite cache | SQL REPLACE (preserve dismissed state) |
| `approval_polling_jobs.project_path` | SQLite cache | SQL REPLACE (preserve polling status) |

Stores that are safe (relative/URL only, no action needed):
- `ProjectMetadata` all fields (`project_data.json`)
- `LinkBank` (`link_bank.json`)
- `EmailCategorySettings.attachment_template_file` (basename only)
- App logs (`%APPDATA%\...\logs\`, outside root)

## Files Changed

| File | Change |
|---|---|
| `services/bootstrap_service.py` | **New** — bootstrap_root, migration, path rewriting |
| `app_web.py` | Call bootstrap_root in run(); inject scanner dependency |
| `infrastructure/settings_store.py` | Remove `ensure_year_structure` side-effect from write() |
| `frontend/src/App.svelte` | Remove rootUnset/FirstRunSetup; add needsAppcode check |
| `frontend/src/lib/components/AppcodeSetup.svelte` | **New** — appcode popup |
| `frontend/src/lib/components/FirstRunSetup.svelte` | **Delete** — replaced by AppcodeSetup |
| `frontend/src/lib/components/Settings.svelte` | Remove root_folder field + Browse button (root is fixed) |
| `tests/test_bootstrap_service.py` | **New** — test suite |

## Decision Record

This design introduces:
- **D-0016** (pending): Root folder defaults to `Documents\Project Tracker`. Force-migrate on launch. Appcode popup required (min 1) before app is usable.
