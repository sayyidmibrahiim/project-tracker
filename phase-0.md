# Phase 0 Implementation Readiness Audit

## Repo reality check

Current repo is partially migrated, not PRD v3.1-ready.

Evidence read/checked:

- `PRD.md` v3.1, including phases and ADRs.
- `CLAUDE.md`.
- Repository tree.
- `project_tracker/`.
- `frontend/`.
- `redesign_ui/`.
- `requirements.txt`.
- pywebview entrypoint wiring.
- static frontend files.
- SQLite/APScheduler/event queue markers.
- PyQt6 import markers.

Current structure:

```text
project_tracker_dbs/
├── PRD.md
├── CLAUDE.md
├── PRD_old.md
├── PROJECT_STATUS_old.md
├── requirements.txt
├── pyproject.toml
├── frontend/
│   ├── index.html
│   ├── dashboard.html
│   ├── project_detail.html
│   ├── second_brain.html
│   ├── report.html
│   ├── automations.html
│   ├── settings.html
│   └── assets/tailwind.min.js
├── project_tracker/
│   ├── app_web.py
│   ├── main.py
│   ├── core/
│   ├── infrastructure/
│   └── services/
└── redesign_ui/
    ├── _REFERENCE_ONLY.md
    ├── UI_FEATURE_DOCUMENTATION.md
    └── PyQt6 prototype files
```

Missing PRD target structure:

```text
web/
├── js_api.py
└── event_queue.py

frontend/
├── package.json
├── tsconfig.json
├── vite.config.ts
└── src/
```

No `PROJECT_STATUS.md` found. Only `PROJECT_STATUS_old.md`.

No `MIGRATION_PLAN.md` found.

## PRD compliance matrix

| Area                    | PRD v3.1 target                                                        | Current repo reality                                                                                     | Status                         |
| ----------------------- | ---------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | ------------------------------ |
| PRD source of truth     | `PRD.md` v3.1 locked                                                   | Present: `PRD.md` v3.1. Old PRD still present as `PRD_old.md`.                                           | Mostly aligned                 |
| CLAUDE alignment        | CLAUDE says PRD v3.1 authoritative                                     | `CLAUDE.md` matches stack/migration direction.                                                           | Aligned                        |
| Production frontend     | Svelte + TypeScript + Vite + Tailwind local build                      | Static `.html` files + `assets/tailwind.min.js`; no Svelte/Vite project.                                 | Non-compliant                  |
| Tailwind strategy       | Bundled through frontend build                                         | Local Tailwind browser script loaded by HTML. No build pipeline.                                         | Non-compliant                  |
| Vanilla JS state        | Not production state-management strategy                               | HTML pages use inline JS / static assumptions.                                                           | Non-compliant                  |
| pywebview shell         | Serve Vite build output via local server/serve-folder                  | `project_tracker/app_web.py` uses pywebview, but loads `frontend/dashboard.html` via file URI.           | Partially compliant / conflict |
| App entrypoint          | `app_web.py` root or configured pywebview app                          | Current entry is `project_tracker/main.py` -> `project_tracker.app_web.run()`.                           | pywebview, not PyQt            |
| Core domain             | Pure Python domain logic                                               | `project_tracker/core/` exists. Need deeper tests before compliance claim.                               | Partially present              |
| Infrastructure stores   | metadata/settings/link bank/cache db/filesystem                        | metadata/settings/link bank/filesystem exist. No `cache_db.py`.                                          | Partial                        |
| SQLite cache/index      | Rebuildable cache only                                                 | No SQLite code/files found; no `cache_db.py`; no references.                                             | Missing                        |
| APScheduler             | Required for background jobs                                           | `requirements.txt` missing apscheduler; no usage found.                                                  | Missing                        |
| Event queue             | `web/event_queue.py`, polling bridge                                   | No `web/` package and no event queue found.                                                              | Missing                        |
| JsApi bridge            | `web/js_api.py` typed standard response                                | Bridge class exists inside `project_tracker/app_web.py` as `AppAPI`; not target `web/js_api.py`.         | Partial / misplaced            |
| Bridge response shape   | `{ ok, data, warnings, error }`                                        | Some methods return raw lists/dicts; mixed shapes.                                                       | Non-compliant                  |
| PyQt6 production        | Reference only; never imported by production                           | No PyQt imports found in `project_tracker/`. PyQt files remain in `redesign_ui/`, marked reference-only. | Compliant                      |
| Static HTML legacy      | Reference only unless verified as new Svelte frontend                  | `frontend/*.html` still used by pywebview entrypoint.                                                    | Conflict                       |
| Notes model             | `notes.md` primary; JSON `notes` legacy/not used                       | `ProjectMetadata.notes` exists and app appends notes into metadata JSON.                                 | Conflict                       |
| `project_state` in JSON | Must never appear                                                      | `metadata_store.py` pops `project_state` before write.                                                   | Likely compliant               |
| Delete safety           | Recycle Bin via `send2trash`, no hard delete                           | `SafeDeleteService` uses `send2trash`. Need full scan before no-hard-delete claim.                       | Mostly aligned                 |
| Dependencies            | Approved baseline includes APScheduler; watchdog optional confirmation | `requirements.txt` includes `watchdog` but not APScheduler.                                              | Conflict                       |
| Packaging output        | Vite output `web/static/`                                              | No `web/static/`; no frontend build.                                                                     | Missing                        |

## Contradictions

### 1. Production frontend still static HTML

PRD says production UI must be Svelte + TypeScript + Vite.

Current:

- `frontend/index.html`
- `frontend/dashboard.html`
- `frontend/project_detail.html`
- `frontend/report.html`
- `frontend/second_brain.html`
- `frontend/automations.html`
- `frontend/settings.html`
- `frontend/assets/tailwind.min.js`

`frontend/index.html:2` loads:

```html
<script src="assets/tailwind.min.js"></script>
```

Conflict: current frontend is static HTML + Tailwind browser script, not Svelte/Vite.

### 2. pywebview loads raw HTML file URI

PRD says production output must be served by pywebview local HTTP server / serve-folder mode, not raw `file://`.

Current evidence from `project_tracker/app_web.py` grep:

```text
335: frontend_path = Path(__file__).resolve().parent.parent / "frontend" / "dashboard.html"
336: webview.create_window(
338:     frontend_path.as_uri(),
344: webview.start()
```

Conflict: app opens `frontend/dashboard.html` by `as_uri()`.

### 3. Bridge lives in wrong layer

PRD target:

```text
web/js_api.py
web/event_queue.py
```

Current:

- `AppAPI` lives in `project_tracker/app_web.py`.
- No `web/` directory.
- No event queue.

Conflict: bridge is not in target architecture and lacks event polling layer.

### 4. SQLite cache/index missing

PRD says SQLite cache is locked ADR and Phase B build target.

Current:

- No `project_tracker/infrastructure/cache_db.py`.
- No SQLite references found.
- No `.db`/`.sqlite` files found.
- `requirements.txt` has no explicit APScheduler and no cache DB module.

Conflict: dashboard/report likely scan live filesystem, not cache/index.

### 5. APScheduler missing

PRD says APScheduler required for:

- Auto IN-PROGRESS.
- Scheduler alarms.
- Rules Engine polling.
- Auto-refresh polling.

Current:

- No `apscheduler` in `requirements.txt`.
- No `APScheduler`/`apscheduler` usage in `project_tracker/`.

Conflict: background task architecture missing.

### 6. watchdog added despite PRD optional status

PRD says `watchdog>=4.0.0` is optional and requires confirmation before adding.

Current `requirements.txt` includes:

```text
watchdog>=4.0.0
```

Conflict unless user previously approved dependency. Phase 0 should record approval status or remove later only with explicit approval.

### 7. Notes still stored in `project_data.json`

PRD says:

- `notes.md` is primary notes storage.
- `notes` JSON field is legacy/not used.

Current evidence:

- `project_tracker/core/models.py` has `notes: str = ""`.
- `project_tracker/app_web.py` reads and appends `metadata.notes`.
- `project_tracker/app_web.py` returns `"notes": metadata.notes`.

Conflict: current implementation persists/uses notes inside metadata model.

### 8. `PROJECT_STATUS.md` missing

CLAUDE says Phase 0 safe task includes:

- create/update `PROJECT_STATUS.md`
- create/update `MIGRATION_PLAN.md`

Current:

- `PROJECT_STATUS_old.md` exists.
- No `PROJECT_STATUS.md`.
- No `MIGRATION_PLAN.md`.

Conflict: Phase 0 docs not initialized.

### 9. Old frontend assumptions still active

PRD says old static HTML frontend is legacy/reference unless verified as part of new Svelte frontend.

Current pywebview entrypoint uses `frontend/dashboard.html`.

Conflict: legacy/reference frontend is still production entry.

### 10. `redesign_ui/CLAUDE.md` says HTML frontend

`redesign_ui/_REFERENCE_ONLY.md` says:

```text
HTML implementation lives in `frontend/`.
```

But PRD now says Svelte + TypeScript + Vite production frontend.

Conflict: reference doc wording is stale. Phase 0 can update reference marker/docs, not implementation code.

## Risk list

| Risk                                                             |   Severity | Why                                                                                                     |
| ---------------------------------------------------------------- | ---------: | ------------------------------------------------------------------------------------------------------- |
| Static HTML remains production path                              |       High | Violates locked frontend architecture and blocks Svelte migration.                                      |
| Raw `file://` pywebview loading                                  |       High | Violates PRD production serving model; may break packaging/security behavior.                           |
| No SQLite cache/index                                            |       High | Dashboard/report/scanner scalability and rebuild behavior missing.                                      |
| No APScheduler                                                   |       High | Auto IN-PROGRESS, scheduler alarms, rules engine cannot exist as specified.                             |
| No event queue                                                   |       High | Background-to-frontend notification architecture absent.                                                |
| Mixed bridge response formats                                    |     Medium | Frontend cannot safely type bridge calls.                                                               |
| Notes in JSON                                                    |     Medium | Data model conflicts with canonical `notes.md` rule.                                                    |
| `watchdog` dependency present                                    |     Medium | Optional dependency may violate “no deps without confirmation.”                                         |
| Static frontend screens may look functional but be dummy/partial |     Medium | User may mistake prototype/static pages for migrated screens.                                           |
| Old docs still present                                           | Low/Medium | `PRD_old.md`, `PROJECT_STATUS_old.md`, and reference docs can mislead agents. Keep but mark superseded. |
| `redesign_ui/.venv` inside repo tree                             | Low/Medium | Search noise, possible packaging confusion if not ignored/excluded.                                     |
| No Phase 0 status docs                                           |     Medium | Migration progress cannot be tracked phase-by-phase.                                                    |

## Existing frontend screen status

| Screen         | File                           | Reality                                                                     |
| -------------- | ------------------------------ | --------------------------------------------------------------------------- |
| Index          | `frontend/index.html`          | Static landing page; checks pywebview bridge if available.                  |
| Dashboard      | `frontend/dashboard.html`      | Current pywebview target. Likely partially wired to bridge, but not Svelte. |
| Project Detail | `frontend/project_detail.html` | Static HTML page, not PRD target Svelte page.                               |
| Second Brain   | `frontend/second_brain.html`   | Static HTML page, likely dummy/partial.                                     |
| Report         | `frontend/report.html`         | Static HTML page, likely dummy/partial.                                     |
| Automations    | `frontend/automations.html`    | Static HTML page, likely dummy/partial.                                     |
| Settings       | `frontend/settings.html`       | Static HTML page, likely partial.                                           |

Audit conclusion: current screens are legacy/static implementation, not PRD v3.1 production frontend. Do not claim migrated.

## App entrypoint status

Current:

```text
project_tracker/main.py -> project_tracker.app_web.run()
project_tracker/app_web.py -> pywebview.create_window(...)
```

So app entrypoint is pywebview, not PyQt.

But it loads old static HTML through file URI:

```text
frontend/dashboard.html
frontend_path.as_uri()
```

Status: shell migrated from PyQt to pywebview, but not PRD-compliant production serving model.

## PyQt6 status

Production package:

- `project_tracker/` has no PyQt imports found.

Reference package:

- `redesign_ui/*.py` imports PyQt6.
- `redesign_ui/_REFERENCE_ONLY.md` marks files reference only.
- `redesign_ui/CLAUDE.md` says PyQt6 files are UX/userflow reference.

Status: PyQt6 appears reference-only, not production code. Caveat: `redesign_ui/.venv` is inside repo tree and creates noisy PyQt matches.

## PRD.md and CLAUDE.md alignment

Mostly aligned.

Aligned:

- PRD v3.1 is source of truth.
- Production frontend must be Svelte + TypeScript + Vite + Tailwind.
- pywebview desktop shell.
- SQLite cache only.
- Filesystem + JSON canonical source.
- PyQt6 reference-only.
- Phase-by-phase migration.
- Linux/Windows boundaries.
- No hard delete.
- Do not implement whole PRD in one pass.

Minor doc conflicts/staleness:

- `redesign_ui/_REFERENCE_ONLY.md` still says “HTML implementation lives in frontend/.”
- `redesign_ui/CLAUDE.md` describes HTML/Tailwind frontend lab.
- `PROJECT_STATUS_old.md` still exists and could mislead unless new `PROJECT_STATUS.md` supersedes it.

## Recommended migration plan

### Phase 0 only — documentation and readiness lock

Do not touch production implementation yet.

1. Create `PROJECT_STATUS.md`.
   - State current repo reality.
   - Mark PRD v3.1 as source of truth.
   - Mark current static HTML frontend as legacy/reference.
   - Mark Svelte/Vite missing.
   - Mark SQLite/APScheduler/event queue missing.
   - Mark PyQt6 reference-only.
   - Track next phase: Phase A Core Domain readiness.

2. Create `MIGRATION_PLAN.md`.
   - Phase order from PRD Section 25.
   - Explicit “do not implement all at once.”
   - Define Phase A entry criteria and verification.
   - Define forbidden Phase 0 actions.

3. Optionally update `redesign_ui/_REFERENCE_ONLY.md`.
   - Replace “HTML implementation lives in frontend/” with “Production frontend target is Svelte + TypeScript + Vite under frontend/; current HTML is legacy/reference until replaced.”

4. Optionally update root `CLAUDE.md` only if needed.
   - It already aligns. Do not churn.

5. Leave `PRD.md` unchanged.
   - It is current source of truth.

6. Leave `PROJECT_STATUS_old.md` and `PRD_old.md` unchanged.
   - Do not delete without approval.
   - New docs should clearly supersede them.

### Phase A — after Phase 0 approval

Start core domain only:

- Verify enums against PRD.
- Verify models exclude `notes` and `project_state` from metadata.
- Verify state machine.
- Verify T-10.
- Verify folder name validation.
- Verify link extraction.
- Write/adjust tests.

Do not start Svelte, SQLite, APScheduler, or bridge rewrite in Phase A unless plan says so.

### Phase B — infrastructure/stores

- Add/verify `cache_db.py`.
- Settings/link bank/metadata stores.
- Filesystem scanner.
- Send2trash safety.
- Windows guard stubs.

### Phase C — services/event queue/bridge

- Move bridge to target `web/js_api.py`.
- Add `web/event_queue.py`.
- Standard bridge response shape.
- APScheduler-backed services where appropriate.

### Phase D+ — frontend migration

- Replace static HTML with Svelte + TypeScript + Vite.
- Use Context7 before Svelte/Vite/Tailwind config changes.
- Build to `web/static/`.
- pywebview serves build output.

## Phase 0 task list

No code implementation.

- [ ] Create `PROJECT_STATUS.md`.
  - Include current audit summary.
  - Include PRD compliance matrix.
  - Include “screens not migrated” warning.
  - Include next phase gate.

- [ ] Create `MIGRATION_PLAN.md`.
  - Mirror PRD Section 25.
  - Add per-phase entry/exit criteria.
  - Add “Phase 0 touched files only” rule.

- [ ] Update `redesign_ui/_REFERENCE_ONLY.md` if approved.
  - Clarify PyQt6 files and old HTML are UX/reference only.
  - Clarify production target is Svelte/Vite.

- [ ] Optionally add a root note in `PROJECT_STATUS.md` that `PROJECT_STATUS_old.md` is superseded.
  - Do not edit/delete old file unless approved.

- [ ] Verify Phase 0 docs only.
  - Run markdown/file existence checks.
  - Do not run frontend build; no Svelte project exists.
  - Do not run pywebview app; audit only.

## Files likely touched in Phase 0 only

Recommended:

```text
PROJECT_STATUS.md
MIGRATION_PLAN.md
redesign_ui/_REFERENCE_ONLY.md
```

Possibly touched only if contradiction found during doc update:

```text
CLAUDE.md
```

Do not touch in Phase 0:

```text
PRD.md
requirements.txt
project_tracker/
frontend/
redesign_ui/*.py
PRD_old.md
PROJECT_STATUS_old.md
```

## Verification evidence used

Commands/read checks performed during audit:

```text
Read PRD.md
Read CLAUDE.md
find repo tree
find project_tracker Python files
list frontend/
read frontend/index.html
grep pywebview startup wiring
grep Tailwind/static frontend markers
grep PyQt markers
grep SQLite/APScheduler/event_queue markers
grep metadata notes/project_state markers
check PROJECT_STATUS.md and MIGRATION_PLAN.md
read redesign_ui/_REFERENCE_ONLY.md
```

Key observed outputs:

```text
frontend/package.json missing
No Svelte/Vite config files found
No SQLite cache_db.py references found
No APScheduler usage found
No event_queue usage found
project_tracker/main.py -> project_tracker.app_web.run()
project_tracker/app_web.py uses frontend/dashboard.html and frontend_path.as_uri()
```

## Bottom line

Repo is not ready for PRD v3.1 implementation beyond Phase 0.

Phase 0 should only create/update migration tracking docs and mark legacy/reference boundaries. Next implementation phase should start with Phase A Core Domain, not frontend rewrite, not SQLite, not scheduler.
