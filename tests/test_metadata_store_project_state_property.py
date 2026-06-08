"""Property-based test for Property 3: `project_state` is never serialized.

Design Correctness Property 3 (prd-completion design.md):
    For any `ProjectMetadata`, the JSON written by `MetadataStore` contains no
    `project_state` key.

**Validates: Requirements 2.5**

Implementation note
-------------------
The design's principle #3 ("No new dependencies") and the workspace
release-candidate hard rules forbid adding packages, and `hypothesis` is not
part of the PRD v3.1 baseline / not installed. This property test therefore
uses the standard library `random` module to generate a large, diverse space of
`ProjectMetadata` instances and asserts the invariant holds for every one. The
generation is seeded per-example and the failing seed/example is surfaced on
assertion failure so any counterexample is reproducible.

All filesystem activity is confined to pytest's `tmp_path` (Temp_Root).
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from project_tracker.core.enums import CRState, DroneState
from project_tracker.core.models import (
    DroneTicket,
    EmailFlags,
    HistoryEntry,
    ProjectMetadata,
)
from project_tracker.infrastructure.metadata_store import METADATA_FILE, MetadataStore

# Number of randomly generated examples per property run.
EXAMPLE_COUNT = 250

# A pool of strings spanning empty, whitespace, unicode, and a literal that
# collides with the forbidden key name to stress the serializer.
_STRING_POOL = [
    "",
    "PROJECT_A",
    "  spaced  ",
    "project_state",  # value that looks like the forbidden key
    "проект",
    "项目-2026",
    'weird"\\chars/',
    "a" * 300,
    "line\nbreak",
]

_TZINFOS = [
    timezone.utc,
    timezone(timedelta(hours=7)),  # WIB
    timezone(timedelta(hours=-5)),
    timezone(timedelta(minutes=330)),  # IST
]


def _rand_string(rng: random.Random) -> str:
    return rng.choice(_STRING_POOL)


def _rand_datetime(rng: random.Random) -> datetime | None:
    if rng.random() < 0.2:
        return None
    base = datetime(2020, 1, 1) + timedelta(
        days=rng.randint(0, 4000),
        seconds=rng.randint(0, 86_399),
    )
    return base.replace(tzinfo=rng.choice(_TZINFOS))


def _rand_drone_ticket(rng: random.Random) -> DroneTicket:
    return DroneTicket(
        subfolder_name=_rand_string(rng) if rng.random() < 0.8 else None,
        drone_link=_rand_string(rng),
        drone_state=rng.choice(list(DroneState)),
        drone_state_updated_at=_rand_datetime(rng),
        owner=_rand_string(rng),
    )


def _rand_history_entry(rng: random.Random) -> HistoryEntry:
    timestamp = _rand_datetime(rng)
    # HistoryEntry serialization requires a tz-aware timestamp.
    if timestamp is None:
        timestamp = datetime(2024, 6, 1, tzinfo=timezone.utc)
    return HistoryEntry(
        timestamp=timestamp,
        action=_rand_string(rng),
        detail=_rand_string(rng),
        user=_rand_string(rng),
    )


def _generate_metadata(rng: random.Random) -> ProjectMetadata:
    return ProjectMetadata(
        project_name=_rand_string(rng),
        start_datetime=_rand_datetime(rng),
        end_datetime=_rand_datetime(rng),
        cr_link=_rand_string(rng),
        cr_state=rng.choice(list(CRState)),
        cr_state_updated_at=_rand_datetime(rng),
        cr_pending_approval_at=_rand_datetime(rng),
        drone_tickets=[_rand_drone_ticket(rng) for _ in range(rng.randint(0, 4))],
        notes=_rand_string(rng),
        implementation_plan=_rand_string(rng),
        email_flags=EmailFlags(
            ack_sent=rng.random() < 0.5,
            approval_sent=rng.random() < 0.5,
            last_cr_link_when_sent=_rand_string(rng) if rng.random() < 0.5 else None,
        ),
        history=[_rand_history_entry(rng) for _ in range(rng.randint(0, 3))],
        created_at=_rand_datetime(rng),
        updated_at=_rand_datetime(rng),
    )


def _contains_project_state_key(value: Any) -> bool:
    """Recursively check whether any mapping in the structure has the key."""
    if isinstance(value, dict):
        if "project_state" in value:
            return True
        return any(_contains_project_state_key(item) for item in value.values())
    if isinstance(value, list):
        return any(_contains_project_state_key(item) for item in value)
    return False


def test_project_state_is_never_serialized(tmp_path: Path) -> None:
    """Property 3: for any ProjectMetadata, written JSON has no project_state key."""
    store = MetadataStore()

    for example_index in range(EXAMPLE_COUNT):
        seed = example_index
        rng = random.Random(seed)
        metadata = _generate_metadata(rng)

        project_path = tmp_path / f"example_{example_index}"
        store.write(project_path, metadata)

        raw = json.loads((project_path / METADATA_FILE).read_text(encoding="utf-8"))

        # The property: no `project_state` key anywhere in the written JSON.
        assert not _contains_project_state_key(raw), (
            f"project_state key was serialized for seed={seed}; "
            f"written JSON: {raw!r}"
        )


def test_project_state_popped_even_if_to_dict_emits_it(tmp_path: Path) -> None:
    """Defensive arm of Property 3: the write path strips `project_state`.

    `ProjectMetadata.to_dict()` does not currently emit `project_state`, so the
    happy-path generator above can never trip the guard on its own. This case
    forces `to_dict()` to return the forbidden key and asserts the store's
    `data.pop("project_state", None)` removes it before writing.
    """

    class _LeakyMetadata(ProjectMetadata):
        def to_dict(self) -> dict[str, Any]:  # type: ignore[override]
            data = super().to_dict()
            data["project_state"] = "PROD_READY"
            return data

    metadata = _LeakyMetadata(project_name="LEAK")
    project_path = tmp_path / "leaky"

    MetadataStore().write(project_path, metadata)

    raw = json.loads((project_path / METADATA_FILE).read_text(encoding="utf-8"))
    assert "project_state" not in raw
