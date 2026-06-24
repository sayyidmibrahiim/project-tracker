"""Property-based test for Property 5: guard-gated, reversible-on-failure folder transitions.

Property 5 (design.md): Folder transitions are guard-gated and reversible-on-failure.

    For any project in any source Folder_State, a disallowed transition leaves
    state unchanged and returns ``ok=false``; a mid-move failure rolls back with
    no cache update.

**Validates: Requirements 4.9, 4.12**

The locked dependency baseline does not include ``hypothesis`` (and adding
dependencies is forbidden by the release-candidate rules), so the property is
exercised with a deterministic, seeded ``random.Random`` generator -- the same
pattern used by the sibling property tests in this spec. The generator produces
a diverse population of project source states, CR states, drone-ticket
configurations, datetimes, years, and names, paired with transition requests.

Every destructive operation runs strictly against pytest's ``tmp_path``
(Temp_Root): a year/state folder tree is built per case, the transition is
driven through the real wired ``create_js_api()`` bridge surface, and the
Cache_Db lives in a per-case temp database file.

Two invariants are checked across the generated input space:

* **Guard-gated (Req 4.9 / 4.10):** when a transition is requested from a source
  Folder_State the state machine does not permit, the bridge returns ``ok=false``,
  the project folder stays in its original location with metadata untouched, and
  the Cache_Db is not mutated.
* **Reversible-on-failure (Req 4.12):** when the physical move fails mid-flight
  (``shutil.move`` is monkeypatched to raise), the bridge returns ``ok=false``,
  the project remains in its pre-move location with metadata untouched, and the
  Cache_Db is left exactly as it was before the attempt (no cache update).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, replace
from datetime import timedelta
from pathlib import Path

import pytest

from core.enums import CRState, DroneState, ProjectState
from core.models import (
    AppSettings,
    DroneTicket,
    HistoryEntry,
    ProjectMetadata,
    local_now,
)
from core.state_machine import (
    PROJECT_STATE_TRANSITIONS,
    REOPEN_ALLOWED_FOLDER_STATES,
)
from infrastructure.cache_db import CacheDb, rebuild_year_cache
from infrastructure.metadata_store import MetadataStore
from infrastructure.settings_store import SettingsStore

# ── transition catalogue ────────────────────────────────────────────────
# Maps each guarded bridge transition to the Folder_State it targets. ``reopen``
# is special: it is gated by REOPEN_ALLOWED_FOLDER_STATES rather than the plain
# PROJECT_STATE_TRANSITIONS map, so its allowed sources are computed separately.
_TARGET_BY_TRANSITION: dict[str, ProjectState] = {
    "folder_move_to_prod_ready": ProjectState.PROD_READY,
    "folder_move_to_implemented": ProjectState.IMPLEMENTED,
    "folder_postpone": ProjectState.POSTPONED,
    "folder_cancel": ProjectState.CANCELED,
}

_ALL_STATES: tuple[ProjectState, ...] = (
    ProjectState.UAT_PREPARE,
    ProjectState.PROD_READY,
    ProjectState.IMPLEMENTED,
    ProjectState.POSTPONED,
    ProjectState.CANCELED,
)


def _allowed_sources(transition: str) -> frozenset[ProjectState]:
    """Independent oracle for which source states permit ``transition``."""
    if transition == "folder_reopen":
        return frozenset(REOPEN_ALLOWED_FOLDER_STATES)
    target = _TARGET_BY_TRANSITION[transition]
    return frozenset(
        source
        for source, targets in PROJECT_STATE_TRANSITIONS.items()
        if target in targets
    )


def _disallowed_sources(transition: str) -> list[ProjectState]:
    allowed = _allowed_sources(transition)
    return [state for state in _ALL_STATES if state not in allowed]


_GUARDED_TRANSITIONS = (
    "folder_move_to_prod_ready",
    "folder_move_to_implemented",
    "folder_postpone",
    "folder_cancel",
    "folder_reopen",
)

# Transitions whose only gate is the state-machine source check (no business
# guards): from an allowed source they reach the physical move, so they exercise
# the mid-move rollback contract deterministically.
_ROLLBACK_TRANSITIONS = ("folder_postpone", "folder_cancel", "folder_reopen")


# ── scenario generation (seeded, deterministic) ──────────────────────────
@dataclass(frozen=True)
class _Scenario:
    transition: str
    source_state: ProjectState
    seed: int


def _build_metadata(rng: random.Random) -> ProjectMetadata:
    """Generate a diverse, valid ProjectMetadata for input-space coverage."""
    now = local_now()
    # REOPEN is an action/event, never a persistent CR state, so exclude it.
    cr_state = rng.choice([s for s in CRState if s != CRState.REOPEN])
    drone_count = rng.randrange(0, 4)
    drones = [
        DroneTicket(
            subfolder_name=rng.choice([None, f"sub_{i}"]),
            drone_link=rng.choice(["", f"https://drone.example/{rng.randrange(1000)}"]),
            drone_state=rng.choice(list(DroneState)),
            owner=rng.choice(["", "Alice", "Bob"]),
        )
        for i in range(drone_count)
    ]
    start = now + timedelta(days=rng.randint(-5, 30)) if rng.random() < 0.8 else None
    end = (
        (start + timedelta(days=rng.randint(1, 20)))
        if (start is not None and rng.random() < 0.8)
        else None
    )
    pending = now - timedelta(days=rng.randint(0, 40)) if rng.random() < 0.6 else None
    return ProjectMetadata(
        project_name="placeholder",  # overwritten by caller to match folder
        start_datetime=start,
        end_datetime=end,
        cr_link=rng.choice(["", "https://cr.example/CR-42"]),
        cr_state=cr_state,
        cr_pending_approval_at=pending,
        drone_tickets=drones,
        implementation_plan=rng.choice(["", "do the thing"]),
        history=[
            HistoryEntry(
                timestamp=now,
                action="CREATE",
                detail="seeded",
                user="seed",
            )
        ],
        created_at=now,
        updated_at=now,
    )


def _generate_disallowed_scenarios(
    count: int = 120, seed: int = 4912
) -> list[_Scenario]:
    """Diverse (transition, disallowed-source) scenarios for the guard property."""
    scenarios: list[_Scenario] = []
    # Deterministic full coverage: every disallowed (transition, source) pair.
    base_seed = 0
    for transition in _GUARDED_TRANSITIONS:
        for source in _disallowed_sources(transition):
            scenarios.append(_Scenario(transition, source, base_seed))
            base_seed += 1
    # Seeded random variety on top of the exhaustive base.
    rng = random.Random(seed)
    for _ in range(count):
        transition = rng.choice(_GUARDED_TRANSITIONS)
        disallowed = _disallowed_sources(transition)
        source = rng.choice(disallowed)
        scenarios.append(_Scenario(transition, source, base_seed))
        base_seed += 1
    return scenarios


def _generate_rollback_scenarios(
    count: int = 120, seed: int = 7731
) -> list[_Scenario]:
    """Diverse (transition, allowed-source) scenarios for the rollback property."""
    scenarios: list[_Scenario] = []
    base_seed = 0
    for transition in _ROLLBACK_TRANSITIONS:
        for source in sorted(_allowed_sources(transition), key=lambda s: s.value):
            scenarios.append(_Scenario(transition, source, base_seed))
            base_seed += 1
    rng = random.Random(seed)
    for _ in range(count):
        transition = rng.choice(_ROLLBACK_TRANSITIONS)
        source = rng.choice(sorted(_allowed_sources(transition), key=lambda s: s.value))
        scenarios.append(_Scenario(transition, source, base_seed))
        base_seed += 1
    return scenarios


_DISALLOWED = _generate_disallowed_scenarios()
_DISALLOWED_IDS = [
    f"{i:03d}:{s.transition}:{s.source_state.value}" for i, s in enumerate(_DISALLOWED)
]
_ROLLBACK = _generate_rollback_scenarios()
_ROLLBACK_IDS = [
    f"{i:03d}:{s.transition}:{s.source_state.value}" for i, s in enumerate(_ROLLBACK)
]


# ── per-case fixtures/helpers (all within tmp_path) ──────────────────────
def _make_api(tmp_path: Path):
    """Wire a real JsApi over a temp root + temp Cache_Db; return (api, db_path, root)."""
    from project_tracker import app_web

    root = tmp_path / "Temp_Root"
    root.mkdir()
    db_path = tmp_path / "cache.db"
    settings_store = SettingsStore(config_dir=tmp_path / "config")
    settings_store.write(replace(AppSettings(), root_folder=root))
    api = app_web.create_js_api(db_path=db_path, settings_store=settings_store)
    return api, db_path, root


def _create_project(
    root: Path, year: str, state: ProjectState, name: str, metadata: ProjectMetadata
) -> Path:
    project_path = root / year / state.value / name
    project_path.mkdir(parents=True)
    MetadataStore().save(project_path, replace(metadata, project_name=name))
    return project_path


def _cache_snapshot(db_path: Path) -> set[tuple[str, str]]:
    """Stable snapshot of project_index as {(path, folder_state)}."""
    cache = CacheDb(db_path)
    cache.initialize()
    return {
        (str(row.project_path), str(row.project_state))
        for row in cache.list_projects()
    }


@pytest.mark.parametrize("scenario", _DISALLOWED, ids=_DISALLOWED_IDS)
def test_property_disallowed_transition_leaves_state_unchanged_and_fails(
    tmp_path: Path, scenario: _Scenario
) -> None:
    """Req 4.9/4.10: a disallowed source transition is rejected with ok=false,
    leaving the folder, its metadata, and the Cache_Db unchanged."""
    rng = random.Random(scenario.seed)
    api, db_path, root = _make_api(tmp_path)
    year = rng.choice(["2023", "2024", "2025", "2026"])
    name = f"PROJ_{scenario.seed}"
    metadata = _build_metadata(rng)
    project_path = _create_project(root, year, scenario.source_state, name, metadata)

    # Seed the cache to a known, non-empty baseline so "no cache update" is
    # meaningful rather than vacuously empty.
    rebuild_year_cache(CacheDb(db_path), root / year, MetadataStore())
    cache_before = _cache_snapshot(db_path)
    meta_before = MetadataStore().load(project_path)

    result = getattr(api, scenario.transition)(str(project_path))

    assert result["ok"] is False, (
        f"disallowed {scenario.transition} from {scenario.source_state.value} "
        f"must return ok=false, got {result}"
    )
    assert result["error"] is not None and result["error"].get("code"), (
        f"ok=false must carry an error code, got {result}"
    )
    # The project folder stays exactly where it was.
    assert project_path.is_dir(), "rejected transition removed the source folder"
    # No sibling target-state folder for this project sprang into being.
    for state in _ALL_STATES:
        if state == scenario.source_state:
            continue
        assert not (root / year / state.value / name).exists(), (
            f"rejected transition created a stray {state.value} folder"
        )
    # Metadata is untouched (same history length and CR state).
    meta_after = MetadataStore().load(project_path)
    assert meta_after is not None and meta_before is not None
    assert len(meta_after.history) == len(meta_before.history), (
        "rejected transition mutated history"
    )
    assert meta_after.cr_state == meta_before.cr_state, (
        "rejected transition mutated cr_state"
    )
    # Cache_Db is unchanged.
    assert _cache_snapshot(db_path) == cache_before, (
        "rejected transition mutated the Cache_Db"
    )


@pytest.mark.parametrize("scenario", _ROLLBACK, ids=_ROLLBACK_IDS)
def test_property_mid_move_failure_rolls_back_with_no_cache_update(
    tmp_path: Path, scenario: _Scenario, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Req 4.12: a mid-move failure leaves the project in its pre-move location
    with no cache update and returns ok=false."""
    rng = random.Random(scenario.seed)
    api, db_path, root = _make_api(tmp_path)
    year = rng.choice(["2023", "2024", "2025", "2026"])
    name = f"PROJ_{scenario.seed}"
    metadata = _build_metadata(rng)
    project_path = _create_project(root, year, scenario.source_state, name, metadata)

    # Seed a known cache baseline, then snapshot it.
    rebuild_year_cache(CacheDb(db_path), root / year, MetadataStore())
    cache_before = _cache_snapshot(db_path)
    meta_before = MetadataStore().load(project_path)

    # Induce a mid-move failure: the physical move raises after guards pass.
    def _boom(*_args: object, **_kwargs: object):
        raise OSError("simulated mid-move failure")

    monkeypatch.setattr(
        "services.project_service.shutil.move", _boom
    )

    result = getattr(api, scenario.transition)(str(project_path))

    assert result["ok"] is False, (
        f"mid-move failure for {scenario.transition} from "
        f"{scenario.source_state.value} must return ok=false, got {result}"
    )
    assert result["error"] is not None and result["error"].get("code"), (
        f"ok=false must carry an error code, got {result}"
    )
    # Project remains in its pre-move location with metadata intact.
    assert project_path.is_dir(), "rollback lost the project from its source location"
    meta_after = MetadataStore().load(project_path)
    assert meta_after is not None and meta_before is not None
    assert len(meta_after.history) == len(meta_before.history), (
        "failed move mutated history (no rollback)"
    )
    assert meta_after.cr_state == meta_before.cr_state, (
        "failed move mutated cr_state (no rollback)"
    )
    # No cache update occurred.
    assert _cache_snapshot(db_path) == cache_before, (
        "failed move updated the Cache_Db despite rollback contract"
    )
