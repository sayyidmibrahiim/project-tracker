# Dashboard Auto-Move + Gap-Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make inline Dashboard CR/Drone state changes drive real folder transitions (auto-move), replace the T-10 hard guard with a non-blocking H-10 reminder, add the G1 "CR APPROVED requires all drones APPROVED" guard, and close five small Dashboard display gaps.

**Architecture:** A new pure core function `resolve_auto_move` decides the target folder state from CR/drone state. Orchestration (calling existing tested `ProjectService` move methods, writing history, emitting notifications, pushing EventQueue events) lives in the `AppAPI` adapter layer in `app_web.py`. Core stays I/O-free. Reuses already-tested move methods (`move_to_prod_ready`, `move_to_implemented`, `postpone_project`, `cancel_project`) — this is wiring + one evaluator, not greenfield.

**Tech Stack:** Python 3.12 (core + services + adapter), pytest, Svelte 5 + TypeScript + Vite (frontend), Tailwind. Datetimes ISO-8601 timezone-aware via `local_now()`.

**Spec:** `docs/superpowers/specs/2026-06-10-dashboard-auto-move-design.md` (approved).

---

## File Structure

**Backend (Python):**

- `project_tracker/core/state_machine.py` — add pure `resolve_auto_move()`. Reuses `target_project_state_for_cr_state()`, `PROJECT_STATE_TRANSITIONS`.
- `project_tracker/core/rules.py` — remove T-10 from `validate_uat_to_prod_ready_transition` failed_guards; add `compute_h10()` + `h10_reminder_due()` helpers; add `validate_cr_approved_requires_drones()` (G1).
- `project_tracker/core/models.py` — add `h10_notified_at` field to `ProjectMetadata`; add `h10_reminder_days` field to `AppSettings`.
- `project_tracker/app_web.py` (AppAPI) — wire auto-move into `update_cr_state`/`update_drone`; route POSTPONED/CANCELED through move methods; add history + notification + `push_event` on every move; enforce G1 in `update_cr_state`; H-10 evaluation on dashboard load.
- `project_tracker/services/notification_service.py` — no change (reuse `.add()`).
- `project_tracker/web/event_queue.py` — no change (reuse `push_event`).

**Frontend (Svelte/TS):**

- `frontend/src/lib/components/Dashboard.svelte` — G1 inline error display; extracted-ID beside link cells (A4); semantic state color chips (C2); per-cell saving spinner (C4); long-name ellipsis + tooltip (B4); zero-year "Add Year" empty-state (B3).

**Tests:**

- `tests/test_core_state_machine.py` — `resolve_auto_move` all rows + no-op.
- `tests/test_core_rules.py` — H-10 helpers, G1 guard, T-10 removal from prod-ready guard.
- `tests/test_app_web_dashboard_auto_move.py` (new) — adapter wiring: auto-move on state persist, routed postpone/cancel, history, notification, event push, G1 rejection, H-10 fire-once/dedup/re-arm.
- `frontend/tests/dashboard.test.ts` (extend existing) — G1 inline error, extracted-ID render, color chips.

---

## Task 1: Pure `resolve_auto_move` evaluator (core)

**Files:**

- Modify: `project_tracker/core/state_machine.py` (append after `target_project_state_for_cr_state`, ~L139)
- Test: `tests/test_core_state_machine.py`

Context: `target_project_state_for_cr_state(cr_state)` already maps APPROVED→PROD_READY, FINISHED→IMPLEMENTED, POSTPONED→POSTPONED, CANCELED→CANCELED, else None. `PROJECT_STATE_TRANSITIONS` defines legal folder transitions. `resolve_auto_move` adds the no-op rules (target==current, IMPLEMENTED terminal, illegal transition) on top.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_core_state_machine.py — append
from project_tracker.core.enums import CRState, DroneState, ProjectState
from project_tracker.core.state_machine import resolve_auto_move


def test_resolve_auto_move_approved_uat_to_prod_ready():
    assert resolve_auto_move(
        CRState.APPROVED, [DroneState.APPROVED], ProjectState.UAT_PREPARE
    ) == ProjectState.PROD_READY


def test_resolve_auto_move_approved_no_drones():
    assert resolve_auto_move(
        CRState.APPROVED, [], ProjectState.UAT_PREPARE
    ) == ProjectState.PROD_READY


def test_resolve_auto_move_finished_prod_ready_to_implemented():
    assert resolve_auto_move(
        CRState.FINISHED, [DroneState.FINISHED], ProjectState.PROD_READY
    ) == ProjectState.IMPLEMENTED


def test_resolve_auto_move_postponed_from_uat():
    assert resolve_auto_move(
        CRState.POSTPONED, [], ProjectState.UAT_PREPARE
    ) == ProjectState.POSTPONED


def test_resolve_auto_move_canceled_from_prod_ready():
    assert resolve_auto_move(
        CRState.CANCELED, [], ProjectState.PROD_READY
    ) == ProjectState.CANCELED


def test_resolve_auto_move_noop_target_equals_current():
    # CR APPROVED but already in PROD_READY -> no move
    assert resolve_auto_move(
        CRState.APPROVED, [], ProjectState.PROD_READY
    ) is None


def test_resolve_auto_move_noop_terminal_implemented():
    # IMPLEMENTED folder is locked; never auto-moves
    assert resolve_auto_move(
        CRState.CANCELED, [], ProjectState.IMPLEMENTED
    ) is None


def test_resolve_auto_move_noop_illegal_transition():
    # FINISHED -> IMPLEMENTED is illegal from UAT_PREPARE (must pass PROD_READY)
    assert resolve_auto_move(
        CRState.FINISHED, [], ProjectState.UAT_PREPARE
    ) is None


def test_resolve_auto_move_noop_cr_state_with_no_mapping():
    assert resolve_auto_move(
        CRState.IN_PROGRESS, [], ProjectState.PROD_READY
    ) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_core_state_machine.py -k resolve_auto_move -v`
Expected: FAIL — `ImportError: cannot import name 'resolve_auto_move'`

- [ ] **Step 3: Implement `resolve_auto_move`**

```python
# project_tracker/core/state_machine.py — append after target_project_state_for_cr_state (~L139)
def resolve_auto_move(
    cr_state: CRState,
    drone_states: list[DroneState],
    current_folder: ProjectState,
) -> ProjectState | None:
    """Decide the target folder state for an inline CR state change.

    Pure; no I/O. Returns the target ProjectState, or None for a no-op.
    Drone preconditions (G1, FINISHED cascade) are enforced by callers /
    structural guards, not here — this only decides the target folder.
    """
    target = target_project_state_for_cr_state(cr_state)
    if target is None:
        return None
    if current_folder == ProjectState.IMPLEMENTED:
        return None
    if target == current_folder:
        return None
    if not can_transition_project_state(current_folder, target):
        return None
    return target
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_core_state_machine.py -k resolve_auto_move -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
rtk git add project_tracker/core/state_machine.py tests/test_core_state_machine.py
rtk git commit -m "feat(core): add resolve_auto_move evaluator for dashboard auto-move"
```

## Task 2: G1 guard — CR APPROVED requires all drones APPROVED (core)

**Files:**

- Modify: `project_tracker/core/rules.py` (append helper near other validators, ~after L232)
- Test: `tests/test_core_rules.py`

Context: G1 mirrors the office CR web portal — a project with ≥1 drone ticket cannot set CR to APPROVED until all drone states are APPROVED. No drones → APPROVED allowed. This makes auto-move to PROD_READY deterministic. Returns a `TransitionGuardResult` (already defined in `rules.py` L46, fields `allowed: bool`, `failed_guards: list[str]`).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_core_rules.py — append
from project_tracker.core.enums import DroneState
from project_tracker.core.models import DroneTicket
from project_tracker.core.rules import validate_cr_approved_requires_drones


def _drone(state: DroneState) -> DroneTicket:
    return DroneTicket(drone_link="https://drone/x", drone_state=state)


def test_g1_no_drones_allows_approved():
    result = validate_cr_approved_requires_drones([])
    assert result.allowed is True
    assert result.failed_guards == []


def test_g1_all_drones_approved_allows():
    result = validate_cr_approved_requires_drones(
        [_drone(DroneState.APPROVED), _drone(DroneState.APPROVED)]
    )
    assert result.allowed is True


def test_g1_one_drone_not_approved_blocks():
    result = validate_cr_approved_requires_drones(
        [_drone(DroneState.APPROVED), _drone(DroneState.IN_PROGRESS)]
    )
    assert result.allowed is False
    assert "1 drone" in result.failed_guards[0]


def test_g1_multiple_not_approved_counts():
    result = validate_cr_approved_requires_drones(
        [_drone(DroneState.UAT), _drone(DroneState.PENDING_APPROVAL)]
    )
    assert result.allowed is False
    assert "2 drone" in result.failed_guards[0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_core_rules.py -k g1 -v`
Expected: FAIL — `ImportError: cannot import name 'validate_cr_approved_requires_drones'`

- [ ] **Step 3: Implement the guard**

```python
# project_tracker/core/rules.py — append after validate_prod_ready_to_implemented_transition (~L232)
def validate_cr_approved_requires_drones(
    drone_tickets: list[DroneTicket],
) -> TransitionGuardResult:
    """G1: CR cannot become APPROVED while any drone is not APPROVED.

    No drones -> allowed. This keeps the auto-move to PROD_READY deterministic:
    when CR reaches APPROVED, every drone is already APPROVED.
    """
    not_approved = [
        t for t in drone_tickets if t.drone_state != DroneState.APPROVED
    ]
    if not not_approved:
        return TransitionGuardResult(allowed=True, failed_guards=[])
    count = len(not_approved)
    return TransitionGuardResult(
        allowed=False,
        failed_guards=[
            f"CR cannot be APPROVED — {count} drone(s) not yet APPROVED."
        ],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_core_rules.py -k g1 -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
rtk git add project_tracker/core/rules.py tests/test_core_rules.py
rtk git commit -m "feat(core): add G1 guard - CR APPROVED requires all drones APPROVED"
```

## Task 3: Add `h10_notified_at` (metadata) + `h10_reminder_days` (settings)

**Files:**

- Modify: `project_tracker/core/models.py` — `ProjectMetadata` (~L129-175) and `AppSettings` (~L464-512)
- Test: `tests/test_core_models.py` (extend; create if absent)

Context: H-10 reminder needs a dedup stamp (`h10_notified_at`) on metadata and a configurable threshold (`h10_reminder_days`, default 10) on settings. Both must round-trip through `from_dict`/`to_dict`. `datetime_from_json`/`datetime_to_json` already exist in `models.py`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_core_models.py — append
from project_tracker.core.models import AppSettings, ProjectMetadata


def test_metadata_h10_notified_at_roundtrip():
    md = ProjectMetadata(project_name="X")
    assert md.h10_notified_at is None
    data = md.to_dict()
    assert "h10_notified_at" in data
    restored = ProjectMetadata.from_dict(data)
    assert restored.h10_notified_at is None


def test_settings_h10_reminder_days_default_and_roundtrip():
    s = AppSettings()
    assert s.h10_reminder_days == 10
    data = s.to_dict()
    assert data["h10_reminder_days"] == 10
    restored = AppSettings.from_dict({**data, "h10_reminder_days": 7})
    assert restored.h10_reminder_days == 7
```

- [ ] **Step 2: Run to verify fail**

Run: `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_core_models.py -k h10 -v`
Expected: FAIL — `AttributeError: ... has no attribute 'h10_notified_at'` / `h10_reminder_days`

- [ ] **Step 3a: Add `h10_notified_at` to `ProjectMetadata`**

In the dataclass field block (after `updated_at: datetime | None = None`, ~L142):

```python
    h10_notified_at: datetime | None = None
```

In `from_dict` (after the `updated_at=...` line):

```python
            h10_notified_at=datetime_from_json(data.get("h10_notified_at")),
```

In `to_dict` (after the `"updated_at": ...` line):

```python
            "h10_notified_at": datetime_to_json(self.h10_notified_at),
```

- [ ] **Step 3b: Add `h10_reminder_days` to `AppSettings`**

In the dataclass field block (after `t10_threshold_days: int = 10`, ~L469):

```python
    h10_reminder_days: int = 10
```

In `from_dict` (after `t10_threshold_days=int(...)`):

```python
            h10_reminder_days=int(data.get("h10_reminder_days", 10)),
```

In `to_dict` (after `"t10_threshold_days": ...`):

```python
            "h10_reminder_days": self.h10_reminder_days,
```

- [ ] **Step 4: Run to verify pass**

Run: `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_core_models.py -k h10 -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
rtk git add project_tracker/core/models.py tests/test_core_models.py
rtk git commit -m "feat(models): add h10_notified_at metadata + h10_reminder_days setting"
```

## Task 4: H-10 reminder helpers (core)

**Files:**

- Modify: `project_tracker/core/rules.py` (append helpers, ~after Task 2 guard)
- Test: `tests/test_core_rules.py`

Context: H-10 = `start_datetime − h10_reminder_days`. The reminder is due when `now >= H-10` AND (CR != APPROVED OR any drone != APPROVED). It NEVER blocks any transition — it only signals that a notification + history note should be emitted. The adapter layer (Task 7) owns dedup via `h10_notified_at`; these helpers are pure.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_core_rules.py — append
from datetime import datetime, timedelta, timezone
from project_tracker.core.enums import CRState, DroneState
from project_tracker.core.models import DroneTicket, ProjectMetadata
from project_tracker.core.rules import compute_h10, h10_reminder_due

TZ = timezone(timedelta(hours=7))


def _md(start, cr_state, drones=None):
    return ProjectMetadata(
        project_name="X",
        start_datetime=start,
        cr_state=cr_state,
        drone_tickets=drones or [],
    )


def test_compute_h10_none_when_no_start():
    assert compute_h10(_md(None, CRState.PENDING_APPROVAL), reminder_days=10) is None


def test_compute_h10_subtracts_days():
    start = datetime(2026, 6, 20, 9, 0, tzinfo=TZ)
    assert compute_h10(_md(start, CRState.PENDING_APPROVAL), reminder_days=10) == datetime(
        2026, 6, 10, 9, 0, tzinfo=TZ
    )


def test_h10_due_when_past_and_cr_not_approved():
    start = datetime(2026, 6, 15, 9, 0, tzinfo=TZ)  # H-10 = Jun 5
    now = datetime(2026, 6, 10, 9, 0, tzinfo=TZ)
    assert h10_reminder_due(_md(start, CRState.PENDING_APPROVAL), now=now, reminder_days=10) is True


def test_h10_not_due_before_h10():
    start = datetime(2026, 6, 30, 9, 0, tzinfo=TZ)  # H-10 = Jun 20
    now = datetime(2026, 6, 10, 9, 0, tzinfo=TZ)
    assert h10_reminder_due(_md(start, CRState.PENDING_APPROVAL), now=now, reminder_days=10) is False


def test_h10_not_due_when_cr_and_drones_approved():
    start = datetime(2026, 6, 15, 9, 0, tzinfo=TZ)
    now = datetime(2026, 6, 10, 9, 0, tzinfo=TZ)
    md = _md(start, CRState.APPROVED, [DroneTicket(drone_link="x", drone_state=DroneState.APPROVED)])
    assert h10_reminder_due(md, now=now, reminder_days=10) is False


def test_h10_due_when_cr_approved_but_drone_not():
    start = datetime(2026, 6, 15, 9, 0, tzinfo=TZ)
    now = datetime(2026, 6, 10, 9, 0, tzinfo=TZ)
    md = _md(start, CRState.APPROVED, [DroneTicket(drone_link="x", drone_state=DroneState.UAT)])
    assert h10_reminder_due(md, now=now, reminder_days=10) is True


def test_h10_not_due_when_no_start():
    now = datetime(2026, 6, 10, 9, 0, tzinfo=TZ)
    assert h10_reminder_due(_md(None, CRState.PENDING_APPROVAL), now=now, reminder_days=10) is False
```

- [ ] **Step 2: Run to verify fail**

Run: `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_core_rules.py -k h10 -v`
Expected: FAIL — `ImportError: cannot import name 'compute_h10'`

- [ ] **Step 3: Implement helpers**

```python
# project_tracker/core/rules.py — append after validate_cr_approved_requires_drones
def compute_h10(metadata: ProjectMetadata, *, reminder_days: int) -> datetime | None:
    """H-10 = start_datetime - reminder_days. None when no start date."""
    if metadata.start_datetime is None:
        return None
    return metadata.start_datetime - timedelta(days=reminder_days)


def h10_reminder_due(
    metadata: ProjectMetadata, *, now: datetime, reminder_days: int
) -> bool:
    """True when now >= H-10 AND (CR != APPROVED OR any drone != APPROVED).

    Never blocks a transition; callers use this only to decide whether to
    emit a reminder notification. Dedup is the caller's responsibility.
    """
    h10 = compute_h10(metadata, reminder_days=reminder_days)
    if h10 is None or now < h10:
        return False
    cr_not_approved = metadata.cr_state != CRState.APPROVED
    any_drone_not_approved = any(
        t.drone_state != DroneState.APPROVED for t in metadata.drone_tickets
    )
    return cr_not_approved or any_drone_not_approved
```

Note: ensure `timedelta` is imported at the top of `rules.py` (it imports `datetime` already — add `timedelta` to that import if missing).

- [ ] **Step 4: Run to verify pass**

Run: `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_core_rules.py -k h10 -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
rtk git add project_tracker/core/rules.py tests/test_core_rules.py
rtk git commit -m "feat(core): add H-10 reminder helpers (compute_h10, h10_reminder_due)"
```

## Task 5: Remove T-10 from prod-ready hard guard

**Files:**

- Modify: `project_tracker/core/rules.py` — `validate_uat_to_prod_ready_transition` (~L161-217)
- Test: `tests/test_core_rules.py`

Context: T-10 is reclassified as the non-blocking H-10 reminder (Task 4). The prod-ready transition guard must no longer fail on T-10. All other structural guards (CR link, CR APPROVED, drone links, drone APPROVED, dates present + coherent, timezone-aware) remain. Lines 212-215 currently append the T-10 reason — remove that block. Keep the `threshold_days` parameter for signature compatibility (callers still pass it); it simply goes unused after removal, or remove it in a follow-up. **Decision: keep the parameter, drop the T-10 block**, to avoid touching `move_to_prod_ready` and its `override_t10` path in this task.

- [ ] **Step 1: Write/adjust the failing test**

```python
# tests/test_core_rules.py — append
from datetime import datetime, timedelta, timezone
from project_tracker.core.enums import CRState
from project_tracker.core.models import ProjectMetadata
from project_tracker.core.rules import validate_uat_to_prod_ready_transition

TZ = timezone(timedelta(hours=7))


def test_prod_ready_guard_no_longer_fails_on_t10():
    # Start in 3 days (< 10), CR APPROVED, links + dates valid -> previously T-10 failed,
    # now must be allowed.
    now = datetime(2026, 6, 10, 9, 0, tzinfo=TZ)
    md = ProjectMetadata(
        project_name="X",
        start_datetime=now + timedelta(days=3),
        end_datetime=now + timedelta(days=5),
        cr_link="https://cr/123",
        cr_state=CRState.APPROVED,
    )
    result = validate_uat_to_prod_ready_transition(md, current_time=now, threshold_days=10)
    assert result.allowed is True
    assert all("T-10" not in g for g in result.failed_guards)
```

- [ ] **Step 2: Run to verify fail**

Run: `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_core_rules.py -k t10 -v`
Expected: FAIL — `assert result.allowed is True` fails (T-10 reason present).

- [ ] **Step 3: Remove the T-10 block**

Delete lines ~212-215 in `validate_uat_to_prod_ready_transition`:

```python
    if metadata.start_datetime is None or start_datetime_is_aware:
        t10_result = validate_t10(metadata, threshold_days=threshold_days)
        if not t10_result.passed:
            failed_guards.append(t10_result.reason or "T-10 rule failed")
```

Leave the rest of the function (structural guards) intact. The function still ends with:

```python
    return TransitionGuardResult(allowed=not failed_guards, failed_guards=failed_guards)
```

- [ ] **Step 4: Run to verify pass + check no regressions in existing prod-ready tests**

Run: `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_core_rules.py -v`
Expected: new test PASSES. Existing tests that asserted T-10 _failure_ in this guard will now fail — update them: any test expecting a T-10 reason from `validate_uat_to_prod_ready_transition` should be removed or repointed to `h10_reminder_due`. List them in the commit.

- [ ] **Step 5: Commit**

```bash
rtk git add project_tracker/core/rules.py tests/test_core_rules.py
rtk git commit -m "refactor(core): drop T-10 from prod-ready guard (now non-blocking H-10 reminder)"
```

## Task 6: Shared auto-move helper in AppAPI

**Files:**

- Modify: `project_tracker/app_web.py` (AppAPI inner class, near `_run_transition` ~L800-848)
- Test: `tests/test_app_web_dashboard_auto_move.py` (new)

Context: After an inline CR/drone state persist, the adapter must run `resolve_auto_move` and, if a target is returned, call the matching existing `ProjectService` move method (which does the `shutil.move`, history, cache). Then push an EventQueue event (R3) and emit a notification. This helper centralizes that so `update_cr_state` and `update_drone` both reuse it. AppAPI already holds `self._project_service`, `self._settings_store`, `self._notification_service`, `self._metadata_store`, and `self._rebuild_cache_for`. `push_event(event_type, payload)` is imported from `project_tracker.web.event_queue`.

Mapping target → service method:

- PROD_READY → `move_to_prod_ready(path, settings, local_now(), settings.t10_threshold_days, override_t10=False)`
- IMPLEMENTED → `move_to_implemented(path, settings, local_now())`
- POSTPONED → `postpone_project(path, settings)`
- CANCELED → `cancel_project(path, settings)`

All may return `Path` (success) or `TransitionGuardResult` (blocked). On blocked: do NOT move; surface reason in a non-blocking banner (return it); the state change already persisted.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_app_web_dashboard_auto_move.py — new file
from pathlib import Path
import pytest
from project_tracker.core.enums import CRState, ProjectState

# Use the existing app_web test harness/fixtures. Mirror the setup style of
# the current tests/test_app_web_*.py (temp root, year folder, UAT_PREPARE
# project with metadata). See an existing app_web test for the exact fixture.

def test_auto_move_prod_ready_on_cr_approved(app_api_factory, tmp_uat_project):
    api, paths = app_api_factory(), tmp_uat_project
    # project in UAT_PREPARE, CR PENDING_APPROVAL, no drones
    result = api.cr_update_state(str(paths.project), CRState.APPROVED.value)
    # folder physically moved to PROD_READY
    assert (paths.year / ProjectState.PROD_READY.value / paths.project.name).is_dir()
    assert not paths.project.is_dir()
    # event pushed
    from project_tracker.web.event_queue import drain_events
    evts = drain_events()
    assert any(e["type"] == "AUTO_MOVE" for e in evts)
```

Note: match the real fixture names used in the existing `tests/test_app_web_*.py`. If those tests construct the API inline rather than via a factory fixture, replicate that construction here instead of inventing `app_api_factory`/`tmp_uat_project`. **The implementer must read one existing `tests/test_app_web_*.py` first to copy the setup verbatim.**

- [ ] **Step 2: Run to verify fail**

Run: `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_app_web_dashboard_auto_move.py -v`
Expected: FAIL — auto-move not wired; folder stays in UAT_PREPARE.

- [ ] **Step 3: Implement `_apply_auto_move` helper**

```python
# project_tracker/app_web.py — add inside AppAPI, near _run_transition
def _apply_auto_move(self, project_path: Path) -> dict[str, object] | None:
    """After an inline state persist, move the folder if resolve_auto_move
    returns a target. Returns a banner dict on a blocked structural guard,
    or None when no move / move succeeded."""
    from project_tracker.core.state_machine import resolve_auto_move
    from project_tracker.web.event_queue import push_event

    path = Path(project_path)
    metadata = self._metadata_store.read(path)
    if metadata is None:
        return None
    current_folder = ProjectState(path.parent.name)
    drone_states = [t.drone_state for t in metadata.drone_tickets]
    target = resolve_auto_move(metadata.cr_state, drone_states, current_folder)
    if target is None:
        return None

    settings = self._settings_store.read()
    method_map = {
        ProjectState.PROD_READY: lambda: self._project_service.move_to_prod_ready(
            path, settings, local_now(), settings.t10_threshold_days, override_t10=False
        ),
        ProjectState.IMPLEMENTED: lambda: self._project_service.move_to_implemented(
            path, settings, local_now()
        ),
        ProjectState.POSTPONED: lambda: self._project_service.postpone_project(path, settings),
        ProjectState.CANCELED: lambda: self._project_service.cancel_project(path, settings),
    }
    call = method_map.get(target)
    if call is None:
        return None
    result = call()

    if isinstance(result, TransitionGuardResult) and not result.allowed:
        # state persisted, folder stays; surface non-blocking banner
        return {"banner": "; ".join(result.failed_guards)}

    moved_path = Path(str(result))
    self._rebuild_cache_for(moved_path)
    push_event("AUTO_MOVE", {
        "project_path": str(moved_path),
        "from_state": current_folder.value,
        "to_state": target.value,
    })
    if self._notification_service is not None:
        self._notification_service.add(
            type="AUTO_MOVE",
            title="Project moved",
            message=f"{path.name}: {current_folder.value} → {target.value}",
            project_path=moved_path,
        )
    return None
```

- [ ] **Step 4: Run to verify pass**

Run: `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_app_web_dashboard_auto_move.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add project_tracker/app_web.py tests/test_app_web_dashboard_auto_move.py
rtk git commit -m "feat(adapter): add _apply_auto_move helper (move + event + notification)"
```

## Task 7: Wire G1 + auto-move + history into `update_cr_state` and `update_drone`

**Files:**

- Modify: `project_tracker/app_web.py` — `update_cr_state` (~L716), `update_drone` (~L668), `update_cr_link` (~L629)
- Test: `tests/test_app_web_dashboard_auto_move.py`

Context: Today `update_cr_state` (L716) and `update_drone` (L668) are metadata-only with NO history and NO move. After this task: (1) G1 enforced before persisting APPROVED; (2) a `HistoryEntry` appended on each state change and on link paste; (3) `_apply_auto_move` called after persist; (4) any returned banner surfaced. The inline ConfirmModal for POSTPONED/CANCELED stays on the frontend; backend just routes through the move methods via `_apply_auto_move`.

History append pattern (reuse `HistoryEntry`, `current_user`, `local_now` — all already imported in `app_web.py` or import locally):

```python
metadata.history.append(HistoryEntry(
    timestamp=now, action="CR_STATE_CHANGE",
    detail=f"CR {old.value} → {target.value}", user=current_user(settings),
))
```

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_app_web_dashboard_auto_move.py — append
from project_tracker.core.enums import CRState, DroneState

def test_g1_blocks_cr_approved_with_unapproved_drone(app_api_factory, tmp_uat_project_with_drone):
    api, paths = app_api_factory(), tmp_uat_project_with_drone  # drone in UAT
    with pytest.raises(ValueError) as exc:
        api.cr_update_state(str(paths.project), CRState.APPROVED.value)
    assert "drone" in str(exc.value).lower()
    # folder unchanged
    assert paths.project.is_dir()

def test_cr_state_change_appends_history(app_api_factory, tmp_uat_project):
    api, paths = app_api_factory(), tmp_uat_project
    api.cr_update_state(str(paths.project), CRState.PENDING_APPROVAL.value)
    # read metadata from wherever the project now lives (no move for PENDING_APPROVAL)
    from project_tracker.infrastructure.metadata_store import MetadataStore
    md = MetadataStore().read(paths.project)
    assert any(h.action == "CR_STATE_CHANGE" for h in md.history)

def test_cr_link_paste_appends_history(app_api_factory, tmp_uat_project):
    api, paths = app_api_factory(), tmp_uat_project
    api.cr_update_link(str(paths.project), "https://cr/999")
    from project_tracker.infrastructure.metadata_store import MetadataStore
    md = MetadataStore().read(paths.project)
    assert any(h.action == "CR_LINK" for h in md.history)
```

- [ ] **Step 2: Run to verify fail**

Run: `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_app_web_dashboard_auto_move.py -v`
Expected: FAIL — no G1, no history.

- [ ] **Step 3a: Enforce G1 + history + auto-move in `update_cr_state`**

Replace the body of `update_cr_state` (L716-736) with:

```python
def update_cr_state(self, project_path: Path, cr_state: str) -> object:
    """Update CR state: G1 guard, history, then auto-move folder."""
    from project_tracker.core.state_machine import validate_cr_transition
    from project_tracker.core.rules import validate_cr_approved_requires_drones, current_user
    from project_tracker.core.models import HistoryEntry

    path = Path(project_path)
    metadata = self._metadata_store.read(path)
    if metadata is None:
        raise FileNotFoundError(f"Project metadata not found: {path}")
    target = CRState(cr_state)
    validate_cr_transition(metadata.cr_state, target)

    if target == CRState.APPROVED:
        g1 = validate_cr_approved_requires_drones(metadata.drone_tickets)
        if not g1.allowed:
            raise ValueError("; ".join(g1.failed_guards))

    settings = self._settings_store.read()
    old = metadata.cr_state
    now = local_now()
    metadata.cr_state = target
    metadata.cr_state_updated_at = now
    metadata.updated_at = now
    if target == CRState.PENDING_APPROVAL and metadata.cr_pending_approval_at is None:
        metadata.cr_pending_approval_at = now
    metadata.history.append(HistoryEntry(
        timestamp=now, action="CR_STATE_CHANGE",
        detail=f"CR {old.value} → {target.value}", user=current_user(settings),
    ))
    self._metadata_store.write(path, metadata)

    banner = self._apply_auto_move(path)
    project_state = ProjectState(path.parent.name)
    # path.parent may be stale if moved; re-resolve from auto-move result is
    # handled by _apply_auto_move's cache rebuild. Re-read current location:
    response = {
        "project_path": str(path),
        "project_state": project_state.value,
        "cr_state": target.value,
    }
    if banner:
        response["banner"] = banner["banner"]
    return response
```

Note: when `_apply_auto_move` physically moves the folder, the original `path` no longer exists. The frontend refreshes from the EventQueue poll (R3), so returning the old path is acceptable for the immediate response; the dashboard reload picks up the new location. If the existing tests assert the returned `project_path` is current, adjust `_apply_auto_move` to return the moved path and thread it into `response`.

- [ ] **Step 3b: Add history to `update_cr_link` (L629)**

After `metadata.cr_link = cr_link` and before/with the existing `updated_at` set, append:

```python
            settings = self._settings_store.read()
            from project_tracker.core.models import HistoryEntry
            from project_tracker.core.rules import current_user
            metadata.history.append(HistoryEntry(
                timestamp=metadata.updated_at, action="CR_LINK",
                detail="CR link updated", user=current_user(settings),
            ))
```

- [ ] **Step 3c: Add history + auto-move to `update_drone` (L668)**

After the drone_state change block (L689-696) and before `self._metadata_store.write`, when `"drone_state" in data`, append a `HistoryEntry` with `action="DRONE_STATE_CHANGE"`. After the write, call `self._apply_auto_move(path)` (a drone reaching APPROVED can complete G1 and let a pending CR-APPROVED-driven move land — but per spec "Out of Scope", drone-only changes don't trigger a move unless CR is already at target; `resolve_auto_move` enforces that by keying on `metadata.cr_state`).

- [ ] **Step 4: Run to verify pass + full app_web suite**

Run: `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_app_web_dashboard_auto_move.py tests/ -k "app_web or dashboard" -v`
Expected: PASS. Fix any existing test asserting metadata-only (no history) behavior on these methods.

- [ ] **Step 5: Commit**

```bash
rtk git add project_tracker/app_web.py tests/test_app_web_dashboard_auto_move.py
rtk git commit -m "feat(adapter): wire G1 + history + auto-move into CR/drone updates"
```

## Task 8: H-10 reminder evaluation (dashboard load + dedup + re-arm)

**Files:**

- Modify: `project_tracker/app_web.py` — add `_evaluate_h10_reminders()` called from the concrete `dashboard_data` handler
- Test: `tests/test_app_web_dashboard_auto_move.py`

Context: On dashboard load, scan visible projects; for each where `h10_reminder_due(...)` is True AND not already notified (dedup via `h10_notified_at`), emit ONE notification + history note and stamp `h10_notified_at = now`. Re-arm: when the condition resolves (CR/all drones APPROVED) OR the start date changes, clear `h10_notified_at` so it can fire again later. Never blocks. `h10_reminder_days` comes from settings (Task 3, default 10).

Dedup/re-arm logic:

- due AND `h10_notified_at is None` → fire + stamp.
- due AND `h10_notified_at is not None` → skip (already notified).
- NOT due AND `h10_notified_at is not None` → clear stamp (re-arm).

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_app_web_dashboard_auto_move.py — append
def test_h10_fires_once_and_dedups(app_api_factory, tmp_uat_project_due_h10, monkeypatch):
    api, paths = app_api_factory(), tmp_uat_project_due_h10  # start within H-10, CR not APPROVED
    api.dashboard_data(paths.year.name)
    n1 = len([x for x in api.get_undismissed_notifications() if x.get("type") == "H10_REMINDER"])
    assert n1 == 1
    api.dashboard_data(paths.year.name)  # second load: no duplicate
    n2 = len([x for x in api.get_undismissed_notifications() if x.get("type") == "H10_REMINDER"])
    assert n2 == 1

def test_h10_rearms_when_condition_resolves(app_api_factory, tmp_uat_project_due_h10):
    api, paths = app_api_factory(), tmp_uat_project_due_h10
    api.dashboard_data(paths.year.name)  # fires + stamps
    # resolve: set CR APPROVED (no drones) -> not due -> stamp cleared on next load
    api.cr_update_state(str(paths.project), CRState.APPROVED.value)
    from project_tracker.infrastructure.metadata_store import MetadataStore
    # project likely moved to PROD_READY; read at new location
    moved = paths.year / "PROD_READY" / paths.project.name
    md = MetadataStore().read(moved if moved.is_dir() else paths.project)
    assert md.h10_notified_at is None
```

Note: notification accessor name (`get_undismissed_notifications`) must match the real AppAPI surface — check `app_web.py` (there is a `get_undismissed`-style accessor around L191). Adjust the test to the real method.

- [ ] **Step 2: Run to verify fail**

Run: `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_app_web_dashboard_auto_move.py -k h10 -v`
Expected: FAIL — no H-10 evaluation.

- [ ] **Step 3: Implement `_evaluate_h10_reminders` + call from dashboard_data**

```python
# project_tracker/app_web.py — add inside AppAPI
def _evaluate_h10_reminders(self, project_paths: list[Path]) -> None:
    from project_tracker.core.rules import h10_reminder_due, current_user
    from project_tracker.core.models import HistoryEntry

    settings = self._settings_store.read()
    days = settings.h10_reminder_days
    now = local_now()
    for path in project_paths:
        metadata = self._metadata_store.read(path)
        if metadata is None:
            continue
        due = h10_reminder_due(metadata, now=now, reminder_days=days)
        if due and metadata.h10_notified_at is None:
            if self._notification_service is not None:
                self._notification_service.add(
                    type="H10_REMINDER",
                    title="H-10 cutoff passed",
                    message=(
                        f"{path.name}: H-10 cutoff passed — CR/Drone not yet APPROVED. "
                        "Change start date or request management approval."
                    ),
                    project_path=path,
                )
            metadata.h10_notified_at = now
            metadata.history.append(HistoryEntry(
                timestamp=now, action="H10_REMINDER",
                detail="H-10 cutoff passed; CR/Drone not yet APPROVED",
                user=current_user(settings),
            ))
            self._metadata_store.write(path, metadata)
        elif not due and metadata.h10_notified_at is not None:
            metadata.h10_notified_at = None
            self._metadata_store.write(path, metadata)
```

Call it from the concrete `dashboard_data` handler (the AppAPI method backing the `dashboard_data` facade, which builds the project list): after assembling the list of visible project paths, call `self._evaluate_h10_reminders(paths)` before returning the DTO. The implementer must locate this handler — `dashboard_data` in the facade (`js_api.py:508`) delegates to a backing callable; find it in `app_web.py` (search `dashboard_data` / the `DashboardService` call site) and inject the evaluation there.

- [ ] **Step 4: Run to verify pass**

Run: `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_app_web_dashboard_auto_move.py -k h10 -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add project_tracker/app_web.py tests/test_app_web_dashboard_auto_move.py
rtk git commit -m "feat(adapter): H-10 reminder on dashboard load with dedup + re-arm"
```

## Task 9: R4 — Drone-FINISHED cascade surfacing on CR→FINISHED

**Files:**

- Modify: `project_tracker/core/state_machine.py` — add `drones_blocking_finish()` pure helper
- Modify: `project_tracker/app_web.py` — `_apply_auto_move` IMPLEMENTED branch
- Test: `tests/test_core_state_machine.py`, `tests/test_app_web_dashboard_auto_move.py`

Context: When CR→FINISHED would cascade drones→FINISHED, only `IN_PROGRESS→FINISHED` is a legal drone transition (`DRONE_MANUAL_TRANSITIONS`). Any drone in a state with no legal path to FINISHED (UAT, PENDING_APPROVAL, APPROVED, CANCELED) must NOT be silently skipped — the IMPLEMENTED move is blocked and the reason surfaces. Per spec this is a hard block with a clear message, not a partial move.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_core_state_machine.py — append
from project_tracker.core.enums import DroneState
from project_tracker.core.state_machine import drones_blocking_finish

def test_drones_blocking_finish_in_progress_ok():
    assert drones_blocking_finish([DroneState.IN_PROGRESS, DroneState.FINISHED]) == 0

def test_drones_blocking_finish_counts_illegal():
    # UAT and PENDING_APPROVAL cannot reach FINISHED
    assert drones_blocking_finish([DroneState.UAT, DroneState.PENDING_APPROVAL]) == 2

def test_drones_blocking_finish_empty():
    assert drones_blocking_finish([]) == 0
```

- [ ] **Step 2: Run to verify fail**

Run: `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_core_state_machine.py -k blocking_finish -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 3a: Implement `drones_blocking_finish`**

```python
# project_tracker/core/state_machine.py — append
def drones_blocking_finish(drone_states: list[DroneState]) -> int:
    """Count drones whose current state has no legal path to FINISHED.

    Only IN_PROGRESS -> FINISHED is legal; FINISHED is already done.
    Any other state blocks the CR->FINISHED cascade to IMPLEMENTED.
    """
    blocking = 0
    for state in drone_states:
        if state == DroneState.FINISHED:
            continue
        if state == DroneState.IN_PROGRESS:
            continue  # legal to finish
        blocking += 1
    return blocking
```

- [ ] **Step 3b: Block the IMPLEMENTED move in `_apply_auto_move`**

In `_apply_auto_move`, before invoking the IMPLEMENTED method, when `target == ProjectState.IMPLEMENTED`:

```python
    if target == ProjectState.IMPLEMENTED:
        from project_tracker.core.state_machine import drones_blocking_finish
        blocked = drones_blocking_finish(drone_states)
        if blocked:
            return {"banner": (
                f"{blocked} drone(s) cannot auto-finish (illegal state). "
                "Move to IMPLEMENTED blocked."
            )}
```

(Place this check after `target` is resolved and before `method_map` is called.)

- [ ] **Step 3c: Adapter test**

```python
# tests/test_app_web_dashboard_auto_move.py — append
def test_cr_finished_blocked_when_drone_cannot_finish(app_api_factory, tmp_prod_ready_with_uat_drone):
    api, paths = app_api_factory(), tmp_prod_ready_with_uat_drone
    # project in PROD_READY, CR IN_PROGRESS->FINISHED, one drone in UAT
    resp = api.cr_update_state(str(paths.project), CRState.FINISHED.value)
    assert "cannot auto-finish" in resp.get("banner", "")
    assert paths.project.is_dir()  # not moved to IMPLEMENTED
```

- [ ] **Step 4: Run to verify pass**

Run: `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/test_core_state_machine.py tests/test_app_web_dashboard_auto_move.py -k "blocking_finish or cannot_finish" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add project_tracker/core/state_machine.py project_tracker/app_web.py tests/test_core_state_machine.py tests/test_app_web_dashboard_auto_move.py
rtk git commit -m "feat: R4 - block IMPLEMENTED move when drones cannot auto-finish"
```

## Task 10: Frontend Dashboard gaps (A4, C2, C4, B4, B3) + G1 inline error

**Files:**

- Modify: `frontend/src/lib/components/Dashboard.svelte`
- Test: `frontend/tests/dashboard.test.ts` (extend)

Context: Section 4 of the spec — display polish only, no domain logic. Plus surface the G1 `ValueError` (raised in Task 7) as an inline error. The component already has `actionError` state (Dashboard.svelte:123) set from `r.error.message` on failed bridge calls — G1's message flows through that automatically (verify the bridge wraps the raised `ValueError` into `r.error.message`). Backend identifier extraction helpers `extract_cr_number`/`extract_drone_ticket` already exist (rules.py L55/L64) and `cr_number` is already returned by `cr_update_link`.

Each gap is small and independent — implement and commit individually.

- [ ] **Step 1 (A4): Show extracted identifier beside link cells**

The dashboard row DTO should carry `cr_number` (already present) and a per-drone `drone_ticket` id. In `Dashboard.svelte`, render the extracted id as a muted label beside each CR/drone link cell. If the drone DTO lacks the extracted ticket, add it to the backend dashboard row builder (`DashboardService`) using `extract_drone_ticket(drone_link)`. Commit: `feat(dashboard): A4 show extracted CR/drone identifier beside links`.

- [ ] **Step 2 (C2): Semantic state color chips**

Add a `stateChipClass(state: string): string` helper in the component returning Tailwind classes: APPROVED → green, PENDING\_\* → amber, CANCELED/POSTPONED → red, others → neutral. Apply to CR and drone state cells. Commit: `feat(dashboard): C2 semantic state color chips`.

- [ ] **Step 3 (C4): Inline per-cell saving spinner**

Track a `savingCell` key (e.g. `${project_path}:cr_state`) in `$state`; while a `callBridge` for that cell is in flight, render a small spinner in the cell (not just disabling the input). Clear on resolve. Commit: `feat(dashboard): C4 inline per-cell saving spinner`.

- [ ] **Step 4 (B4): Long-name ellipsis + tooltip**

Apply `truncate` + `title={fullName}` to project/sub-project name cells so long names ellipsize with a hover tooltip. Commit: `feat(dashboard): B4 long-name ellipsis + tooltip`.

- [ ] **Step 5 (B3): Zero-year empty-state nudge**

When `root_folder` is set but the dashboard returns zero year folders, render an "Add Year" empty-state prompt (reuse the existing Add Year control wired in Header.svelte / PRD 11). Commit: `feat(dashboard): B3 add-year empty-state nudge`.

- [ ] **Step 6: Frontend tests + build**

Add SSR/unit assertions in `frontend/tests/dashboard.test.ts` for: G1 inline error surfaces from a failed `cr_update_state`; extracted-id renders beside a link; `stateChipClass` returns the expected class per state.

Run:

```bash
rtk npm --prefix frontend run check
rtk npm --prefix frontend test
rtk npm --prefix frontend run build
```

Expected: typecheck clean, tests pass, build succeeds.

- [ ] **Step 7: Commit any remaining**

```bash
rtk git add frontend/src/lib/components/Dashboard.svelte frontend/tests/dashboard.test.ts
rtk git commit -m "test(dashboard): cover G1 inline error + extracted-id + state chips"
```

## Task 11: Full verification gate

**Files:** none (verification only)

- [ ] **Step 1: Full Python test suite**

Run: `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/ -q`
Expected: all pass. Investigate + fix any regression (especially older tests asserting metadata-only CR/drone behavior or T-10 failure in the prod-ready guard).

- [ ] **Step 2: py_compile guarded modules**

Run: `rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m py_compile project_tracker/app_web.py project_tracker/core/state_machine.py project_tracker/core/rules.py project_tracker/core/models.py`
Expected: no output (clean).

- [ ] **Step 3: Frontend gates**

Run:

```bash
rtk npm --prefix frontend run check
rtk npm --prefix frontend run build
```

Expected: typecheck clean, build succeeds.

- [ ] **Step 4: Update PROJECT_STATUS.md**

Record: auto-move engine wired, T-10→H-10 reminder, G1 guard, R3 event push, R4 cascade block, Dashboard gaps A4/C2/C4/B4/B3. Note Windows-only manual gate still pending (real `shutil.move`, WebView2 render).

- [ ] **Step 5: Refresh knowledge graph**

Run: `rtk graphify update .`
Expected: graph rebuilt (AST-only, no API cost).

- [ ] **Step 6: Commit status update**

```bash
rtk git add PROJECT_STATUS.md
rtk git commit -m "docs: update status for dashboard auto-move + gap closure"
```

---

## Self-Review

**Spec coverage:**

- §1 Auto-Move Evaluator → Task 1 (`resolve_auto_move`) + Task 6 (orchestration).
- §2 H-10 Reminder → Task 3 (fields), Task 4 (helpers), Task 5 (T-10 removal), Task 8 (eval + dedup + re-arm + configurable days).
- §3 Wiring + History/Notifications → Task 6 (helper), Task 7 (history on CR state / drone state / CR link; routed POSTPONED/CANCELED; guard-fail banner).
- §4 Smaller gaps A4/C2/C4/B4/B3 → Task 10.
- G1 hard guard → Task 2 (core) + Task 7 (enforced in `update_cr_state`).
- R3 EventQueue on move → Task 6 (`push_event("AUTO_MOVE", ...)`).
- R4 cascade surfacing → Task 9.
- Verification Plan → Task 11 + per-task TDD steps.

**Out-of-scope respected:** drone-only over-trigger prevented by `resolve_auto_move` keying on `cr_state`; no toast/undo; no pre-move confirm (silent move + notification); other menus untouched.

**Open implementation notes (flag during execution, not blockers):**

1. **Moved-path response.** After `_apply_auto_move` physically moves the folder, `update_cr_state` returns the stale `path`. Frontend recovers via the R3 EventQueue poll. If any existing test asserts the response `project_path` is the _new_ location, thread the moved path out of `_apply_auto_move` (return it alongside the banner) and into the response. Decide at Task 7 Step 4.
2. **Test fixtures.** Tasks 6-9 assume `app_api_factory` / `tmp_uat_project*` fixtures. They likely do NOT exist yet — the implementer MUST read one existing `tests/test_app_web_*.py` first and copy its real AppAPI construction + temp-root setup verbatim, then name fixtures to match. This is the single highest-risk area; do it before writing Task 6.
3. **Notification accessor name.** Task 8 test uses `get_undismissed_notifications()` — confirm the real AppAPI accessor (around app_web.py:191 there is an undismissed filter) and adjust.
4. **`current_user` import.** Used in app_web.py history appends; confirm it is imported from `project_tracker.core.rules` at module top or import locally inside each method (the plan uses local imports to be safe).
5. **EventQueue drained in tests.** `drain_events()` is global state — call `clear_events()` in fixture setup/teardown to avoid cross-test bleed.

**Placeholder scan:** none — every code step has concrete code; fixture-dependent tests carry an explicit "read the existing test first" instruction with the reason.

**Type consistency:** `resolve_auto_move(CRState, list[DroneState], ProjectState) -> ProjectState | None`; `validate_cr_approved_requires_drones(list[DroneTicket]) -> TransitionGuardResult`; `compute_h10(ProjectMetadata, *, reminder_days) -> datetime | None`; `h10_reminder_due(ProjectMetadata, *, now, reminder_days) -> bool`; `drones_blocking_finish(list[DroneState]) -> int`; `_apply_auto_move(Path) -> dict | None`. Banner dict shape `{"banner": str}` used consistently in Tasks 6/7/9.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-10-dashboard-auto-move.md`. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task, two-stage review between tasks, fast iteration. Best here given the test-fixture risk (note 2): a reviewer catches fixture mismatches early.
2. **Inline Execution** — execute tasks in this session via executing-plans, batch with checkpoints.

Which approach?
