# Piece A Implementation Plan — Appcode Folder Structure + CR/Non-CR Project Types

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the project folder hierarchy from `{ROOT}/{YEAR}/{STATE}/{PROJECT}/{SUBPROJECT}/` to `{ROOT}/{appcode}/{YEAR}/CR/{STATE}/{PROJECT}/{drone}/UAT+PRD` + `{ROOT}/{appcode}/{YEAR}/Non-CR/{PROJECT}/`, add CR vs Non-CR project types, and rename "sub project" to "drone" throughout.

**Architecture:** Layered monolith (Python backend: core/infrastructure/services/web/app_web, Svelte+TS frontend). Filesystem is canonical truth, SQLite is rebuildable cache. New enums (`ProjectType`, `NonCrState`) extend the domain model. Scanner walks appcode->year->CR/Non-CR. Path helpers gain 2 levels of depth for CR projects.

**Tech Stack:** Python 3.12+, Svelte 5 + TypeScript + Vite + Tailwind, pywebview, SQLite (cache), pytest + node:test

## Global Constraints

- All project data stays local; filesystem is canonical truth, SQLite is rebuildable cache only.
- Hard delete forbidden; delete uses `send2trash` (Windows Recycle Bin).
- `core/` must be pure Python (no UI, no I/O imports).
- Bridge returns `{ success, data, error }` response objects.
- Frontend communicates with Python through pywebview bridge only.
- Greenfield: no migration of existing data needed.
- No new dependencies without user confirmation.
- Run app from repo root: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main`
- Run tests: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/ -v -k <pattern>`
- Frontend build: `npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run build`
- `_reference/` is legacy visual reference only — DO NOT TOUCH.

---

## File Structure

### New files (created)

| File | Responsibility |
|------|---------------|
| `tests/test_appcode_discovery.py` | Tests for `discover_appcodes` |
| `tests/test_appcode_config.py` | Tests for `AppCodeConfig` model |
| `tests/test_scan_appcode_year.py` | Tests for `scan_appcode_year` (CR + Non-CR branches) |
| `tests/test_non_cr_state_machine.py` | Tests for `NON_CR_TRANSITIONS` + `validate_non_cr_transition` |
| `tests/test_non_cr_project_service.py` | Tests for `set_non_cr_state` service method |
| `tests/test_create_project_types.py` | Tests for `create_project` with 3 project types |
| `tests/test_drone_scaffold.py` | Tests for `_scaffold_drone` (UAT/PRD/notes.md) |
| `tests/test_project_type_from_path.py` | Tests for `project_type_from_path` helper |

### Modified files (existing)

| File | What changes |
|------|-------------|
| `core/enums.py` | Add `ProjectType`, `NonCrState` enums |
| `core/models.py` | `ProjectMetadata` +2 fields; new `AppCodeConfig`; `ScannedProject` +3 fields, rename `subproject_paths`->`drone_paths` |
| `core/state_machine.py` | Add `NON_CR_TRANSITIONS` + `validate_non_cr_transition` |
| `infrastructure/filesystem.py` | `ensure_year_structure`->`ensure_appcode_year_structure`; `scan_year`->`scan_appcode_year`; `discover_subproject_paths`->`discover_drone_paths`; new `discover_appcodes`; new `_scaffold_drone`; `ScannedProject` fields; new `project_type_from_path` |
| `infrastructure/cache_db.py` | `CachedProjectRow` +3 fields; `subprojects_json`->`drone_paths_json`; schema migration; `list_projects` appcode param; `replace_projects_for_year`->`replace_projects_for_appcode_year` |
| `infrastructure/settings_store.py` | `write` calls `ensure_appcode_year_structure` per discovered appcode |
| `services/scanner_service.py` | `rebuild_year`->`rebuild_appcode_year`; rename drone functions; UAT/PRD validation |
| `services/project_service.py` | Path helpers new depth; `delete_subproject`->`delete_drone`; new `set_non_cr_state`; new `_scaffold_drone` usage |
| `services/dashboard_service.py` | `DashboardProject` +3 fields, `subprojects`->`drones`; `DashboardSummary` +`by_project_type`; `list_projects` appcode param |
| `web/js_api.py` | Protocols: rename subproject->drone; new `AppCodeServiceProtocol`; year methods appcode-scoped; new `set_non_cr_state` |
| `app_web.py` | `create_project` new params; `_YearServiceAdapter` appcode-scoped; new `_AppCodeServiceAdapter`; rename subproject->drone; path helpers updated |
| `frontend/src/lib/types.ts` | `DashboardProject`/`ProjectDetail` new fields; new `AppCode` interface; `subprojects`->`drones` |
| `frontend/src/lib/components/SubProjectTable.svelte` | Rename to `DroneTable.svelte`; props `subprojects`->`drones` |
| `frontend/src/lib/components/ProjectDetails.svelte` | Import `DroneTable`; Non-CR conditional; Drone labels |
| `frontend/src/lib/components/Dashboard.svelte` | Appcode selector; Non-CR rows; `subprojects`->`drones` |
| `frontend/src/lib/components/ProjectActions.svelte` | `onSubprojectsChanged`->`onDronesChanged` |
| `frontend/src/lib/components/NewProjectForm.svelte` | Project-type dropdown + appcode selector + drone name |
| `frontend/src/lib/bridge.ts` | New appcode wrappers; renamed drone methods |
| `frontend/src/lib/folderLocks.ts` | Rename `create_subproject`/`delete_subproject`->`create_drone`/`delete_drone` |

### Docs to update (final task)

`PRD.md` (Section 7 rewrite), `_docs/ARCHITECTURE.md`, `_docs/DECISIONS.md` (D-0008), `_docs/FILE_ROUTING.md`, `_docs/DESIGN_RULES.md`, `_docs/PROGRESS.md`, `_docs/session-notes.md`, `CLAUDE.md`

---
## Task 1: New Enums — ProjectType + NonCrState

**Files:**
- Modify: `core/enums.py`
- Test: `tests/test_core_enums.py`

**Interfaces:**
- Produces: `ProjectType(StrEnum)` with `CR = "CR"`, `NON_CR = "NON_CR"`; `NonCrState(StrEnum)` with `PLANNING = "PLANNING"`, `IN_PROGRESS = "IN_PROGRESS"`, `DONE = "DONE"`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_core_enums.py — add to existing file or create if missing
from core.enums import ProjectType, NonCrState

def test_project_type_values():
    assert ProjectType.CR.value == "CR"
    assert ProjectType.NON_CR.value == "NON_CR"

def test_non_cr_state_values():
    assert NonCrState.PLANNING.value == "PLANNING"
    assert NonCrState.IN_PROGRESS.value == "IN_PROGRESS"
    assert NonCrState.DONE.value == "DONE"

def test_project_type_is_str_enum():
    assert isinstance(ProjectType.CR, str)
    assert ProjectType("CR") == ProjectType.CR

def test_non_cr_state_is_str_enum():
    assert isinstance(NonCrState.PLANNING, str)
    assert NonCrState("PLANNING") == NonCrState.PLANNING
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_core_enums.py -v -k "project_type or non_cr_state"`
Expected: FAIL with `ImportError: cannot import name 'ProjectType'`

- [ ] **Step 3: Write minimal implementation**

Add to the end of `core/enums.py` (after `EmailMode`):

```python
class ProjectType(StrEnum):
    CR = "CR"
    NON_CR = "NON_CR"


class NonCrState(StrEnum):
    PLANNING = "PLANNING"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_core_enums.py -v -k "project_type or non_cr_state"`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add core/enums.py tests/test_core_enums.py
git commit -m "feat(enums): add ProjectType and NonCrState enums"
```

---

## Task 2: Domain Model — ProjectMetadata + AppCodeConfig + ScannedProject

**Files:**
- Modify: `core/models.py`
- Modify: `infrastructure/filesystem.py` (ScannedProject dataclass)
- Test: `tests/test_core_models.py`

**Interfaces:**
- Consumes: `ProjectType`, `NonCrState` from Task 1
- Produces: `ProjectMetadata` with `project_type: ProjectType = ProjectType.CR` and `non_cr_state: NonCrState | None = None`; `AppCodeConfig` dataclass; `ScannedProject` with `appcode: str`, `project_type: ProjectType`, `project_state: ProjectState | None`, `drone_paths: list[Path]` (renamed from `subproject_paths`)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_core_models.py — add to existing file
from core.enums import ProjectType, NonCrState
from core.models import ProjectMetadata, AppCodeConfig

def test_project_metadata_defaults_to_cr():
    m = ProjectMetadata(project_name="Test")
    assert m.project_type == ProjectType.CR
    assert m.non_cr_state is None

def test_project_metadata_non_cr_roundtrip():
    m = ProjectMetadata(
        project_name="NonCrTask",
        project_type=ProjectType.NON_CR,
        non_cr_state=NonCrState.IN_PROGRESS,
    )
    d = m.to_dict()
    assert d["project_type"] == "NON_CR"
    assert d["non_cr_state"] == "IN_PROGRESS"
    restored = ProjectMetadata.from_dict(d)
    assert restored.project_type == ProjectType.NON_CR
    assert restored.non_cr_state == NonCrState.IN_PROGRESS

def test_project_metadata_cr_roundtrip():
    m = ProjectMetadata(project_name="CrProj", project_type=ProjectType.CR)
    d = m.to_dict()
    assert d["project_type"] == "CR"
    assert d["non_cr_state"] is None
    restored = ProjectMetadata.from_dict(d)
    assert restored.project_type == ProjectType.CR
    assert restored.non_cr_state is None

def test_appcode_config_defaults():
    c = AppCodeConfig()
    assert c.display_name == ""
    assert c.cicd_location == "per_appcode"
    assert c.cicd_shared_path is None

def test_appcode_config_roundtrip():
    c = AppCodeConfig(display_name="My Appcode", cicd_location="shared_root", cicd_shared_path=Path("D:/WORK/CICD"))
    d = c.to_dict()
    assert d["display_name"] == "My Appcode"
    assert d["cicd_location"] == "shared_root"
    restored = AppCodeConfig.from_dict(d)
    assert restored.display_name == "My Appcode"
    assert restored.cicd_location == "shared_root"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_core_models.py -v -k "project_metadata or appcode_config"`
Expected: FAIL with `ImportError: cannot import name 'AppCodeConfig'`

- [ ] **Step 3: Write minimal implementation**

In `core/models.py`, add import at top (line 8, modify the existing import line):

```python
from core.enums import CRState, DroneState, EmailMode, Language, NonCrState, ProjectType, Theme
```

Add two fields to `ProjectMetadata` (after `h10_notified_at` on line 148):

```python
    project_type: ProjectType = ProjectType.CR
    non_cr_state: NonCrState | None = None
```

Add to `ProjectMetadata.from_dict` (after `h10_notified_at=...`):

```python
            project_type=ProjectType(data.get("project_type", ProjectType.CR.value)),
            non_cr_state=NonCrState(data["non_cr_state"]) if data.get("non_cr_state") else None,
```

Add to `ProjectMetadata.to_dict` (after `"h10_notified_at": ...`):

```python
            "project_type": self.project_type.value,
            "non_cr_state": self.non_cr_state.value if self.non_cr_state else None,
```

Add `AppCodeConfig` dataclass after `ProjectMetadata` (after line 186):

```python
@dataclass(slots=True)
class AppCodeConfig:
    display_name: str = ""
    cicd_location: str = "per_appcode"
    cicd_shared_path: Path | None = None
    created_at: datetime | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppCodeConfig:
        cicd_shared = data.get("cicd_shared_path", "")
        return cls(
            display_name=str(data.get("display_name", "")),
            cicd_location=str(data.get("cicd_location", "per_appcode")),
            cicd_shared_path=Path(cicd_shared) if cicd_shared else None,
            created_at=datetime_from_json(data.get("created_at")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "display_name": self.display_name,
            "cicd_location": self.cicd_location,
            "cicd_shared_path": str(self.cicd_shared_path) if self.cicd_shared_path else "",
            "created_at": datetime_to_json(self.created_at),
        }
```

In `infrastructure/filesystem.py`, modify `ScannedProject` (lines 18-24):

```python
@dataclass(frozen=True, slots=True)
class ScannedProject:
    path: Path
    year: str
    appcode: str
    project_type: ProjectType
    project_state: ProjectState | None
    metadata: ProjectMetadata
    drone_paths: list[Path]
```

Add import at top of `infrastructure/filesystem.py`:
```python
from core.enums import ProjectState, ProjectType
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_core_models.py -v -k "project_metadata or appcode_config"`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add core/models.py infrastructure/filesystem.py tests/test_core_models.py
git commit -m "feat(models): add ProjectType/NonCrState fields, AppCodeConfig, update ScannedProject"
```

---

## Task 3: Non-CR State Machine

**Files:**
- Modify: `core/state_machine.py`
- Test: `tests/test_non_cr_state_machine.py`

**Interfaces:**
- Consumes: `NonCrState` from Task 1
- Produces: `NON_CR_TRANSITIONS` dict, `valid_next_non_cr_states(current) -> frozenset`, `can_transition_non_cr(current, target) -> bool`, `validate_non_cr_transition(current, target) -> None`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_non_cr_state_machine.py
import pytest
from core.enums import NonCrState
from core.exceptions import InvalidTransitionError
from core.state_machine import (
    NON_CR_TRANSITIONS,
    valid_next_non_cr_states,
    can_transition_non_cr,
    validate_non_cr_transition,
)

def test_planning_can_go_to_in_progress_and_done():
    assert NonCrState.IN_PROGRESS in valid_next_non_cr_states(NonCrState.PLANNING)
    assert NonCrState.DONE in valid_next_non_cr_states(NonCrState.PLANNING)

def test_in_progress_can_go_to_done_and_planning():
    assert NonCrState.DONE in valid_next_non_cr_states(NonCrState.IN_PROGRESS)
    assert NonCrState.PLANNING in valid_next_non_cr_states(NonCrState.IN_PROGRESS)

def test_done_can_go_to_in_progress():
    assert NonCrState.IN_PROGRESS in valid_next_non_cr_states(NonCrState.DONE)

def test_done_cannot_go_to_planning():
    assert NonCrState.PLANNING not in valid_next_non_cr_states(NonCrState.DONE)

def test_can_transition_non_cr_true():
    assert can_transition_non_cr(NonCrState.PLANNING, NonCrState.IN_PROGRESS) is True

def test_can_transition_non_cr_false():
    assert can_transition_non_cr(NonCrState.DONE, NonCrState.PLANNING) is False

def test_validate_non_cr_transition_valid():
    validate_non_cr_transition(NonCrState.PLANNING, NonCrState.IN_PROGRESS)

def test_validate_non_cr_transition_invalid_raises():
    with pytest.raises(InvalidTransitionError):
        validate_non_cr_transition(NonCrState.DONE, NonCrState.PLANNING)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_non_cr_state_machine.py -v`
Expected: FAIL with `ImportError: cannot import name 'NON_CR_TRANSITIONS'`

- [ ] **Step 3: Write minimal implementation**

In `core/state_machine.py`, add import (modify line 5):

```python
from core.enums import CRState, DroneState, NonCrState, ProjectState
```

Add after `PROJECT_STATE_TRANSITIONS` (after line 46):

```python
NON_CR_TRANSITIONS: dict[NonCrState, frozenset[NonCrState]] = {
    NonCrState.PLANNING: frozenset({NonCrState.IN_PROGRESS, NonCrState.DONE}),
    NonCrState.IN_PROGRESS: frozenset({NonCrState.DONE, NonCrState.PLANNING}),
    NonCrState.DONE: frozenset({NonCrState.IN_PROGRESS}),
}
```

Add at the end of the file (after all existing functions):

```python
def valid_next_non_cr_states(current_state: NonCrState) -> frozenset[NonCrState]:
    return NON_CR_TRANSITIONS[current_state]


def can_transition_non_cr(current_state: NonCrState, target_state: NonCrState) -> bool:
    return target_state in valid_next_non_cr_states(current_state)


def validate_non_cr_transition(current_state: NonCrState, target_state: NonCrState) -> None:
    if not can_transition_non_cr(current_state, target_state):
        raise InvalidTransitionError(
            f"Invalid Non-CR transition: {current_state.value} -> {target_state.value}"
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_non_cr_state_machine.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: Commit**

```bash
git add core/state_machine.py tests/test_non_cr_state_machine.py
git commit -m "feat(state-machine): add Non-CR state machine (Planning/In Progress/Done)"
```
---

## Task 4: Filesystem — Path Helpers, Appcode Discovery, Drone Scaffolding

**Files:**
- Modify: `infrastructure/filesystem.py`
- Test: `tests/test_appcode_discovery.py`
- Test: `tests/test_drone_scaffold.py`
- Test: `tests/test_project_type_from_path.py`

**Interfaces:**
- Consumes: `ProjectType`, `AppCodeConfig`, `ScannedProject` from Tasks 1-2
- Produces: `project_type_from_path(path) -> ProjectType`, `discover_appcodes(root_folder) -> list[AppCodeEntry]`, `AppCodeEntry` dataclass, `ensure_appcode_year_structure(appcode_path, year) -> None`, `discover_drone_paths(project_path) -> list[Path]` (replaces `discover_subproject_paths`), `_scaffold_drone(project_path, drone_name) -> Path`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_project_type_from_path.py
from pathlib import Path
from core.enums import ProjectType
from infrastructure.filesystem import project_type_from_path

def test_cr_project_path_returns_cr():
    path = Path("D:/WORK/MYAPP/2026/CR/UAT_PREPARE/MyProject")
    assert project_type_from_path(path) == ProjectType.CR

def test_non_cr_project_path_returns_non_cr():
    path = Path("D:/WORK/MYAPP/2026/Non-CR/MyTask")
    assert project_type_from_path(path) == ProjectType.NON_CR

def test_cr_in_implemented_state():
    path = Path("D:/WORK/MYAPP/2026/CR/IMPLEMENTED/DoneProject")
    assert project_type_from_path(path) == ProjectType.CR
```

```python
# tests/test_appcode_discovery.py
from pathlib import Path
from infrastructure.filesystem import discover_appcodes, AppCodeEntry

def test_discover_appcodes_finds_registered(tmp_path):
    appcode_dir = tmp_path / "MYAPP"
    appcode_dir.mkdir()
    (appcode_dir / "appcode.json").write_text('{"display_name":"My App"}', encoding="utf-8")
    plain_dir = tmp_path / "plain"
    plain_dir.mkdir()
    result = discover_appcodes(tmp_path)
    assert len(result) == 1
    assert result[0].name == "MYAPP"
    assert result[0].config.display_name == "My App"

def test_discover_appcodes_empty_root(tmp_path):
    assert discover_appcodes(tmp_path) == []

def test_discover_appcodes_skips_plain_folders(tmp_path):
    (tmp_path / "noconfig").mkdir()
    assert discover_appcodes(tmp_path) == []
```

```python
# tests/test_drone_scaffold.py
import pytest
from pathlib import Path
from infrastructure.filesystem import _scaffold_drone

def test_scaffold_drone_creates_uat_prd_notes(tmp_path):
    project = tmp_path / "MyProject"
    project.mkdir()
    drone = _scaffold_drone(project, "api-module")
    assert drone.is_dir()
    assert (drone / "UAT").is_dir()
    assert (drone / "PRD").is_dir()
    assert (drone / "notes.md").is_file()

def test_scaffold_drone_rejects_duplicate(tmp_path):
    project = tmp_path / "MyProject"
    project.mkdir()
    _scaffold_drone(project, "api")
    with pytest.raises(ValueError, match="already exists"):
        _scaffold_drone(project, "api")

def test_scaffold_drone_rejects_cr_docs_name(tmp_path):
    project = tmp_path / "MyProject"
    project.mkdir()
    with pytest.raises(ValueError):
        _scaffold_drone(project, "_cr-docs")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_project_type_from_path.py tests/test_appcode_discovery.py tests/test_drone_scaffold.py -v`
Expected: FAIL with `ImportError: cannot import name 'project_type_from_path'`

- [ ] **Step 3: Write minimal implementation**

In `infrastructure/filesystem.py`, add imports at top (modify existing import block):

```python
from core.enums import ProjectState, ProjectType
from core.models import AppCodeConfig, ProjectMetadata
```

Add `AppCodeEntry` dataclass after `ScannedProject`:

```python
@dataclass(frozen=True, slots=True)
class AppCodeEntry:
    path: Path
    name: str
    config: AppCodeConfig
```

Add `project_type_from_path` function:

```python
def project_type_from_path(project_path: Path) -> ProjectType:
    """Determine project type from path: under CR/ = CR, under Non-CR/ = NON_CR."""
    for parent in project_path.parents:
        if parent.name == "CR":
            return ProjectType.CR
        if parent.name == "Non-CR":
            return ProjectType.NON_CR
    return ProjectType.CR
```

Add `discover_appcodes` function:

```python
def discover_appcodes(root_folder: Path) -> list[AppCodeEntry]:
    """Scan {root}/* for folders containing appcode.json."""
    if not root_folder.exists():
        return []
    entries: list[AppCodeEntry] = []
    for child in sorted(root_folder.iterdir()):
        if not child.is_dir():
            continue
        config_path = child / "appcode.json"
        if not config_path.exists():
            continue
        import json
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        config = AppCodeConfig.from_dict(data)
        if not config.display_name:
            config.display_name = child.name
        entries.append(AppCodeEntry(path=child, name=child.name, config=config))
    return entries
```

Add `ensure_appcode_year_structure` (replaces `ensure_year_structure`):

```python
def ensure_appcode_year_structure(appcode_path: Path, year: int) -> None:
    """Create appcode/{YEAR}/CR/{5 states} + appcode/{YEAR}/Non-CR/."""
    year_path = appcode_path / str(year)
    cr_path = year_path / "CR"
    for state_name in STATE_FOLDER_NAMES:
        target = cr_path / state_name
        assert_within(appcode_path, target)
        target.mkdir(parents=True, exist_ok=True)
    non_cr_path = year_path / "Non-CR"
    assert_within(appcode_path, non_cr_path)
    non_cr_path.mkdir(parents=True, exist_ok=True)
```

Rename `discover_subproject_paths` to `discover_drone_paths` and add `_cr-docs` exclusion:

```python
def discover_drone_paths(project_path: Path) -> list[Path]:
    return sorted(
        child
        for child in project_path.iterdir()
        if child.is_dir()
        and not is_organizational_folder(child)
        and child.name != "_cr-docs"
    )
```

Add `_scaffold_drone` function:

```python
def _scaffold_drone(project_path: Path, drone_name: str) -> Path:
    """Create {project}/{drone}/ + UAT/ + PRD/ + notes.md."""
    from core.rules import validate_windows_folder_name
    validate_windows_folder_name(drone_name)
    if drone_name == "_cr-docs":
        raise ValueError("Drone name cannot be '_cr-docs' (reserved folder)")
    drone_path = project_path / drone_name
    if drone_path.exists():
        raise ValueError(f"Drone folder already exists: {drone_path}")
    drone_path.mkdir(parents=True)
    (drone_path / "UAT").mkdir()
    (drone_path / "PRD").mkdir()
    (drone_path / "notes.md").touch()
    return drone_path
```

Keep the old `ensure_year_structure` and `discover_subproject_paths` as deprecated aliases that call the new functions, so existing callers do not break during the transition. They will be removed after all callers are updated in later tasks.

- [ ] **Step 4: Run tests to verify they pass**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_project_type_from_path.py tests/test_appcode_discovery.py tests/test_drone_scaffold.py -v`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add infrastructure/filesystem.py tests/test_project_type_from_path.py tests/test_appcode_discovery.py tests/test_drone_scaffold.py
git commit -m "feat(filesystem): add path helpers, appcode discovery, drone scaffolding"
```
---

## Task 5: Scanner — scan_appcode_year + Drone Path Discovery

**Files:**
- Modify: `infrastructure/filesystem.py` (scan_year -> scan_appcode_year)
- Modify: `services/scanner_service.py`
- Test: `tests/test_scan_appcode_year.py`

**Interfaces:**
- Consumes: `ScannedProject` (with new fields), `discover_drone_paths`, `project_type_from_path` from Task 4
- Produces: `scan_appcode_year(appcode_path, year, metadata_store) -> list[ScannedProject]`; `rebuild_appcode_year(cache, appcode_path, year, metadata_store) -> list[str]` in scanner_service

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scan_appcode_year.py
from pathlib import Path
from infrastructure.filesystem import scan_appcode_year, ensure_appcode_year_structure
from infrastructure.metadata_store import MetadataStore
from core.enums import ProjectState, ProjectType

def _make_cr_project(appcode_path, year, state, name):
    project = appcode_path / str(year) / "CR" / state.value / name
    project.mkdir(parents=True)
    (project / "project_data.json").write_text(
        f'{{"$schema":"project_data_v1","project_name":"{name}","project_type":"CR"}}',
        encoding="utf-8",
    )
    (project / "notes.md").touch()
    (project / "_cr-docs").mkdir()
    return project

def _make_non_cr_project(appcode_path, year, name):
    project = appcode_path / str(year) / "Non-CR" / name
    project.mkdir(parents=True)
    (project / "project_data.json").write_text(
        f'{{"$schema":"project_data_v1","project_name":"{name}","project_type":"NON_CR","non_cr_state":"PLANNING"}}',
        encoding="utf-8",
    )
    (project / "notes.md").touch()
    return project

def test_scan_finds_cr_project(tmp_path):
    appcode = tmp_path / "MYAPP"
    appcode.mkdir()
    ensure_appcode_year_structure(appcode, 2026)
    _make_cr_project(appcode, 2026, ProjectState.UAT_PREPARE, "MyCR")
    result = scan_appcode_year(appcode, "2026")
    assert len(result) == 1
    assert result[0].project_type == ProjectType.CR
    assert result[0].project_state == ProjectState.UAT_PREPARE
    assert result[0].appcode == "MYAPP"
    assert result[0].year == "2026"

def test_scan_finds_non_cr_project(tmp_path):
    appcode = tmp_path / "MYAPP"
    appcode.mkdir()
    ensure_appcode_year_structure(appcode, 2026)
    _make_non_cr_project(appcode, 2026, "MyTask")
    result = scan_appcode_year(appcode, "2026")
    assert len(result) == 1
    assert result[0].project_type == ProjectType.NON_CR
    assert result[0].project_state is None
    assert result[0].drone_paths == []

def test_scan_finds_both_types(tmp_path):
    appcode = tmp_path / "MYAPP"
    appcode.mkdir()
    ensure_appcode_year_structure(appcode, 2026)
    _make_cr_project(appcode, 2026, ProjectState.UAT_PREPARE, "CR1")
    _make_non_cr_project(appcode, 2026, "Task1")
    result = scan_appcode_year(appcode, "2026")
    assert len(result) == 2
    types = {p.project_type for p in result}
    assert types == {ProjectType.CR, ProjectType.NON_CR}

def test_scan_empty_year(tmp_path):
    appcode = tmp_path / "MYAPP"
    appcode.mkdir()
    ensure_appcode_year_structure(appcode, 2026)
    result = scan_appcode_year(appcode, "2026")
    assert result == []

def test_scan_drone_paths_excludes_cr_docs(tmp_path):
    appcode = tmp_path / "MYAPP"
    appcode.mkdir()
    ensure_appcode_year_structure(appcode, 2026)
    project = _make_cr_project(appcode, 2026, ProjectState.UAT_PREPARE, "WithDrone")
    drone = project / "api-module"
    drone.mkdir()
    (drone / "UAT").mkdir()
    (drone / "PRD").mkdir()
    result = scan_appcode_year(appcode, "2026")
    assert len(result) == 1
    assert len(result[0].drone_paths) == 1
    assert result[0].drone_paths[0].name == "api-module"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_scan_appcode_year.py -v`
Expected: FAIL with `ImportError: cannot import name 'scan_appcode_year'`

- [ ] **Step 3: Write minimal implementation**

In `infrastructure/filesystem.py`, replace `scan_year` with `scan_appcode_year`:

```python
def scan_appcode_year(appcode_path: Path, year: str, metadata_store: MetadataStore | None = None) -> list[ScannedProject]:
    store = metadata_store or MetadataStore()
    projects: list[ScannedProject] = []
    year_path = appcode_path / year
    if not year_path.exists():
        return projects

    # CR branch: year/CR/{STATE}/project
    cr_root = year_path / "CR"
    if cr_root.is_dir():
        for state in ProjectState:
            state_path = cr_root / state.value
            if not state_path.is_dir():
                continue
            for project_path in sorted(child for child in state_path.iterdir() if child.is_dir()):
                metadata = store.read(project_path)
                if metadata is None:
                    continue
                metadata.project_type = ProjectType.CR
                projects.append(
                    ScannedProject(
                        path=project_path,
                        year=year,
                        appcode=appcode_path.name,
                        project_type=ProjectType.CR,
                        project_state=state,
                        metadata=metadata,
                        drone_paths=discover_drone_paths(project_path),
                    )
                )

    # Non-CR branch: year/Non-CR/project (no state folders)
    non_cr_root = year_path / "Non-CR"
    if non_cr_root.is_dir():
        for project_path in sorted(child for child in non_cr_root.iterdir() if child.is_dir()):
            metadata = store.read(project_path)
            if metadata is None:
                continue
            metadata.project_type = ProjectType.NON_CR
            projects.append(
                ScannedProject(
                    path=project_path,
                    year=year,
                    appcode=appcode_path.name,
                    project_type=ProjectType.NON_CR,
                    project_state=None,
                    metadata=metadata,
                    drone_paths=[],
                )
            )
    return projects
```

In `services/scanner_service.py`, rename `rebuild_year` to `rebuild_appcode_year`:

```python
def rebuild_appcode_year(self, appcode_path: Path, year: str) -> ScanYearResult:
    warnings = rebuild_appcode_year_cache(self.cache, appcode_path, year, self.metadata_store)
    return ScanYearResult(
        year=year,
        project_count=len(self.cache.list_projects(year, appcode_path.name)),
        warnings=warnings,
    )
```

Rename `discover_subproject_folders` to `discover_drone_folders` and `validate_drone_subfolders` to `validate_drone_folders`. Add UAT/PRD check in `validate_drone_folders`:

```python
def validate_drone_folders(project_path: Path, metadata: ProjectMetadata) -> list[ScanWarning]:
    warnings: list[ScanWarning] = []
    for ticket in metadata.drone_tickets:
        if not ticket.subfolder_name:
            continue
        drone_path = project_path / ticket.subfolder_name
        if not drone_path.is_dir():
            warnings.append(ScanWarning(project_path=project_path, message=f"Drone folder not found: {ticket.subfolder_name}"))
            continue
        if not (drone_path / "UAT").is_dir():
            warnings.append(ScanWarning(project_path=project_path, message=f"Drone {ticket.subfolder_name} missing UAT/ subfolder"))
        if not (drone_path / "PRD").is_dir():
            warnings.append(ScanWarning(project_path=project_path, message=f"Drone {ticket.subfolder_name} missing PRD/ subfolder"))
    return warnings
```

Keep old `scan_year` and `rebuild_year` as deprecated wrappers calling the new functions.

- [ ] **Step 4: Run test to verify it passes**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_scan_appcode_year.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add infrastructure/filesystem.py services/scanner_service.py tests/test_scan_appcode_year.py
git commit -m "feat(scanner): add scan_appcode_year with CR/Non-CR branches + drone validation"
```

---

## Task 6: Cache DB — New Columns + Appcode-Aware Rows

**Files:**
- Modify: `infrastructure/cache_db.py`
- Test: `tests/test_phase_b_cache_db.py` (update existing)

**Interfaces:**
- Consumes: `ProjectType`, `NonCrState` from Task 1, `ScannedProject` new fields from Task 2
- Produces: `CachedProjectRow` with `appcode`, `project_type`, `non_cr_state`, `drone_paths_json`; schema migration; `list_projects(year, appcode)`; `replace_projects_for_appcode_year(appcode, year, rows)`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_phase_b_cache_db.py
from core.enums import ProjectType, NonCrState

def test_cached_project_row_has_appcode_and_type():
    row = CachedProjectRow(
        project_path=Path("D:/WORK/MYAPP/2026/CR/UAT_PREPARE/Test"),
        year="2026",
        project_state=ProjectState.UAT_PREPARE,
        project_name="Test",
        appcode="MYAPP",
        project_type=ProjectType.CR,
        non_cr_state=None,
    )
    assert row.appcode == "MYAPP"
    assert row.project_type == ProjectType.CR

def test_list_projects_filters_by_appcode(tmp_path):
    cache = CacheDb(tmp_path / "test.db")
    cache.initialize()
    row1 = CachedProjectRow(
        project_path=Path(str(tmp_path / "APP1" / "2026" / "CR" / "UAT_PREPARE" / "P1")),
        year="2026", project_state=ProjectState.UAT_PREPARE, project_name="P1",
        appcode="APP1", project_type=ProjectType.CR, non_cr_state=None,
    )
    row2 = CachedProjectRow(
        project_path=Path(str(tmp_path / "APP2" / "2026" / "CR" / "UAT_PREPARE" / "P2")),
        year="2026", project_state=ProjectState.UAT_PREPARE, project_name="P2",
        appcode="APP2", project_type=ProjectType.CR, non_cr_state=None,
    )
    cache.upsert_project(row1)
    cache.upsert_project(row2)
    result = cache.list_projects("2026", appcode="APP1")
    assert len(result) == 1
    assert result[0].appcode == "APP1"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_b_cache_db.py -v -k "appcode_and_type or filters_by_appcode"`
Expected: FAIL with `TypeError: CachedProjectRow() got an unexpected keyword argument 'appcode'`

- [ ] **Step 3: Write minimal implementation**

In `infrastructure/cache_db.py`:

Add `appcode`, `project_type`, `non_cr_state` to `CachedProjectRow` (after line 48, before `t10_status`):

```python
    appcode: str = ""
    project_type: ProjectType = ProjectType.CR
    non_cr_state: NonCrState | None = None
```

Rename `subprojects_json` to `drone_paths_json` in `CachedProjectRow`.

Update `_create_schema` — add columns to `project_index` CREATE TABLE:
```sql
    appcode TEXT NOT NULL DEFAULT '',
    project_type TEXT NOT NULL DEFAULT 'CR',
    non_cr_state TEXT,
```
Rename `subprojects_json` to `drone_paths_json` in the CREATE TABLE.

Update `_migrate_schema` — add migration for existing DBs:

```python
if "appcode" not in project_columns:
    connection.execute("ALTER TABLE project_index ADD COLUMN appcode TEXT NOT NULL DEFAULT ''")
if "project_type" not in project_columns:
    connection.execute("ALTER TABLE project_index ADD COLUMN project_type TEXT NOT NULL DEFAULT 'CR'")
if "non_cr_state" not in project_columns:
    connection.execute("ALTER TABLE project_index ADD COLUMN non_cr_state TEXT")
if "subprojects_json" in project_columns and "drone_paths_json" not in project_columns:
    connection.execute("ALTER TABLE project_index RENAME COLUMN subprojects_json TO drone_paths_json")
```

Update `_project_values` to include the new fields in the tuple.

Update `cached_project_row_from_scan` to map new `ScannedProject` fields:

```python
    appcode=scanned.appcode,
    project_type=scanned.project_type,
    non_cr_state=scanned.metadata.non_cr_state,
    drone_paths_json=json.dumps([path.name for path in scanned.drone_paths], ensure_ascii=False),
```

Update `list_projects` to accept optional `appcode` param and add `AND appcode = ?` when provided.

Add `replace_projects_for_appcode_year`:

```python
def replace_projects_for_appcode_year(self, appcode: str, year: str, rows: Iterable[CachedProjectRow]) -> None:
    # Same as replace_projects_for_year but WHERE clause: year = ? AND appcode = ?
```

Update `rebuild_year_cache` -> `rebuild_appcode_year_cache`:

```python
def rebuild_appcode_year_cache(cache, appcode_path, year, metadata_store=None):
    store = metadata_store or MetadataStore()
    scanned_projects = scan_appcode_year(appcode_path, year, store)
    cache.replace_projects_for_appcode_year(appcode_path.name, year, [cached_project_row_from_scan(s) for s in scanned_projects])
    for scanned in scanned_projects:
        cache.replace_drone_tickets_for_project(scanned.path, cached_drone_rows_from_scan(scanned))
    return list(store.warnings)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_b_cache_db.py -v -k "appcode_and_type or filters_by_appcode"`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add infrastructure/cache_db.py tests/test_phase_b_cache_db.py
git commit -m "feat(cache): add appcode/project_type/non_cr_state columns + appcode-scoped queries"
```
---

## Task 7: Project Service — Path Helpers, set_non_cr_state, Drone Rename

**Files:**
- Modify: `services/project_service.py`
- Test: `tests/test_non_cr_project_service.py`
- Test: `tests/test_create_project_types.py` (partial — service layer)

**Interfaces:**
- Consumes: `NonCrState`, `ProjectType`, `validate_non_cr_transition` from Tasks 1-3; `_scaffold_drone` from Task 4
- Produces: updated `state_from_project_path` (new depth), `year_path_from_project_path` (new depth), `set_non_cr_state(project_path, target, settings) -> Path`, `delete_drone` (replaces `delete_subproject`)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_non_cr_project_service.py
import pytest
from pathlib import Path
from core.enums import NonCrState, ProjectType
from core.models import ProjectMetadata, AppSettings
from infrastructure.metadata_store import MetadataStore
from services.project_service import ProjectService

def _make_non_cr_project(tmp_path):
    appcode = tmp_path / "MYAPP"
    project = appcode / "2026" / "Non-CR" / "MyTask"
    project.mkdir(parents=True)
    store = MetadataStore()
    meta = ProjectMetadata(
        project_name="MyTask",
        project_type=ProjectType.NON_CR,
        non_cr_state=NonCrState.PLANNING,
    )
    store.save(project, meta)
    return project

def test_set_non_cr_state_planning_to_in_progress(tmp_path):
    project = _make_non_cr_project(tmp_path)
    svc = ProjectService()
    svc.set_non_cr_state(project, NonCrState.IN_PROGRESS, AppSettings())
    meta = svc.metadata_store.load(project)
    assert meta.non_cr_state == NonCrState.IN_PROGRESS
    assert len(meta.history) == 1
    assert "PLANNING" in meta.history[0].detail
    assert "IN_PROGRESS" in meta.history[0].detail

def test_set_non_cr_state_invalid_transition_raises(tmp_path):
    project = _make_non_cr_project(tmp_path)
    svc = ProjectService()
    meta = svc.metadata_store.load(project)
    meta.non_cr_state = NonCrState.DONE
    svc.metadata_store.save(project, meta)
    with pytest.raises(Exception):
        svc.set_non_cr_state(project, NonCrState.PLANNING, AppSettings())

def test_set_non_cr_state_on_cr_project_raises(tmp_path):
    appcode = tmp_path / "MYAPP"
    project = appcode / "2026" / "CR" / "UAT_PREPARE" / "MyCR"
    project.mkdir(parents=True)
    store = MetadataStore()
    store.save(project, ProjectMetadata(project_name="MyCR", project_type=ProjectType.CR))
    svc = ProjectService()
    with pytest.raises(ValueError, match="CR project"):
        svc.set_non_cr_state(project, NonCrState.IN_PROGRESS, AppSettings())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_non_cr_project_service.py -v`
Expected: FAIL with `AttributeError: 'ProjectService' object has no attribute 'set_non_cr_state'`

- [ ] **Step 3: Write minimal implementation**

In `services/project_service.py`, update path helpers (lines 28-33):

```python
def state_from_project_path(project_path: Path) -> ProjectState:
    return ProjectState(project_path.parent.name)

def year_path_from_project_path(project_path: Path) -> Path:
    # CR: root/appcode/YEAR/CR/STATE/project -> up 3 from project = YEAR
    # Non-CR: root/appcode/YEAR/Non-CR/project -> up 2 from project = YEAR
    from core.enums import ProjectType
    from infrastructure.filesystem import project_type_from_path
    if project_type_from_path(project_path) == ProjectType.CR:
        return project_path.parent.parent.parent  # up 3 = YEAR (skip STATE, CR)
    return project_path.parent.parent  # up 2 = YEAR (skip Non-CR)
```

Rename `delete_subproject` to `delete_drone`:

```python
def delete_drone(self, drone_path: Path) -> None:
    """Route a drone-folder deletion to the Recycle Bin via send2trash."""
    filesystem.send_to_recycle_bin(drone_path)
```

Add `set_non_cr_state` method to `ProjectService`:

```python
def set_non_cr_state(self, project_path: Path, target: NonCrState, settings: AppSettings) -> Path:
    """Set a Non-CR project state (metadata-only, no folder move)."""
    metadata = self.metadata_store.load(project_path)
    if metadata.project_type != ProjectType.NON_CR:
        raise ValueError("set_non_cr_state called on a CR project")
    current = metadata.non_cr_state or NonCrState.PLANNING
    validate_non_cr_transition(current, target)
    now = local_now()
    metadata.non_cr_state = target
    metadata.updated_at = now
    metadata.history.append(
        HistoryEntry(
            timestamp=now,
            action="STATE_CHANGE",
            detail=f"Non-CR: {current.value} -> {target.value}",
            user=current_user(settings),
        )
    )
    self.metadata_store.save(project_path, metadata)
    return project_path
```

Add imports at top of `services/project_service.py`:
```python
from core.enums import CRState, DroneState, NonCrState, ProjectState, ProjectType
from core.state_machine import (
    ...,
    validate_non_cr_transition,
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_non_cr_project_service.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add services/project_service.py tests/test_non_cr_project_service.py
git commit -m "feat(project-service): add set_non_cr_state, update path helpers, rename delete_drone"
```

---

## Task 8: Bridge & App Web — Adapters, Protocols, Create Project Types

**Files:**
- Modify: `web/js_api.py` (protocols)
- Modify: `app_web.py` (adapters)
- Test: `tests/test_create_project_types.py` (bridge layer)

**Interfaces:**
- Consumes: all previous tasks
- Produces: `AppCodeServiceProtocol` in js_api; `_AppCodeServiceAdapter` in app_web; updated `create_project` with `appcode`+`project_type`+`drone_name`; appcode-scoped year methods; `list_drones`/`create_drone`/`delete_drone` (renamed); `set_non_cr_state` bridge method

- [ ] **Step 1: Write the failing test**

```python
# tests/test_create_project_types.py
import json
from pathlib import Path

def test_create_cr_only_project(tmp_path):
    from app_web import create_js_api
    # Setup: root with appcode + year structure
    root = tmp_path / "WORK"
    appcode = root / "MYAPP"
    appcode.mkdir(parents=True)
    (appcode / "appcode.json").write_text(json.dumps({"display_name": "MYAPP"}), encoding="utf-8")
    (appcode / "2026" / "CR" / "UAT_PREPARE").mkdir(parents=True)
    (appcode / "2026" / "Non-CR").mkdir(parents=True)
    # Configure settings
    from infrastructure.settings_store import SettingsStore
    store = SettingsStore(config_dir=tmp_path / "config")
    store.write(type(store.read())(root_folder=root))
    api = create_js_api(settings_store=store)
    result = api.create_project({
        "project_name": "TestCR",
        "year": "2026",
        "appcode": "MYAPP",
        "project_type": "CR",
    })
    assert result["ok"] is True
    project_path = Path(result["data"]["project_path"])
    assert project_path.is_dir()
    assert (project_path / "project_data.json").is_file()
    assert (project_path / "notes.md").is_file()
    assert (project_path / "_cr-docs").is_dir()

def test_create_cr_with_drone_project(tmp_path):
    # Similar setup, project_type=CR, drone_name="api"
    # Assert drone folder + UAT/ + PRD/ + notes.md exist
    ...

def test_create_non_cr_project(tmp_path):
    # project_type=NON_CR
    # Assert Non-CR path, project_data.json has non_cr_state=PLANNING, no _cr-docs
    ...
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_create_project_types.py -v`
Expected: FAIL — `create_project` does not accept `appcode`/`project_type`

- [ ] **Step 3: Write minimal implementation**

In `web/js_api.py`, add new protocol:

```python
class AppCodeServiceProtocol(Protocol):
    def list_appcodes(self) -> object: ...
    def add_appcode(self, name: str) -> object: ...
    def remove_appcode(self, name: str) -> object: ...
    def get_appcode_config(self, appcode: str) -> object: ...
    def update_appcode_config(self, appcode: str, data: dict) -> object: ...
```

Rename in `ProjectServiceProtocol`: `list_subprojects`->`list_drones`, `create_subproject`->`create_drone`, `delete_subproject`->`delete_drone`. Add `set_non_cr_state(self, project_path: Path, target_state: str) -> object`.

Update `YearServiceProtocol`: `list_years(self, appcode: str) -> object`, `create_year(self, appcode: str, year: str) -> object`.

In `app_web.py`, update `create_project` (around line 752):

```python
def create_project(self, data: dict[str, object]) -> object:
    name = str(data.get("project_name", "")).strip()
    if not name:
        raise ValueError("Project name is required")
    validate_windows_folder_name(name)
    year = str(data.get("year", "")).strip() or str(local_now().year)
    appcode_name = str(data.get("appcode", "")).strip()
    project_type = ProjectType(data.get("project_type", "CR"))
    drone_name = str(data.get("drone_name", "")).strip()
    settings = _settings_store.read()
    if settings.root_folder is None:
        raise ValueError("Root folder is not configured")
    appcode_path = settings.root_folder / appcode_name
    year_path = appcode_path / year

    if project_type == ProjectType.CR:
        project_dir = year_path / "CR" / "UAT_PREPARE" / name
        if project_dir.exists():
            raise ValueError(f"Project folder already exists: {project_dir}")
        project_dir.mkdir(parents=True)
        now = local_now()
        metadata = ProjectMetadata(project_name=name, project_type=ProjectType.CR, created_at=now, updated_at=now)
        self._metadata_store.write(project_dir, metadata)
        (project_dir / "notes.md").touch()
        (project_dir / "_cr-docs").mkdir()
        if drone_name:
            _scaffold_drone(project_dir, drone_name)
            metadata.drone_tickets.append(DroneTicket(subfolder_name=drone_name))
            self._metadata_store.write(project_dir, metadata)
        return {"project_path": str(project_dir), "project_name": name, "project_state": "UAT_PREPARE", "project_type": "CR"}

    elif project_type == ProjectType.NON_CR:
        project_dir = year_path / "Non-CR" / name
        if project_dir.exists():
            raise ValueError(f"Project folder already exists: {project_dir}")
        project_dir.mkdir(parents=True)
        now = local_now()
        metadata = ProjectMetadata(project_name=name, project_type=ProjectType.NON_CR, non_cr_state=NonCrState.PLANNING, created_at=now, updated_at=now)
        self._metadata_store.write(project_dir, metadata)
        (project_dir / "notes.md").touch()
        return {"project_path": str(project_dir), "project_name": name, "project_type": "NON_CR", "non_cr_state": "PLANNING"}
```

Update `_YearServiceAdapter.list_years` and `create_year` to be appcode-scoped.

Add `_AppCodeServiceAdapter` class with `list_appcodes`, `add_appcode`, `remove_appcode`, `get_appcode_config`, `update_appcode_config`.

Rename `create_subproject` to `create_drone` (uses `_scaffold_drone`). Rename `delete_subproject` to `delete_drone`.

Add `set_non_cr_state` bridge method that calls `ProjectService.set_non_cr_state`.

Update `_rebuild_cache_for` to use new path depth and `rebuild_appcode_year_cache`.

- [ ] **Step 4: Run test to verify it passes**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_create_project_types.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add web/js_api.py app_web.py tests/test_create_project_types.py
git commit -m "feat(bridge): add appcode adapters, project type creation, drone rename, non-cr state"
```
---

## Task 9: Dashboard Service — DTO Updates + Appcode Filter

**Files:**
- Modify: `services/dashboard_service.py`
- Test: `tests/test_phase_c_dashboard_service.py` (update existing)

**Interfaces:**
- Consumes: `CachedProjectRow` new fields from Task 6
- Produces: `DashboardProject` with `appcode`, `project_type`, `non_cr_state`, `drones` (renamed from `subprojects`); `DashboardSummary` with `by_project_type`; `list_projects(year, appcode)`

- [ ] **Step 1: Write the failing test**

```python
# Add to tests/test_phase_c_dashboard_service.py
from core.enums import ProjectType, NonCrState

def test_dashboard_project_has_appcode_and_type():
    row = CachedProjectRow(
        project_path=Path("D:/WORK/MYAPP/2026/CR/UAT_PREPARE/Test"),
        year="2026", project_state=ProjectState.UAT_PREPARE, project_name="Test",
        appcode="MYAPP", project_type=ProjectType.CR, non_cr_state=None,
    )
    result = _dashboard_project_from_cache_row(row)
    assert result.appcode == "MYAPP"
    assert result.project_type == ProjectType.CR
    assert result.non_cr_state is None
    assert result.drones == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_c_dashboard_service.py -v -k "appcode_and_type"`
Expected: FAIL — `DashboardProject` has no `appcode` field

- [ ] **Step 3: Write minimal implementation**

In `services/dashboard_service.py`:

Add imports: `from core.enums import CRState, DroneState, NonCrState, ProjectState, ProjectType`

Add fields to `DashboardProject` (after `scanned_at`):
```python
    appcode: str = ""
    project_type: ProjectType = ProjectType.CR
    non_cr_state: NonCrState | None = None
    drones: tuple[str, ...] = ()
```
Remove `subprojects` field.

Add `by_project_type` to `DashboardSummary`:
```python
    by_project_type: Mapping[str, int]
```

Update `_dashboard_project_from_cache_row` to map new fields:
```python
    appcode=row.appcode,
    project_type=row.project_type,
    non_cr_state=row.non_cr_state,
    drones=_drones_from_json(row.drone_paths_json),
```

Rename `_subprojects_from_json` to `_drones_from_json` (same logic, reads `drone_paths_json`).

Update `list_projects` to pass appcode:
```python
def list_projects(self, year: str | None = None, appcode: str | None = None) -> list[DashboardProject]:
    return [_dashboard_project_from_cache_row(row) for row in self.cache.list_projects(year, appcode)]
```

Update `_summary_from_projects` to add `by_project_type` count.

- [ ] **Step 4: Run test to verify it passes**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/test_phase_c_dashboard_service.py -v -k "appcode_and_type"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/dashboard_service.py tests/test_phase_c_dashboard_service.py
git commit -m "feat(dashboard): add appcode/project_type/non_cr_state to DashboardProject, rename drones"
```

---

## Task 10: Frontend — Types, DroneTable Rename, Appcode Selector, Project Form

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Rename: `frontend/src/lib/components/SubProjectTable.svelte` -> `DroneTable.svelte`
- Modify: `frontend/src/lib/components/ProjectDetails.svelte`
- Modify: `frontend/src/lib/components/Dashboard.svelte`
- Modify: `frontend/src/lib/components/ProjectActions.svelte`
- Modify: `frontend/src/lib/components/NewProjectForm.svelte`
- Modify: `frontend/src/lib/bridge.ts`
- Modify: `frontend/src/lib/folderLocks.ts`

**Interfaces:**
- Consumes: new bridge methods from Task 8, new DTO shapes from Task 9
- Produces: Updated TS types, DroneTable component, appcode selector in Dashboard, project-type dropdown in form

- [ ] **Step 1: Update TS types**

In `frontend/src/lib/types.ts`, update `DashboardProject` (around line 63):

```typescript
export interface DashboardProject {
  project_path: string;
  year: string;
  project_name: string;
  project_state: string;
  appcode: string;                          // NEW
  project_type: "CR" | "NON_CR";            // NEW
  non_cr_state: "PLANNING" | "IN_PROGRESS" | "DONE" | null;  // NEW
  cr_number: string | null;
  cr_link: string;
  cr_state: string;
  cr_pending_approval_at: string | null;
  start_datetime: string | null;
  end_datetime: string | null;
  t10_status: string;
  drone_ticket_count: number;
  drones: string[];                         // RENAMED from subprojects
  updated_at: string | null;
  scanned_at: string | null;
  drone_tickets: DashboardRowDrone[];
}
```

Update `ProjectDetail` (around line 120):
```typescript
export interface ProjectDetail {
  project_name: string;
  project_path: string;
  project_state: string;
  appcode: string;                          // NEW
  project_type: "CR" | "NON_CR";            // NEW
  non_cr_state: "PLANNING" | "IN_PROGRESS" | "DONE" | null;  // NEW
  cr_number: string;
  cr_link: string;
  cr_state: string;
  start_datetime: string | null;
  end_datetime: string | null;
  t10_status: string;
  drone_ticket_count: number;
  drone_tickets: DroneTicket[];
  implementation_plan?: string | null;
  history?: HistoryEntry[];
  drones: string[];                         // RENAMED from subprojects
  drone_paths: string[];                    // NEW
}
```

Add new `AppCode` interface:
```typescript
export interface AppCode {
  name: string;
  path: string;
  display_name: string;
  cicd_location: "per_appcode" | "shared_root";
  cicd_shared_path: string | null;
}
```

Remove `is_subproject` from `ProjectDetail`.

- [ ] **Step 2: Rename SubProjectTable.svelte -> DroneTable.svelte**

Rename the file. Update props: `subprojects` -> `drones`. Update all internal references from "subproject" to "drone".

- [ ] **Step 3: Update bridge.ts**

Add appcode method wrappers. Rename `list_subprojects`/`create_subproject`/`delete_subproject` to `list_drones`/`create_drone`/`delete_drone`. Add `set_non_cr_state`, `list_appcodes`, `add_appcode`, `remove_appcode`. Update `list_projects` to accept appcode param. Update `list_years`/`create_year` to accept appcode param.

- [ ] **Step 4: Update folderLocks.ts**

Rename `create_subproject` -> `create_drone`, `delete_subproject` -> `delete_drone` in the action list.

- [ ] **Step 5: Update ProjectDetails.svelte**

Import `DroneTable` instead of `SubProjectTable`. Change `subprojects` prop to `drones`. Add conditional rendering: for Non-CR projects, show a Non-CR state dropdown (Planning/In Progress/Done) instead of CR/Drone sections. Replace all "Sub Project" labels with "Drone".

- [ ] **Step 6: Update Dashboard.svelte**

Add appcode selector (dropdown of available appcodes). Pass `appcode` to `list_projects`. Update `subprojects` references to `drones`. For Non-CR rows, render `non_cr_state` badge instead of `cr_state`/`project_state`.

- [ ] **Step 7: Update NewProjectForm.svelte**

Add project-type dropdown (CR only / CR with drone / Non-CR). Add appcode selector. When "CR with drone" is selected, show a drone name input field. When "Non-CR" is selected, hide CR/Drone fields.

- [ ] **Step 8: Update ProjectActions.svelte**

Rename `onSubprojectsChanged` to `onDronesChanged`.

- [ ] **Step 9: Run frontend build**

Run: `npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run build`
Expected: build succeeds with no errors (pre-existing a11y warnings OK)

- [ ] **Step 10: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/components/DroneTable.svelte frontend/src/lib/components/ProjectDetails.svelte frontend/src/lib/components/Dashboard.svelte frontend/src/lib/components/ProjectActions.svelte frontend/src/lib/components/NewProjectForm.svelte frontend/src/lib/bridge.ts frontend/src/lib/folderLocks.ts
git rm frontend/src/lib/components/SubProjectTable.svelte
git commit -m "feat(frontend): rename to DroneTable, add appcode selector, project-type dropdown, Non-CR rendering"
```

---

## Task 11: Update Existing Tests — Path Depth + Drone Rename

**Files:**
- Modify: ~20 existing test files (update path scaffolds + rename subproject->drone)

**Interfaces:**
- Consumes: all previous tasks
- Produces: all existing tests passing with new structure

- [ ] **Step 1: Update path scaffolds in test helpers**

In each test file that creates projects with `root / year / state / name`, change to `root / appcode / year / "CR" / state / name`. Add an appcode folder with `appcode.json`.

Key files to update (path scaffold pattern: `root / "2026" / ProjectState.UAT_PREPARE.value / "PROJECT"` -> `root / "MYAPP" / "2026" / "CR" / ProjectState.UAT_PREPARE.value / "PROJECT"`):

- `tests/test_phase_b_stores.py` — `root_folder = tmp_path / "CR"` -> appcode structure
- `tests/test_phase_b_cache_mapping.py` — update `cached_project_row_from_scan` usage
- `tests/test_phase_b_cache_rebuild.py` — `rebuild_year_cache` -> `rebuild_appcode_year_cache`
- `tests/test_phase_c_js_api_subproject_file_notes.py` — rename to `test_phase_c_js_api_drone_file_notes.py`; `list_subprojects` -> `list_drones`, `create_subproject` -> `create_drone`
- `tests/test_phase_c_js_api_project.py` — `create_project` data includes `appcode` + `project_type`
- `tests/test_phase_c_js_api_project_mutations.py` — same
- `tests/test_project_rename_delete.py` — path scaffold + `delete_subproject` -> `delete_drone`
- `tests/test_project_service_reopen.py` — path scaffold
- `tests/test_project_transitions_unit.py` — path scaffold
- `tests/test_project_transitions_property.py` — path scaffold
- `tests/test_project_file_operations.py` — path scaffold
- `tests/test_year_create.py` — `create_year` now appcode-scoped
- `tests/test_phase_e_cr_state_guarded.py` — path scaffold
- `tests/test_phase_f_drone_state_guarded.py` — path scaffold
- `tests/test_phase_g_project_create_update.py` — `create_project` new params
- `tests/test_app_web_dashboard_auto_move.py` — path scaffold + `_rebuild_cache_for` depth
- `tests/test_phase_d_app_web_project_details_read_wiring.py` — `subproject_list` -> `drone_list`
- `tests/test_phase_d_app_web_project_service_adapter.py` — path scaffold + new params

Frontend tests:
- `frontend/tests/components.test.mjs` — `SubProjectTable` -> `DroneTable`
- `frontend/tests/project-details-fase3-fase4.test.mjs` — "sub-projects" -> "drones"
- `frontend/tests/project-actions.test.mjs` — `onSubprojectsChanged` -> `onDronesChanged`

- [ ] **Step 2: Run full test suite**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m pytest tests/ -v`
Expected: All tests PASS (some may need individual fixes for renamed methods)

- [ ] **Step 3: Run frontend build + check**

Run: `npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run build && npm --prefix D:/Ibrahim/Projects/project_tracker/frontend run check`
Expected: 0 errors (pre-existing a11y warnings OK)

- [ ] **Step 4: Run app for verification**

Run: `D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main`
Expected: app starts, no traceback

- [ ] **Step 5: Commit**

```bash
git add tests/ frontend/tests/
git commit -m "test: update all existing tests for appcode path depth + drone rename"
```

---

## Task 12: Documentation Update — PRD, Architecture, Decisions, Progress

**Files:**
- Modify: `PRD.md` (Section 7 rewrite + Section 9/11/12/21 updates)
- Modify: `_docs/ARCHITECTURE.md`
- Modify: `_docs/DECISIONS.md` (add D-0008)
- Modify: `_docs/FILE_ROUTING.md`
- Modify: `_docs/DESIGN_RULES.md`
- Modify: `_docs/PROGRESS.md`
- Modify: `_docs/session-notes.md`
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: completed implementation from Tasks 1-11
- Produces: all docs reflecting the new structure

- [ ] **Step 1: Rewrite PRD.md Section 7 (Filesystem Model)**

Update Section 7 to reflect the new tree: `root/appcode/year/CR/STATE/project/_cr-docs + drone/UAT/PRD` + `root/appcode/year/Non-CR/project`. Add Section 7.7 (Non-CR projects), 7.8 (Appcode folders), 7.9 (CICD folder). Rename all "Sub Project" to "Drone". Add `_cr-docs` to exclusion list in 7.6.

- [ ] **Step 2: Update PRD.md other sections**

- Section 9 (State): add Non-CR state machine (Planning/In Progress/Done)
- Section 11 (Dashboard): add appcode filter; Non-CR row rendering
- Section 12 (Project Details): Add Project dropdown (3 types); Sub Project -> Drone; Non-CR state dropdown
- Section 21 (JsApi): new appcode methods; renamed drone methods; set_non_cr_state

- [ ] **Step 3: Update _docs/ARCHITECTURE.md**

Persistence Model table: add appcode row, project_type row; rename Sub project -> Drone; update "Project year" description (parent is now `appcode/year`).

- [ ] **Step 4: Add D-0008 to _docs/DECISIONS.md**

```markdown
| D-0008 | 2026-07-01 | Appcode-based folder structure with CR/Non-CR project types. Sub project renamed to Drone. State folders relocated inside CR. Non-CR projects use metadata-only state (Planning/In Progress/Done). | User new workflow requirement. Greenfield — no migration needed. | LOCKED |
```

- [ ] **Step 5: Update remaining docs**

- `_docs/FILE_ROUTING.md`: note `_cr-docs/` as runtime data folder inside project folders
- `_docs/DESIGN_RULES.md`: `SubProjectTable` -> `DroneTable`; add Non-CR state dropdown styling note
- `_docs/PROGRESS.md`: add new active slice "Appcode folder structure + CR/Non-CR project types"
- `_docs/session-notes.md`: update Now/Next/Blocked
- `CLAUDE.md`: note PRD Section 7 rewrite in Documentation Sync section

- [ ] **Step 6: Commit**

```bash
git add PRD.md _docs/ARCHITECTURE.md _docs/DECISIONS.md _docs/FILE_ROUTING.md _docs/DESIGN_RULES.md _docs/PROGRESS.md _docs/session-notes.md CLAUDE.md
git commit -m "docs: update PRD, architecture, decisions, progress for appcode structure [D-0008]"
```

---

## Self-Review

**Spec coverage check:**
- Section 1 (Folder Structure): Task 4 (path helpers, scaffolding), Task 5 (scanner), Task 8 (creation)
- Section 2 (Domain Model): Task 1 (enums), Task 2 (models)
- Section 3 (Scanner & Filesystem): Task 4, Task 5, Task 6 (cache)
- Section 4 (Project Creation): Task 4 (_scaffold_drone), Task 8 (create_project)
- Section 5 (Non-CR State Machine): Task 3, Task 7
- Section 6 (Bridge & Frontend DTOs): Task 8, Task 9, Task 10
- Section 7 (Error Handling): covered in Tasks 4-8 (guards, validation, edge cases in tests)
- Section 8 (Testing + References): Task 11 (existing tests), Task 12 (docs)
- Success criteria 1-12: all mapped to tasks

**Placeholder scan:** No TBD/TODO found. All steps contain actual code.

**Type consistency:** `ProjectType`, `NonCrState`, `AppCodeConfig`, `ScannedProject`, `discover_drone_paths`, `_scaffold_drone`, `scan_appcode_year`, `set_non_cr_state`, `list_drones`, `create_drone`, `delete_drone` — names consistent across all tasks.