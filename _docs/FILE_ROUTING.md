# File Routing — Project Tracker

## Ownership Map

| Path | Category | Treatment |
|------|----------|-----------|
| `.claude/settings.json` | Config | Commit; project-level Claude Code settings |
| `.claude/rules/*` | Config | Commit; Claude Code rules (memory, integration routing) |
| `.gitignore` | Config | Commit; source control ignores |
| `.graphifyignore` | Config | Commit; graphify scan ignores |
| `CLAUDE.md` | Config | Commit; workflow/tooling rules for Claude Code |
| `PRD.md` | Docs | Commit; product requirements source of truth |
| `CHANGELOG.md` | Docs | Commit; release notes |
| `pyproject.toml`, `requirements.txt` | Config | Commit; Python dependencies |
| `main.py`, `app_web.py`, `__init__.py` | Code | Commit; Python entry points |
| `core/`, `infrastructure/`, `services/` | Code | Commit; Python backend layers |
| `web/` | Code | Commit; Python bridge layer |
| `frontend/` | Code | Commit; Svelte+TS frontend source |
| `scripts/` | Code | Commit; packaging, guards, hooks |
| `project_tracker/` | Legacy/shadow | Gitignored; stale nested package (root `__init__.py` is real package) |
| `_docs/` | Docs | Commit; architecture, design, workflow, decisions, session notes |
| `_docs/specs/` | Docs | Commit; per-menu SPEC files before implementation |
| `_docs/_archive/` | Docs | Commit; history snapshots (append only, don't overwrite) |
| `_reference/` | Reference | Commit; HTML prototype files (visual AS-IS parity only) |
| `_specs/` | Docs | Commit; raw prompt specs |
| `graphify-out/` | Generated | Gitignore; rebuildable AST graph |
| `node_modules/`, `.venv/` | Deps | Gitignore; install artifacts |
| `web/static/` | Build | Gitignore; Vite build output |
| `__pycache__/`, `.pytest_cache/` | Cache | Gitignore; Python cache |
| `project_data.json` (root) | Runtime data | Gitignore; belongs in per-project folders, not root |
| `nul` | Windows artifact | Gitignore; Windows reserved device name |

## Rules

- **Non-code files** go in `_docs/` (or underscore-prefixed folder).
- **Generated/artifact files** go in `.gitignore`, never commit.
- **No file** outside `_docs/` should contain design decisions, workflow rules, or architecture notes — those belong in `_docs/`.
- **If touching X, read Y first:**

| Touching | Read |
|----------|------|
| `services/*` | `_docs/ARCHITECTURE.md` (layer rules, dependency flow) |
| `web/js_api.py` | `_docs/ARCHITECTURE.md` (bridge contract, response shape) |
| `frontend/src/lib/*` | `_docs/ARCHITECTURE.md`, `_docs/DESIGN_RULES.md` |
| Bridge layer (services ↔ frontend) | `_docs/ARCHITECTURE.md` (event queue, bridge pattern) |

## Root Clutter Status

| File | Decision | Status |
|------|----------|--------|
| `notes.md` | Empty/transient | Already deleted (gone from disk) |
| `project_data.json` | Runtime data → gitignore | Already in `.gitignore` |
| `nul` | Windows artifact → gitignore | Already in `.gitignore` |
| `project_tracker/web/` | Legacy/shadow → gitignore | Already in `.gitignore` for `project_tracker/`; only `__pycache__` remains |
