# Piece A Design — Appcode Folder Structure + CR/Non-CR Project Types

**Date:** 2026-07-01  
**Author:** Sayyid M. Ibrahim  
**Branch:** `general/appcode-structure`  
**Status:** Approved (pending implementation)  
**Scope:** Piece A of 4 — the foundation sub-project. Pieces B, C, D are separate spec->plan->implementation cycles.

---

## Context & Motivation

The app currently uses a single-level folder structure: `{ROOT}/{YEAR}/{STATE}/{PROJECT}/{SUBPROJECT}/`. This design introduces a new structure with **appcode** grouping, **CR vs Non-CR** project types, **state folders relocated inside CR**, and the **"sub project" -> "drone"** terminology change.

This is a **greenfield** change — no existing real data to migrate.

---

## Decomposition (4 Pieces)

| Piece | Scope | Dependencies |
|-------|-------|-------------|
| **A (this spec)** | Core folder structure + project types + drone rename + scanner/model/cache | None — foundation |
| B | `_cr-docs` editable files + multi-file RTE editor dropdown | A |
| C | Approval automation (email polling + `.msg` auto-download) | A + B |
| D | CICD Bitbucket clone helper + repo file browser + git detection | A (parallel with B/C) |

**Build order:** A -> B -> C, with D parallel to B/C after A.
---

## Section 1: Complete Folder Structure & Path Model

### Full tree

```
{root_folder}/                              <- e.g. D:\WORK\ (existing setting, unchanged)
  {appcode}/                                <- user adds; each has appcode.json
    appcode.json                            <- per-appcode config (display name, CICD location pref)
    CICD/                                   <- local Bitbucket repos (created empty in Piece A;
    |                                         Piece D adds clone helper + browser)
    {YEAR}/                                 <- e.g. 2026
      CR/                                   <- literal; holds state folders
        UAT_PREPARE/                        <- 5 state folders (relocated inside CR)
        PROD_READY/
        IMPLEMENTED/
        POSTPONED/
        CANCELED/
          {projectName}/                    <- one CR project
            project_data.json               <- canonical metadata
            notes.md                        <- project-level notes
            _cr-docs/                       <- created empty in Piece A; Piece B fills the 4 files
            {droneName}/                    <- named, renameable (was "sub project")
              UAT/                          <- UAT server package (auto-created, empty)
              PRD/                          <- production server package (auto-created, empty)
              notes.md                      <- drone own notes (auto-created, empty)
      Non-CR/                               <- literal; no state folders
        {projectName}/                      <- one Non-CR project
          project_data.json                 <- metadata (project_type=NON_CR, non_cr_state)
          notes.md                          <- project notes
```

### Path helpers

Today the app derives state and year from folder depth. The new CR path is 2 levels deeper.

```python
# CR project: root/appcode/YEAR/CR/STATE/project
state_from_cr_project_path(path)      -> ProjectState(path.parent.name)           # STATE
year_path_from_cr_project_path(path)  -> path.parent.parent.parent               # up 3 = YEAR
cr_appcode_from_project_path(path)    -> path.parent.parent.parent.parent        # up 4 = appcode

# Non-CR project: root/appcode/YEAR/Non-CR/project
non_cr_year_path_from_project_path(path)   -> path.parent.parent                # up 2 = YEAR
non_cr_appcode_from_project_path(path)     -> path.parent.parent.parent         # up 3 = appcode

# Type derivation
project_type_from_path(path) -> checks whether an ancestor folder is named CR or Non-CR
```

### What gets created when

| Action | Folders/files created |
|--------|----------------------|
| Add appcode | `{root}/{appcode}/` + `appcode.json` + `CICD/` (empty) |
| Add Year (under appcode) | `{appcode}/{YEAR}/CR/` + 5 state folders + `{appcode}/{YEAR}/Non-CR/` |
| Add CR project (CR only) | `{appcode}/{YEAR}/CR/{STATE}/{projectName}/` + `project_data.json` + `notes.md` + `_cr-docs/` (empty) |
| Add CR project (CR with drone) | Above + first `{droneName}/` + `UAT/` + `PRD/` + `notes.md` |
| Add Drone Ticket | `{project}/{droneName}/` + `UAT/` + `PRD/` + `notes.md` |
| Add Non-CR project | `{appcode}/{YEAR}/Non-CR/{projectName}/` + `project_data.json` (type=NON_CR) + `notes.md` |

### Key decisions

1. `CICD/` is created as an empty folder in Piece A — clone helper/browser is Piece D.
2. `_cr-docs/` is created empty in Piece A — the 4 files are Piece B.
3. Drone `UAT/` + `PRD/` + `notes.md` are mandatory and auto-created on every drone creation.
4. The 5 state folder names are unchanged — only their location moves (inside `CR/`).
5. `Non-CR/` has no state folders — Non-CR state lives in `project_data.json`.
---

## Section 2: Domain Model Changes

### New enums (`core/enums.py`)

```python
class ProjectType(StrEnum):
    CR = "CR"
    NON_CR = "NON_CR"

class NonCrState(StrEnum):
    PLANNING = "PLANNING"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
```

`ProjectState` (the 5 folder states) stays unchanged — applies to CR projects only.

### `ProjectMetadata` changes (`core/models.py`)

Two new fields:

```python
project_type: ProjectType = ProjectType.CR          # NEW
non_cr_state: NonCrState | None = None              # NEW (None for CR projects)
```

**Semantics by type:**

| Field | CR project | Non-CR project |
|-------|-----------|----------------|
| `project_type` | `CR` | `NON_CR` |
| `non_cr_state` | `None` (ignored) | `PLANNING` / `IN_PROGRESS` / `DONE` |
| `cr_link`, `cr_state`, `cr_state_updated_at`, `cr_pending_approval_at` | Used | Empty/unused |
| `drone_tickets` | Used (0+ drones) | Empty list |
| `start_datetime`, `end_datetime`, `history`, `email_flags`, `implementation_plan` | Used | Used |

### `DroneTicket` — no structural change

The `DroneTicket` dataclass is already the drone concept. The only change is terminology: "sub project" -> "drone" everywhere in code/UI/docs. The `subfolder_name` field keeps its name (it is the drone folder name).

### New `AppCodeConfig` model (`core/models.py`)

```python
@dataclass(slots=True)
class AppCodeConfig:
    display_name: str = ""
    cicd_location: str = "per_appcode"        # "per_appcode" | "shared_root"
    cicd_shared_path: Path | None = None      # only when cicd_location == "shared_root"
    created_at: datetime | None = None
```

Stored at `{root}/{appcode}/appcode.json`.

### `AppSettings` — no new fields

`root_folder` stays as-is. Appcodes are discovered by scanning `{root_folder}/*/` for folders containing `appcode.json` — not stored as a list in `settings.json`.

### `ScannedProject` — add appcode + project_type

```python
@dataclass(frozen=True, slots=True)
class ScannedProject:
    path: Path
    year: str
    appcode: str                # NEW
    project_type: ProjectType   # NEW
    project_state: ProjectState | None   # None for Non-CR
    metadata: ProjectMetadata
    drone_paths: list[Path]     # RENAMED from subproject_paths
```

---

## Section 3: Scanner & Filesystem Changes

### Appcode discovery (`infrastructure/filesystem.py`)

```python
def discover_appcodes(root_folder: Path) -> list[AppCodeEntry]:
    """Scan {root}/* for folders containing appcode.json."""

@dataclass(frozen=True, slots=True)
class AppCodeEntry:
    path: Path
    name: str
    config: AppCodeConfig
```

### `scan_appcode_year` (replaces `scan_year`)

```python
def scan_appcode_year(appcode_path: Path, year: str, metadata_store=None) -> list[ScannedProject]:
    # CR branch: year/CR/{STATE}/project
    # Non-CR branch: year/Non-CR/project (no state folders)
```

CR branch iterates the 5 `ProjectState` folders. Non-CR branch iterates projects directly. Non-CR projects get `project_state=None` and `drone_paths=[]`.

### `discover_drone_paths` (replaces `discover_subproject_paths`)

```python
def discover_drone_paths(project_path: Path) -> list[Path]:
    return sorted(
        child for child in project_path.iterdir()
        if child.is_dir()
        and not is_organizational_folder(child)
        and child.name != "_cr-docs"          # NEW exclusion
    )
```

### `ensure_appcode_year_structure` (replaces `ensure_year_structure`)

```python
def ensure_appcode_year_structure(appcode_path: Path, year: int) -> None:
    """Create appcode/{YEAR}/CR/{5 states} + appcode/{YEAR}/Non-CR/."""
```

### Cache — new columns + appcode-aware rows

`CachedProjectRow` new fields:
- `appcode: str = ""`
- `project_type: ProjectType = ProjectType.CR`
- `non_cr_state: NonCrState | None = None`
- `drone_paths_json: str = "[]"` (renamed from `subprojects_json`)

Schema migration via `_migrate_schema` (ALTER TABLE ADD COLUMN + RENAME COLUMN). `folder_state` for Non-CR projects stores sentinel `"NON_CR"`.

`list_projects(year, appcode)` — adds optional appcode filter.
`rebuild_year_cache` -> `rebuild_appcode_year_cache(cache, appcode_path, year, metadata_store)`.
`replace_projects_for_year` -> `replace_projects_for_appcode_year(appcode, year, rows)` — WHERE clause adds `AND appcode = ?`.

### Unchanged

- `MetadataStore` — no changes (reads/writes `project_data.json` from project path).
- File validation (`validate_file_name`, `assert_within`, atomic writes) — unchanged.
- Delete (`send_to_recycle_bin`) — unchanged.
---

## Section 4: Project Creation & Drone Scaffolding

### Add Appcode

Creates `{root}/{appcode}/` + `appcode.json` + `CICD/` (empty). Validates folder name. Appcodes are filesystem-discovered (folders with `appcode.json`). Remove appcode = `send2trash` the folder.

### Add Year (appcode-scoped)

`create_year(appcode, year)` calls `ensure_appcode_year_structure`. `list_years(appcode)` scans `{root}/{appcode}/*` for digit-named folders.

### Add Project — dropdown: CR only vs CR with drone vs Non-CR

The frontend Add Project form gains a **project type selector**. The bridge receives `project_type` + optional `drone_name`:

- **CR only:** creates project folder + `project_data.json` + `notes.md` + `_cr-docs/` (empty). No drone.
- **CR with drone:** above + first drone folder (UAT/ + PRD/ + notes.md).
- **Non-CR:** creates `Non-CR/{projectName}/` + `project_data.json` (type=NON_CR, non_cr_state=PLANNING) + `notes.md`. No `_cr-docs`, no drones.

New CR projects always start in `UAT_PREPARE`.

### Add Drone Ticket (`_scaffold_drone`)

```python
def _scaffold_drone(project_path: Path, drone_name: str) -> Path:
    """Create {project}/{drone}/ + UAT/ + PRD/ + notes.md."""
    validate_windows_folder_name(drone_name)
    drone_path = project_path / drone_name
    if drone_path.exists():
        raise ValueError(f"Drone folder already exists: {drone_path}")
    drone_path.mkdir(parents=True)
    (drone_path / "UAT").mkdir()
    (drone_path / "PRD").mkdir()
    (drone_path / "notes.md").touch()
    return drone_path
```

Used by `create_project` (CR with drone) and `create_drone` (add to existing). Appends `DroneTicket(subfolder_name=drone_name)` to metadata.

### Rename / delete drone

- **Rename:** moves folder + updates `DroneTicket.subfolder_name` in metadata.
- **Delete:** `send2trash` drone folder + removes matching `DroneTicket` from metadata.

### Non-CR state transitions

Metadata-only write — no folder move. New method `set_non_cr_state(project_path, target_state)`.

---

## Section 5: Non-CR State Machine & Transitions

### Transition map (`core/state_machine.py`)

```python
NON_CR_TRANSITIONS: dict[NonCrState, frozenset[NonCrState]] = {
    NonCrState.PLANNING: frozenset({NonCrState.IN_PROGRESS, NonCrState.DONE}),
    NonCrState.IN_PROGRESS: frozenset({NonCrState.DONE, NonCrState.PLANNING}),
    NonCrState.DONE: frozenset({NonCrState.IN_PROGRESS}),
}
```

```
PLANNING -> IN_PROGRESS, DONE
IN_PROGRESS -> DONE, PLANNING
DONE -> IN_PROGRESS
```

Pure functions: `valid_next_non_cr_states`, `can_transition_non_cr`, `validate_non_cr_transition`. Matches existing state_machine.py pattern (frozenset maps + validate_* functions).

### `set_non_cr_state` service method

Validates `project_type == NON_CR`, validates transition, updates `non_cr_state` + history, saves metadata. No folder move. Cache row updated via `cache.upsert_project`.

### CR state machine — unchanged

All CR transition logic (`CR_MANUAL_TRANSITIONS`, `CR_AUTOMATIC_TRANSITIONS`, `PROJECT_STATE_TRANSITIONS`, all validate_* functions) stays as-is. Only path depth changes (handled by path helpers).

### Auto-move — CR only

`resolve_auto_move` is not called for Non-CR projects. Bridge checks `project_type` before routing. Non-CR state changes are explicit user actions only (no automatic transitions).
---

## Section 6: Bridge & Frontend DTO Changes

### Python DTOs

`DashboardProject` gains: `appcode`, `project_type`, `non_cr_state`, `drones` (renamed from `subprojects`).
`DashboardSummary` gains `by_project_type` mapping.

`ProjectDetail` dict gains: `appcode`, `project_type`, `non_cr_state`, `drones` (renamed from `subprojects`), `drone_paths`.

For Non-CR: `cr_number`/`cr_link`/`cr_state`/`drone_tickets` are empty/null; `non_cr_state` carries state.

### New bridge methods

- `AppCodeServiceProtocol`: `list_appcodes`, `add_appcode`, `remove_appcode`, `get_appcode_config`, `update_appcode_config`.
- Year methods: `list_years(appcode)`, `create_year(appcode, year)`.
- Project: `create_project(data)` with `appcode` + `project_type` + `drone_name`.
- Drone (renamed from subproject): `list_drones`, `create_drone`, `delete_drone`.
- Non-CR state: `set_non_cr_state(project_path, target_state)`.
- `list_projects(year, appcode)` — appcode filter.

### Frontend types (`frontend/src/lib/types.ts`)

`DashboardProject` and `ProjectDetail` gain `appcode`, `project_type`, `non_cr_state`, `drones` (renamed from `subprojects`). New `AppCode` interface. `is_subproject` removed.

### Frontend changes (Piece A scope)

- `SubProjectTable.svelte` -> `DroneTable.svelte` (rename + props `subprojects` -> `drones`).
- `NewProjectForm.svelte` — project-type dropdown + appcode selector + conditional drone name field.
- `ProjectDetails.svelte` — conditional Non-CR state dropdown; hide CR/Drone for Non-CR; "Drone" labels.
- `Dashboard.svelte` — appcode selector; Non-CR row rendering.
- `bridge.ts` — new appcode wrappers; renamed drone methods.
- `folderLocks.ts` — rename `create_subproject`/`delete_subproject` -> `create_drone`/`delete_drone`.

---

## Section 7: Error Handling & Edge Cases

### Scanner reconciliation & warnings

| Edge case | Detection | Handling |
|-----------|-----------|----------|
| Appcode folder without `appcode.json` | `discover_appcodes` skips | Ignored (not registered) |
| Year folder missing `CR/` or `Non-CR/` | `scan_appcode_year` checks `is_dir()` | Warning; missing branch = no projects |
| CR project missing `project_data.json` | `MetadataStore.read` (existing) | Warning + default metadata |
| Drone folder missing `UAT/` or `PRD/` | New `validate_drone_folders` check | Warning (no auto-create) |
| Non-CR project with CR/Drone fields | Scanner checks type vs fields | Warning (fields ignored, not cleared) |
| Drone folders vs metadata mismatch | `discover_drone_paths` vs `metadata.drone_tickets` | Warning (disk = truth for folders) |

### Type/path consistency guards

| Edge case | Guard |
|-----------|-------|
| `set_non_cr_state` on CR project | `ValueError` |
| Folder-state transition on Non-CR | Bridge checks `project_type`; frontend hides buttons |
| Path/metadata type mismatch | Scanner overrides from path; warning on mismatch |
| Drone name = `_cr-docs` or organizational | `InvalidFolderNameError` |

### First-run / empty states

- No appcodes -> "Add an appcode to start."
- Appcode but no years -> "Add a year to start."
- Year but no projects -> existing empty-state.
- Root not configured -> existing Settings prompt.

### Cache rebuild strategy

| Operation | Rebuild scope |
|-----------|---------------|
| Add/remove appcode | All |
| Add/remove year | That appcode year |
| Add/remove/rename project or drone | That appcode year |
| CR state transition | That appcode year (path changed) |
| Non-CR state change | Single row upsert (path unchanged) |
---

## Section 8: Testing + References & Docs to Update

### New test files

- `tests/test_appcode_discovery.py` — discover_appcodes with/without appcode.json, root not set
- `tests/test_appcode_config.py` — AppCodeConfig from_dict/to_dict roundtrip, defaults
- `tests/test_scan_appcode_year.py` — CR branch (5 states), Non-CR branch, missing folders, drone discovery + _cr-docs exclusion
- `tests/test_non_cr_state_machine.py` — NON_CR_TRANSITIONS map, validate_non_cr_transition valid/invalid
- `tests/test_non_cr_project_service.py` — set_non_cr_state valid/invalid, called on CR project raises
- `tests/test_create_project_types.py` — create_project with CR only, CR with drone, NON_CR
- `tests/test_drone_scaffold.py` — _scaffold_drone creates UAT/PRD/notes.md, name validation, _cr-docs collision
- `tests/test_project_type_from_path.py` — project_type_from_path under CR/ vs Non-CR/

### Existing tests to update (path depth + rename)

All test files using `root/year/STATE/project` scaffolds must add appcode + CR levels. All `subproject` references -> `drone`. Key files:

- `test_phase_b_stores.py`, `test_phase_b_cache_db.py`, `test_phase_b_cache_mapping.py`, `test_phase_b_cache_rebuild.py`
- `test_phase_c_dashboard_service.py`, `test_phase_c_js_api_subproject_file_notes.py` (rename to drone), `test_phase_c_js_api_project.py`, `test_phase_c_scanner_service.py`
- `test_project_rename_delete.py`, `test_project_service_reopen.py`, `test_project_transitions_unit.py`, `test_project_transitions_property.py`
- `test_year_create.py`, `test_phase_e_cr_state_guarded.py`, `test_phase_f_drone_state_guarded.py`, `test_phase_g_project_create_update.py`
- `test_core_models.py`, `test_core_enums.py`, `test_core_state_machine.py`

### Frontend tests

- `frontend/tests/components.test.mjs` — SubProjectTable -> DroneTable import
- `frontend/tests/project-details-fase3-fase4.test.mjs` — sub-projects -> drones assertions
- `frontend/tests/project-actions.test.mjs` — onSubprojectsChanged -> onDronesChanged

### Manual checklist (per CLAUDE.md mandatory rule)

After implementation: appcode add/remove, year add (appcode-scoped), project create (all 3 types), drone add/rename/delete, Non-CR state dropdown, dashboard appcode filter, responsive at 3+ window sizes.

### Docs to update

| File | Change |
|------|--------|
| `PRD.md` Section 7 (Filesystem Model) | Full rewrite: root/appcode/year/CR/STATE/project + Non-CR; Sub Project -> Drone; new appcode/CICD sections |
| `PRD.md` Section 12 (Project Details) | Add Project dropdown; Sub Project -> Drone; Non-CR state dropdown |
| `PRD.md` Section 11 (Dashboard) | Appcode filter; Non-CR row rendering |
| `PRD.md` Section 9 (State) | Non-CR state machine (Planning/In Progress/Done) |
| `PRD.md` Section 21 (JsApi) | New appcode methods; renamed drone methods; set_non_cr_state |
| `_docs/ARCHITECTURE.md` | Persistence Model table; appcode row; project_type row; Sub project -> Drone |
| `_docs/DECISIONS.md` | New D-0008: appcode structure + CR/Non-CR types + drone rename |
| `_docs/FILE_ROUTING.md` | Note `_cr-docs/` as runtime data folder |
| `_docs/DESIGN_RULES.md` | SubProjectTable -> DroneTable; Non-CR state dropdown styling |
| `_docs/PROGRESS.md` | New active slice |
| `_docs/session-notes.md` | Update Now/Next/Blocked |
| `CLAUDE.md` | Note PRD Section 7 rewrite in Documentation Sync |

### Backend code references (full rename + new list)

- `core/enums.py` — Add ProjectType, NonCrState
- `core/models.py` — ProjectMetadata +2 fields; new AppCodeConfig; ScannedProject +3 fields, subproject_paths -> drone_paths
- `core/state_machine.py` — Add NON_CR_TRANSITIONS + validate_non_cr_transition
- `infrastructure/filesystem.py` — ensure_year_structure -> ensure_appcode_year_structure; scan_year -> scan_appcode_year; discover_subproject_paths -> discover_drone_paths (+ _cr-docs exclusion); new discover_appcodes; new _scaffold_drone
- `infrastructure/cache_db.py` — CachedProjectRow +3 fields, subprojects_json -> drone_paths_json; schema migration; list_projects appcode param; replace_projects_for_year -> replace_projects_for_appcode_year
- `infrastructure/settings_store.py` — write calls ensure_appcode_year_structure per discovered appcode
- `services/scanner_service.py` — rebuild_year -> rebuild_appcode_year; discover_subproject_folders -> discover_drone_folders; validate_drone_subfolders -> validate_drone_folders (+ UAT/PRD check)
- `services/project_service.py` — path helpers new depth; delete_subproject -> delete_drone; new set_non_cr_state; new _scaffold_drone usage
- `services/dashboard_service.py` — DashboardProject +3 fields, subprojects -> drones; DashboardSummary + by_project_type; list_projects appcode param
- `web/js_api.py` — Protocols: list_subprojects->list_drones, create_subproject->create_drone, delete_subproject->delete_drone; new AppCodeServiceProtocol; year methods appcode-scoped; new set_non_cr_state
- `app_web.py` — create_project new params; _YearServiceAdapter appcode-scoped; new _AppCodeServiceAdapter; create_subproject->create_drone; path helpers updated; _folder_state_for_path updated

### Frontend code references (full rename + new list)

- `frontend/src/lib/components/SubProjectTable.svelte` -> `DroneTable.svelte`
- `frontend/src/lib/types.ts` — DashboardProject/ProjectDetail new fields; new AppCode interface
- `frontend/src/lib/components/ProjectDetails.svelte` — DroneTable import; Non-CR conditional; Drone labels
- `frontend/src/lib/components/Dashboard.svelte` — appcode selector; Non-CR rows; drones
- `frontend/src/lib/components/ProjectActions.svelte` — onSubprojectsChanged -> onDronesChanged
- `frontend/src/lib/components/NewProjectForm.svelte` — project-type dropdown + appcode selector + drone name
- `frontend/src/lib/bridge.ts` — new appcode wrappers; renamed drone methods
- `frontend/src/lib/folderLocks.ts` — create_subproject/delete_subproject -> create_drone/delete_drone

### `_reference/` — DO NOT TOUCH

Per CLAUDE.md, `_reference/` is legacy visual reference only. The prototype still says "sub project" — that is historical and fine.

---

## Out of Scope (Deferred to Pieces B, C, D)

| Item | Piece |
|------|-------|
| `_cr-docs` file contents (uat-signoff, prod-lv, .msg) + multi-file RTE editor dropdown | B |
| Approval automation (conditional buttons, email polling, auto-download .msg) | C |
| CICD Bitbucket clone helper + repo file browser + git detection | D |

---

## Success Criteria for Piece A

1. User can add multiple appcodes under the root folder, each with appcode.json + CICD/.
2. User can add years under an appcode, creating CR/ + 5 state folders + Non-CR/.
3. Add Project offers 3 types: CR only, CR with drone, Non-CR.
4. CR projects scaffold correctly (project_data.json, notes.md, _cr-docs/).
5. Drones scaffold with UAT/ + PRD/ + notes.md; can be added/renamed/deleted.
6. Non-CR projects have Planning/In Progress/Done state in metadata (no state folders).
7. Scanner discovers appcodes, years, CR + Non-CR projects, and drones correctly.
8. Cache stores appcode + project_type + non_cr_state; appcode-scoped rebuilds work.
9. Dashboard shows appcode selector + Non-CR rows with non_cr_state.
10. All "sub project" references renamed to "drone" across code, docs, UI, tests.
11. PRD Section 7 + ARCHITECTURE + DECISIONS updated to reflect the new structure.
12. All existing tests pass with updated path scaffolds; new tests pass.