# Windows Setup — Project Tracker DBS

This project was developed on Linux and migrated to Windows, which is now the
primary development **and** target machine. This guide is the first-time
bootstrap. After this, follow `CLAUDE.md` for day-to-day rules.

> Source of truth: `PRD.md` (v3.1). If anything here conflicts with `PRD.md`,
> `PRD.md` wins — report the conflict before coding.

---

## 1. Prerequisites

Install these once (any recent versions unless pinned):

- **Python 3.12+** — install from python.org and tick "Add python.exe to PATH".
  Verify: `py -3.12 --version`
- **Node.js 20+ LTS** (includes npm) — from nodejs.org.
  Verify: `node --version` and `npm --version`
- **Git** — from git-scm.com. Verify: `git --version`
- **Microsoft Edge WebView2 Runtime** — required by pywebview for rendering.
  Most Windows 11 machines already have it; otherwise install the Evergreen
  Runtime from Microsoft. Verify the app window renders the UI (step 4).
- **Outlook desktop** and **Microsoft Teams desktop** — only needed for the
  live Outlook COM / Teams automation features.

All commands below assume **PowerShell**, run from the repository root
(the folder containing this file).

---

## 2. One-time bootstrap

```powershell
# Create the virtual environment (Python 3.12)
py -3.12 -m venv .venv

# Install Python dependencies (includes pywin32, pyinstaller, etc.)
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Install + build the Svelte/Vite/Tailwind frontend
npm --prefix frontend install
npm --prefix frontend run build
```

`npm run build` writes the production UI into `web/static/`. A prebuilt
`web/static/` is already included in this copy, so the app runs even before you
rebuild — but rebuild whenever frontend source under `frontend/src/` changes.

> If `pip install` cannot reach the internet, this machine is offline and you
> need the offline package strategy (not bundled in this zip). Re-run on a
> connected network, or ask for an air-gapped bundle.

---

## 3. Run the tests (verify the backend works)

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q
```

All tests should pass. These cover the core domain, state machine, JSON stores,
filesystem scanning, SQLite cache rebuild, and bridge contracts.

---

## 4. Run the desktop app

```powershell
.\.venv\Scripts\python.exe -m project_tracker.main
```

This opens the pywebview desktop window serving the built frontend from
`web/static/`. The window title is "Project Tracker DBS".

There is **no** root `main.py`; the entry point is the
`project_tracker.main` module (`-m project_tracker.main`).

---

## 5. Package a Windows release (optional)

PyInstaller runs on this Windows machine (it was forbidden on the Linux dev box).

```powershell
.\.venv\Scripts\python.exe scripts\package.py
```

Requirements before packaging:

- `web/static/` must be built (step 2).
- `assets/` must be present.
- The Windows manual RC test gate should pass first — see
  `docs/windows-manual-test-checklist.md` and
  `docs/release-candidate-manual-test-plan.md`.

The build uses `project_tracker_dbs.spec` and produces `ProjectTrackerDBS`.

---

## 6. Windows-only features now live

These were stubbed/skipped during Linux development and now run for real:

- **Outlook COM** (via pywin32 / win32com) — COM calls run on a background
  thread that calls `pythoncom.CoInitialize()` / `CoUninitialize()`.
  `pywebview.start()` stays on the main thread (see Threading Rule in CLAUDE.md).
- **Teams automation** (pyautogui where required).
- **Recycle Bin delete** via `send2trash` (hard delete is forbidden).
- **Open file/folder** via `os.startfile`.

Windows-only imports remain lazily guarded with `sys.platform == "win32"` —
keep those guards; do not strip them.

---

## 7. Data & paths

- `project_data.json` (repo root) holds project **metadata only**. It is the
  starter dataset included with this copy.
- Canonical source of truth is the **filesystem + JSON**, not SQLite. SQLite is
  a rebuildable local cache/index; deleting it must let the app rebuild from
  filesystem + JSON.
- Keep Windows paths in settings JSON as Windows paths (backslashes). Do not
  normalize them to Linux form.
- Datetimes are ISO 8601, timezone-aware, local OS timezone.

---

## 8. Optional tooling (safe to ignore)

- **RTK** (Rust Token Killer): a Linux token-optimization CLI. Not required on
  Windows. If absent, run commands without the `rtk` prefix.
- **graphify**: optional knowledge graph for token reduction. Not shipped. If
  the `graphify` CLI is installed, run `graphify update .` to build the graph
  under `graphify-out/`; otherwise read source directly.

---

## 9. First Claude Code session on Windows

When you open this project in Claude Code on Windows, the safe first steps are:

1. Read `PRD.md`, `CLAUDE.md`, `PROJECT_STATUS.md`.
2. Run the bootstrap (section 2) if `.venv/` does not exist.
3. Run the tests (section 3) to confirm a green baseline.
4. Launch the app (section 4) to confirm the UI renders.
5. Report any contradictions before coding, and work phase by phase.
