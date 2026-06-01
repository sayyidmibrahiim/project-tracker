# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Always prefix shell commands with `rtk`, including each command in `&&` chains.

Claude Code shells do not inherit the active venv. Use full venv path:

```bash
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/ -v
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_phase_b_stores.py -v
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/ -q
```

Legacy PyQt6 preview (deprecated, jangan dipakai untuk UI baru):

```bash
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python main.py
```

Package for Windows transfer from repository root:

```bash
rtk zip -r project_tracker_dbs_v$(date +%Y%m%d).zip . --exclude ".venv/*" "__pycache__/*" "*.pyc" ".git/*"
```

On Windows target:

```cmd
pip install -r requirements.txt
python main.py
```

No build/lint command is configured in `pyproject.toml`. Do not run PyInstaller on Linux.

## Environment Boundaries

| Component                    | Linux dev          | Windows target   |
| ---------------------------- | ------------------ | ---------------- |
| Core logic, filesystem, JSON | Unit tests allowed | Full app         |
| pywebview + HTML/Tailwind    | Preview allowed    | Full app         |
| PyQt6 UI shell (deprecated)  | Reference only     | DEPRECATED       |
| Outlook COM, Teams/pyautogui | Stub/skip only     | Real integration |
| `send2trash`, `os.startfile` | Stub/skip only     | Real integration |
| PyInstaller                  | Forbidden          | Allowed          |

Windows-only imports must be lazy and guarded with `sys.platform == "win32"`. Outlook, Teams, delete, and file-open services must instantiate without crashing on Linux.

Do not add dependencies without user confirmation. Use `pathlib.Path`; never string path concatenation. Keep Windows-formatted paths in settings JSON as Windows paths.

## UI Tech Stack (Updated Juni 2026)

UI layer dimigrasikan dari PyQt6 ke **pywebview + HTML/Tailwind CDN**.
`project_tracker/core/`, `infrastructure/`, `services/` tidak berubah strukturnya.

### Threading Rule — WAJIB

`pywebview.start()` harus di main thread. Semua COM calls harus di background thread:

```python
import pythoncom, threading

def _com_task():
    pythoncom.CoInitialize()
    try:
        pass  # outlook/teams automation di sini
    finally:
        pythoncom.CoUninitialize()

threading.Thread(target=_com_task).start()
```

### JS → Python Bridge Pattern

```python
class AppAPI:
    def get_projects(self): ...  # callable dari JS: pywebview.api.get_projects()

window = webview.create_window('App', 'frontend/index.html', js_api=AppAPI())
webview.start()
```

### Referensi Visual

Ketika membangun HTML screen baru di frontend/, gunakan redesign_ui/\*.py sebagai referensi visual dan userflow. Ekstrak layout, warna, dan interaksinya — bukan kodenya.

### File yang DIPERTAHANKAN (jangan diubah):

- `project_tracker/core/`
- `project_tracker/infrastructure/`
- `project_tracker/services/` — terapkan threading rule di semua COM calls

### File yang DIGANTIKAN (jangan generate PyQt6 code baru):

- `project_tracker/ui/` → `frontend/` (HTML files)
- `project_tracker/themes/` → Tailwind classes
- `project_tracker/app.py` → pywebview entry point baru

## Product Source of Truth

`PRD.md` is product requirements source of truth. `PROJECT_STATUS.md` records verification status and completed slices. Linux-verifiable work is marked complete; Windows manual verification remains required for Outlook COM, Teams automation, `os.startfile`, `send2trash`, visual/font rendering, and packaging.

Key constraints:

- Local-first, single-user desktop app; no cloud backend, external database, SQLite, or PDF export in MVP. UI layer menggunakan pywebview + HTML/Tailwind CDN (system WebView2, bukan bundled browser). Tidak ada server eksternal.
- Filesystem is source of truth for project existence, year, and folder state.
- `project_data.json` stores metadata only; `project_state` must never be stored in JSON.
- Year comes only from year folder name.
- Hard delete is forbidden; Windows delete must use Recycle Bin via `send2trash`.
- Datetimes must be ISO 8601 timezone-aware using local OS timezone.
- History user comes from `settings.display_name` if set, otherwise Windows login; never hardcode.

## Architecture

Python 3.12+ modular monolith: pywebview + HTML/Tailwind UI, local filesystem, JSON persistence.

```text
ui/ -> services/ -> core/
services/ -> infrastructure/ + core/
core/ imports no ui, services, or infrastructure
```

Runtime flow: `main.py` calls `project_tracker.app.run()`. `app.py` creates `QApplication`, loads `SettingsStore`, ensures year folders when `root_folder` exists, applies `ThemeManager`, then shows `MainWindow`. `ui/main_window.py` owns sidebar, `QStackedWidget` pages, notification panel, theme toggle, onboarding, and `AutoTransitionService` startup.

Core layer: `core/enums.py` defines state/theme/language/email enums; `core/models.py` defines metadata/settings/automation/notification dataclasses and JSON serialization; `core/rules.py` and `core/state_machine.py` enforce transition guards.

Infrastructure layer: `metadata_store.py` atomically reads/writes `project_data.json` and strips `project_state`; `settings_store.py` writes config under `%APPDATA%\ProjectTrackerDBS` on Windows and `~/ProjectTrackerDBS` elsewhere; `filesystem.py` owns year/state folder helpers; `link_bank_store.py` stores reusable links; `watchdog_service.py` monitors filesystem changes.

Services layer: `project_service.py` moves folders between state directories and updates metadata/history; `scanner_service.py` ignores organizational folders and validates drone subfolders; `email_service.py`, `outlook_service.py`, `download_email_service.py`, and `teams_service.py` wrap Windows automation behind guards; `safe_delete_service.py` is the destructive-operation boundary; `theme_manager.py` applies centralized QSS themes.

UI layer: `ui/dashboard.py` lists real scanned projects and must not use dummy production data. `ui/project_detail_wireframe.py` / `ui/project_detail_splitpane.py` handle real detail loading, inline edits, subprojects, notes, and template-file copy flows. `ui/*_tab.py` files compose automation, email, Teams, download-email, notes, and link-bank pages; `ui/widgets/` contains reusable controls.

## Persistence Model

Project root contains year folders; each year contains state folders such as `UAT_PREPARE`, `PROD_READY`, `IMPLEMENTED`, and `POSTPONED`. Project state is derived from parent state folder, not metadata.

Each project folder may contain `project_data.json`. Missing metadata falls back to folder name. Corrupt or unknown schema metadata produces warnings and should not crash scans. Atomic JSON writes use `project_tracker.infrastructure.metadata_store.atomic_write_json()`.

Organizational folders such as docs, backup, scripts, logs, temp, and archive are not drone subprojects.

## Testing Notes

Automated PyQt6 tests must not open blocking modals or require manual clicks; monkeypatch dialogs/message boxes. Linux tests may verify platform-independent logic, JSON/filesystem behavior, and guarded PyQt6 UI shell behavior. Windows manual verification remains required for Outlook COM, Teams/pyautogui, `os.startfile`, `send2trash`, visual rendering, and packaging.
