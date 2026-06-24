"""Property-based test for Property 4: Datetimes round-trip tz-aware.

Design Correctness Property 4 (prd-completion design.md):
    For any stored datetime, reading it back yields a timezone-aware value with
    an explicit UTC offset.

**Validates: Requirements 2.6**

Implementation note
-------------------
The design's principle #2 ("No new dependencies") and the workspace
release-candidate hard rules forbid adding packages, and `hypothesis` is not
part of the PRD v3.1 baseline / not installed. This property test therefore
uses the standard library `random` module to generate a large, diverse space of
`ProjectMetadata` instances whose datetime fields span many timezone offsets
(UTC, positive/negative whole-hour, and sub-hour offsets). For every generated
example it writes via `MetadataStore.write` and reads back via
`MetadataStore.read`, asserting each datetime that was stored reads back as a
timezone-aware value (``tzinfo is not None`` and ``utcoffset() is not None``)
that represents the same instant — with its explicit UTC offset preserved.

Generation is seeded per-example and the failing seed/example is surfaced on
assertion failure so any counterexample is reproducible. All filesystem
activity is confined to pytest's `tmp_path` (Temp_Root).
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.enums import CRState, DroneState
from core.models import (
    DroneTicket,
    HistoryEntry,
    ProjectMetadata,
    local_now,
)
from infrastructure.metadata_store import MetadataStore

# Number of randomly generated examples per property run.
EXAMPLE_COUNT = 300

# A broad pool of UTC offsets: zero, positive/negative whole hours, and
# sub-hour offsets (e.g. IST +05:30, Nepal +05:45, Newfoundland -03:30).
_OFFSET_POOL = [
    timezone.utc,
    timezone(timedelta(hours=7)),  # WIB +07:00
    timezone(timedelta(hours=-5)),  # EST -05:00
    timezone(timedelta(hours=14)),  # max east +14:00
    timezone(timedelta(hours=-12)),  # far west -12:00
    timezone(timedelta(minutes=330)),  # IST +05:30
    timezone(timedelta(minutes=345)),  # Nepal +05:45
    timezone(timedelta(minutes=-210)),  # Newfoundland -03:30
    timezone(timedelta(minutes=-1)),  # tiny negative offset
    timezone(timedelta(minutes=1)),  # tiny positive offset
]

# Datetime field names on ProjectMetadata that participate in the round-trip.
_PROJECT_DATETIME_FIELDS = (
    "start_datetime",
    "end_datetime",
    "cr_state_updated_at",
    "cr_pending_approval_at",
    "created_at",
    "updated_at",
)


def _rand_aware_datetime(rng: random.Random) -> datetime:
    """Generate a diverse timezone-aware datetime with an explicit offset.

    Occasionally returns ``local_now()`` to exercise the production helper used
    by the app, which is itself tz-aware via ``datetime.now().astimezone()``.
    """
    if rng.random() < 0.1:
        return local_now()
    base = datetime(2000, 1, 1) + timedelta(
        days=rng.randint(0, 18_000),
        seconds=rng.randint(0, 86_399),
        microseconds=rng.randint(0, 999_999),
    )
    return base.replace(tzinfo=rng.choice(_OFFSET_POOL))


def _generate_metadata(rng: random.Random) -> ProjectMetadata:
    """Build a ProjectMetadata whose every datetime field is tz-aware."""
    return ProjectMetadata(
        project_name=f"P_{rng.randint(0, 9999)}",
        start_datetime=_rand_aware_datetime(rng),
        end_datetime=_rand_aware_datetime(rng),
        cr_link="",
        cr_state=rng.choice(list(CRState)),
        cr_state_updated_at=_rand_aware_datetime(rng),
        cr_pending_approval_at=_rand_aware_datetime(rng),
        drone_tickets=[
            DroneTicket(
                subfolder_name=f"sub_{i}",
                drone_link="",
                drone_state=rng.choice(list(DroneState)),
                drone_state_updated_at=_rand_aware_datetime(rng),
                owner="",
            )
            for i in range(rng.randint(0, 3))
        ],
        history=[
            HistoryEntry(
                timestamp=_rand_aware_datetime(rng),
                action="x",
                detail="y",
                user="z",
            )
            for _ in range(rng.randint(0, 3))
        ],
        created_at=_rand_aware_datetime(rng),
        updated_at=_rand_aware_datetime(rng),
    )


def _assert_round_trip(
    original: datetime,
    restored: datetime | None,
    *,
    seed: int,
    label: str,
) -> None:
    """Assert a single datetime read back tz-aware and equal to its instant."""
    assert restored is not None, (
        f"{label} read back as None (seed={seed}, original={original!r})"
    )
    # tz-aware with an explicit UTC offset.
    assert restored.tzinfo is not None, (
        f"{label} read back naive (seed={seed}, original={original!r})"
    )
    assert restored.utcoffset() is not None, (
        f"{label} read back without a UTC offset (seed={seed}, "
        f"original={original!r}, restored={restored!r})"
    )
    # Same instant, with the explicit offset preserved byte-for-byte.
    assert restored == original, (
        f"{label} instant changed across round-trip (seed={seed}, "
        f"original={original!r}, restored={restored!r})"
    )
    assert restored.utcoffset() == original.utcoffset(), (
        f"{label} UTC offset changed across round-trip (seed={seed}, "
        f"original={original!r}, restored={restored!r})"
    )


def test_datetimes_round_trip_tz_aware(tmp_path: Path) -> None:
    """Property 4: any stored datetime reads back tz-aware with a UTC offset."""
    store = MetadataStore()

    for example_index in range(EXAMPLE_COUNT):
        seed = example_index
        rng = random.Random(seed)
        metadata = _generate_metadata(rng)

        project_path = tmp_path / f"example_{example_index}"
        store.write(project_path, metadata)
        restored = store.read(project_path)

        assert restored is not None, f"metadata read back as None (seed={seed})"

        # Top-level datetime fields.
        for field_name in _PROJECT_DATETIME_FIELDS:
            _assert_round_trip(
                getattr(metadata, field_name),
                getattr(restored, field_name),
                seed=seed,
                label=field_name,
            )

        # Drone ticket timestamps.
        assert len(restored.drone_tickets) == len(metadata.drone_tickets)
        for i, (orig_ticket, new_ticket) in enumerate(
            zip(metadata.drone_tickets, restored.drone_tickets)
        ):
            _assert_round_trip(
                orig_ticket.drone_state_updated_at,
                new_ticket.drone_state_updated_at,
                seed=seed,
                label=f"drone_tickets[{i}].drone_state_updated_at",
            )

        # History entry timestamps.
        assert len(restored.history) == len(metadata.history)
        for i, (orig_entry, new_entry) in enumerate(
            zip(metadata.history, restored.history)
        ):
            _assert_round_trip(
                orig_entry.timestamp,
                new_entry.timestamp,
                seed=seed,
                label=f"history[{i}].timestamp",
            )
