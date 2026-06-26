# Architecture — Project Tracker

## Layer Structure

```
frontend/          Svelte UI (UI state only)
  → pywebview      JsApi bridge
    → services/    Use case coordinators
      → core/      Pure domain logic (no UI, no I/O)
      → infrastructure/  FS, JSON, SQLite, settings, OS integrations
```

## Dependency Rules

```
frontend  → bridge only (never import services/core directly)
bridge    → services
services  → core + infrastructure
infra     → core when needed
core      → nothing (pure domain, no imports from other layers)
```

## Python ↔ Frontend Bridge

- Frontend communicates with Python through typed pywebview bridge only
- Bridge returns predictable response objects: `{ success, data, error }`
- Business/domain logic stays in Python services, never in Svelte components

### Frontend Owns (UI State)

- Active page/menu
- Selected row/project/link/note
- Search/filter form state
- Modal open/close
- Loading and error display states
- Draft form values

### Python Owns (Domain State)

- Project state machine + folder transitions
- Metadata reads/writes
- Filesystem scanner
- SQLite cache rebuild
- Watchdog file events
- Outlook/Teams automation
- APScheduler jobs
- Notification persistence

## Persistence Model

| What                 | Where               | Rule                                             |
| -------------------- | ------------------- | ------------------------------------------------ |
| Project existence    | Filesystem          | Folder exists = project exists                   |
| Project year         | Year folder         | Parent folder name                               |
| Project folder state | State folder        | Parent state folder determines state             |
| Project metadata     | `project_data.json` | Metadata only, never `project_state`             |
| Cache/index          | SQLite              | Rebuildable — if deleted, rebuild from FS + JSON |
| Notes/links          | Local files         | Per-project files                                |

- Atomic JSON writes via metadata store mechanism
- Hard delete forbidden → `send2trash` on Windows
- Datetimes: ISO 8601, timezone-aware, local OS timezone

## Legacy Code

- PyQt6 files: reference only, do not develop
- Old `frontend/*.html`: reference only unless part of new Svelte frontend
- Use legacy files to understand user flows, screen components, interactions
- Do not delete legacy files without user approval
- A screen is NOT migrated until connected to real data + verified + tracked in \_docs/PROGRESS.md
