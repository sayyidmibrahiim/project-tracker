"""Property-based test for atomic-write preservation in metadata_store.

Property 2: Atomic write preserves the original (design.md / Requirement 2.10)

    For any prior file content and any induced failure before the replace
    step, the target file equals its pre-write content.

This is implemented with stdlib only (no new test dependencies): a seeded
random generator produces arbitrary prior JSON contents and arbitrary
"poisoned" payloads that contain a non-JSON-serializable value, which forces
``json.dump`` to raise *before* the atomic ``Path.replace`` step. The invariant
checked across all generated cases is that the target ends up byte-for-byte
identical to its pre-write content (or stays absent when there was no prior
file), with no partial ``.tmp`` file left behind.

All filesystem activity is confined to pytest's ``tmp_path`` (Temp_Root).

**Validates: Requirements 2.10**
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import pytest

from project_tracker.core.exceptions import AtomicWriteError
from project_tracker.infrastructure.metadata_store import atomic_write_json

# Number of randomized examples explored per property. Kept modest so the suite
# stays fast while still covering a broad slice of the input space.
EXAMPLES = 200


def _random_json_scalar(rng: random.Random) -> Any:
    """Generate an arbitrary JSON-serializable scalar (finite numbers only)."""
    choice = rng.randrange(5)
    if choice == 0:
        return rng.randint(-1_000_000, 1_000_000)
    if choice == 1:
        # Bounded, finite float (no nan/inf, which would complicate equality).
        return round(rng.uniform(-1e6, 1e6), 6)
    if choice == 2:
        length = rng.randrange(0, 12)
        alphabet = "abcdefghijklmnopqrstuvwxyz \t\n\"\\/é\u2603"
        return "".join(rng.choice(alphabet) for _ in range(length))
    if choice == 3:
        return rng.choice([True, False])
    return None


def _random_json_value(rng: random.Random, depth: int = 0) -> Any:
    """Generate an arbitrary JSON-serializable value, optionally nested."""
    if depth >= 3 or rng.random() < 0.5:
        return _random_json_scalar(rng)
    if rng.random() < 0.5:
        size = rng.randrange(0, 4)
        return [_random_json_value(rng, depth + 1) for _ in range(size)]
    size = rng.randrange(0, 4)
    return {
        f"k{rng.randrange(0, 1000)}": _random_json_value(rng, depth + 1)
        for _ in range(size)
    }


def _random_json_dict(rng: random.Random) -> dict[str, Any]:
    """Generate an arbitrary JSON-serializable top-level object (dict)."""
    size = rng.randrange(0, 6)
    return {
        f"key_{i}_{rng.randrange(0, 1000)}": _random_json_value(rng)
        for i in range(size)
    }


# Values that ``json.dump`` cannot serialize; each forces a pre-replace failure.
def _non_serializable_value(rng: random.Random) -> Any:
    factories = [
        lambda: {1, 2, 3},
        lambda: b"raw-bytes",
        lambda: complex(1, 2),
        lambda: object(),
        lambda: {"nested": {"deeper": object()}},
    ]
    return rng.choice(factories)()


def _poisoned_payload(rng: random.Random) -> dict[str, Any]:
    """An otherwise-valid dict carrying a non-serializable value somewhere."""
    payload = _random_json_dict(rng)
    payload[f"poison_{rng.randrange(0, 1000)}"] = _non_serializable_value(rng)
    return payload


def test_property_atomic_write_failure_preserves_existing_target(
    tmp_path: Path,
) -> None:
    """A pre-replace failure leaves an existing target byte-for-byte unchanged."""
    for seed in range(EXAMPLES):
        rng = random.Random(seed)
        target = tmp_path / f"store_{seed}.json"
        tmp_sibling = target.with_name(f"{target.name}.tmp")

        prior = _random_json_dict(rng)
        atomic_write_json(target, prior)
        snapshot = target.read_bytes()

        payload = _poisoned_payload(rng)
        with pytest.raises(AtomicWriteError):
            atomic_write_json(target, payload)

        assert target.read_bytes() == snapshot, (
            f"target was modified by a failed write (seed={seed}, "
            f"prior={prior!r}, payload={payload!r})"
        )
        assert not tmp_sibling.exists(), (
            f"partial temp file left behind (seed={seed})"
        )


def test_property_atomic_write_failure_does_not_create_missing_target(
    tmp_path: Path,
) -> None:
    """A pre-replace failure never materializes a previously-absent target."""
    for seed in range(EXAMPLES):
        rng = random.Random(10_000 + seed)
        target = tmp_path / f"absent_{seed}.json"
        tmp_sibling = target.with_name(f"{target.name}.tmp")

        payload = _poisoned_payload(rng)
        with pytest.raises(AtomicWriteError):
            atomic_write_json(target, payload)

        assert not target.exists(), (
            f"failed write created a target that should not exist (seed={seed}, "
            f"payload={payload!r})"
        )
        assert not tmp_sibling.exists(), (
            f"partial temp file left behind (seed={seed})"
        )
