"""Property-based test for durable pin/favorite round-trips in SecondBrainService.

Property 9: Pin/favorite persistence round-trips (design.md / Requirements 13.1–13.3)

    For any sequence of pin/favorite toggles, the restored state after reload
    equals the last toggled state.

The locked dependency baseline does not include ``hypothesis`` (and adding
dependencies is forbidden by the release-candidate rules), so the property is
exercised with a deterministic, seeded ``random.Random`` generator -- the same
pattern used by the sibling property tests in this spec. Each generated example
produces an arbitrary population of Second Brain item ids plus an arbitrary
sequence of pin/favorite toggles across those ids. The toggles are applied to a
``SecondBrainService`` whose ``folder_provider`` points at a fresh per-example
folder under pytest's ``tmp_path`` (Temp_Root). A FRESH service instance is then
constructed over the SAME folder -- mirroring an application restart that
reloads the durable sidecar ``{folder}/.project_tracker_index.json`` -- and the
restored pinned/favorite state of every item is asserted to equal the last
toggled state tracked by an independent in-test model.

All filesystem activity is confined to ``tmp_path``; no new dependencies.

**Validates: Requirements 13.1, 13.2, 13.3**
"""

from __future__ import annotations

import random
from pathlib import Path

from project_tracker.services.second_brain_service import (
    SecondBrainItem,
    SecondBrainService,
)

# Number of randomized examples explored. Kept modest so the suite stays fast
# while still covering a broad slice of the (item-count x toggle-sequence) space.
EXAMPLES = 200


def _make_items_provider(item_ids: list[str]):
    """Return a provider that yields fresh, un-flagged items for ``item_ids``.

    Every call rebuilds the items with ``pinned=False`` / ``favorite=False`` so
    that any persisted pin/favorite state seen by the service comes solely from
    the durable sidecar -- exactly as a real restart would rebuild the read-only
    filesystem listing before applying restored metadata.
    """

    def provider() -> list[SecondBrainItem]:
        return [
            SecondBrainItem(
                id=item_id,
                title=f"Note {item_id}",
                path=Path(f"/brain/{item_id}.md"),
                item_type="note",
                pinned=False,
                favorite=False,
                excerpt=f"body for {item_id}",
            )
            for item_id in item_ids
        ]

    return provider


def test_property_pin_favorite_persistence_round_trips(tmp_path: Path) -> None:
    """Any toggle sequence's last state survives a fresh reload over the folder."""
    for seed in range(EXAMPLES):
        rng = random.Random(seed)

        # Per-example temp folder (Temp_Root only) for the durable sidecar.
        folder = tmp_path / f"brain_{seed}"
        folder.mkdir()

        item_count = rng.randint(1, 5)
        item_ids = [f"item-{i}" for i in range(item_count)]
        provider = _make_items_provider(item_ids)

        # Independent model of the expected last-toggled state per item.
        expected: dict[str, dict[str, bool]] = {
            item_id: {"pinned": False, "favorite": False} for item_id in item_ids
        }

        service = SecondBrainService(
            items_provider=provider,
            folder_provider=lambda f=folder: f,
        )

        sequence_length = rng.randint(0, 30)
        operations: list[tuple[str, str]] = []
        for _ in range(sequence_length):
            item_id = rng.choice(item_ids)
            flag = rng.choice(["pinned", "favorite"])
            operations.append((item_id, flag))

            if flag == "pinned":
                service.pin_item(item_id)
            else:
                service.favorite_item(item_id)
            # Toggle flips the model flag to match the service semantics.
            expected[item_id][flag] = not expected[item_id][flag]

        # Simulate a restart: a brand-new service over the SAME folder restores
        # persisted metadata from the durable sidecar.
        reloaded = SecondBrainService(
            items_provider=_make_items_provider(item_ids),
            folder_provider=lambda f=folder: f,
        )

        for item_id in item_ids:
            restored = reloaded.get_item(item_id)
            assert restored is not None, (
                f"item missing after reload (seed={seed}, id={item_id})"
            )
            assert restored.pinned == expected[item_id]["pinned"], (
                f"pinned state did not round-trip (seed={seed}, id={item_id}, "
                f"operations={operations}, expected={expected[item_id]['pinned']}, "
                f"restored={restored.pinned})"
            )
            assert restored.favorite == expected[item_id]["favorite"], (
                f"favorite state did not round-trip (seed={seed}, id={item_id}, "
                f"operations={operations}, expected={expected[item_id]['favorite']}, "
                f"restored={restored.favorite})"
            )
