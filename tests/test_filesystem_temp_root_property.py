"""Property-based test for Property 1: No destructive op escapes Temp_Root.

**Validates: Requirements 2.1, 2.9**

For any generated target path, a create / move / rename / delete operation
either resolves strictly within the ``Temp_Root`` base or is rejected (raising
``PathOutsideBaseError``) leaving the filesystem contents unchanged.

The project's locked dependency baseline does not include ``hypothesis`` (and
adding dependencies is forbidden by the release-candidate rules), so the
property is exercised with a deterministic, seeded generator that produces a
diverse population of target paths -- some nested strictly within the base and
some that escape it via ``..`` traversal, sibling locations, or the base
itself. Each generated example is run as a separate parametrized case so a
counterexample is reported directly by pytest.

The property is checked against an independent containment oracle
(``_is_strictly_within``): the destructive helpers must reject every target the
oracle deems outside the base (with the filesystem left unchanged and, for
deletes, ``send2trash`` never invoked), and must never reject a target the
oracle deems strictly within the base.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from project_tracker.core.exceptions import PathOutsideBaseError
from project_tracker.infrastructure import filesystem

# Names used to build path segments. Deliberately disjoint from the seeded
# fixture file names so a generated destination never collides with setup data.
_SEGMENT_NAMES = (
    "alpha",
    "beta",
    "child",
    "nested",
    "proj_dir",
    "sub",
    "deeper",
    "leaf",
)


def _generate_recipes(count: int = 200, seed: int = 1337) -> list[list[str]]:
    """Generate a diverse, deterministic population of path-segment recipes.

    A recipe is a list of path segments joined onto the base. Segments may be
    ordinary names or ``..`` traversal tokens, producing both contained and
    escaping targets. The empty recipe represents the base itself (which must be
    rejected as not strictly within itself).
    """
    rng = random.Random(seed)
    recipes: list[list[str]] = [
        [],  # the base itself -> rejected
        [".."],  # parent -> escape
        ["..", "outside"],  # escape into a sibling tree
        ["a", "..", "..", "escaped"],  # climb above the base
        ["sub", "..", "sibling"],  # ".." that still resolves within base
        ["a", "b", "c", "d"],  # deep but contained
        ["..", "..", "Temp_Root", "tricky"],  # re-enters a same-named tree, escapes
    ]
    for _ in range(count):
        depth = rng.randint(1, 5)
        segments: list[str] = []
        for _ in range(depth):
            if rng.random() < 0.3:
                segments.append("..")
            else:
                segments.append(rng.choice(_SEGMENT_NAMES))
        recipes.append(segments)
    return recipes


_RECIPES = _generate_recipes()
_IDS = [f"{i:03d}:{'/'.join(r) if r else '<base>'}" for i, r in enumerate(_RECIPES)]


def _target_for(base: Path, recipe: list[str]) -> Path:
    return base.joinpath(*recipe) if recipe else base


def _snapshot(root: Path) -> dict[str, bytes | None]:
    """Capture every path under ``root`` with file contents for mutation checks."""
    snap: dict[str, bytes | None] = {}
    for path in sorted(root.rglob("*")):
        rel = str(path.relative_to(root))
        snap[rel] = path.read_bytes() if path.is_file() else None
    return snap


def _is_strictly_within(base: Path, target: Path) -> bool:
    """Independent oracle: does ``target`` resolve strictly within ``base``?"""
    base_resolved = base.resolve()
    target_resolved = Path(target).resolve()
    return target_resolved != base_resolved and target_resolved.is_relative_to(base_resolved)


def _seed_base(tmp_path: Path) -> Path:
    """Create a Temp_Root with some contents plus an outside marker file."""
    base = tmp_path / "Temp_Root"
    base.mkdir()
    (base / "keep.txt").write_text("original", encoding="utf-8")
    (tmp_path / "outside_marker.txt").write_text("safe", encoding="utf-8")
    return base


@pytest.mark.parametrize("recipe", _RECIPES, ids=_IDS)
def test_property_create_directory_contained_or_rejected(
    tmp_path: Path, recipe: list[str]
) -> None:
    base = _seed_base(tmp_path)
    target = _target_for(base, recipe)
    expected_within = _is_strictly_within(base, target)
    before = _snapshot(tmp_path)

    try:
        result = filesystem.create_directory(base, target)
    except PathOutsideBaseError:
        assert not expected_within, (
            f"guard rejected a contained target for recipe {recipe!r}"
        )
        assert _snapshot(tmp_path) == before, (
            f"rejected create mutated filesystem for recipe {recipe!r}"
        )
        return

    assert expected_within, f"guard allowed an escaping target for recipe {recipe!r}"
    assert _is_strictly_within(base, result), (
        f"create succeeded but result {result!r} escaped base for {recipe!r}"
    )
    assert target.exists(), f"create succeeded but target {target!r} missing for {recipe!r}"


@pytest.mark.parametrize("recipe", _RECIPES, ids=_IDS)
def test_property_move_path_contained_or_rejected(
    tmp_path: Path, recipe: list[str]
) -> None:
    base = _seed_base(tmp_path)
    source = base / "source_item.txt"
    source.write_text("payload", encoding="utf-8")
    target = _target_for(base, recipe)
    expected_within = _is_strictly_within(base, target)
    before = _snapshot(tmp_path)

    try:
        result = filesystem.move_path(base, source, target)
    except PathOutsideBaseError:
        assert not expected_within, (
            f"guard rejected a contained destination for recipe {recipe!r}"
        )
        assert _snapshot(tmp_path) == before, (
            f"rejected move mutated filesystem for recipe {recipe!r}"
        )
        return
    except OSError:
        # The containment guard permitted the (contained) destination; the move
        # then failed for an unrelated filesystem reason (e.g. a missing
        # intermediate directory). That is not a containment escape -- the only
        # property under test is that the guard never rejects a contained path
        # nor permits an escaping one.
        assert expected_within, (
            f"guard permitted an escaping destination for recipe {recipe!r}"
        )
        return

    assert expected_within, f"guard allowed an escaping destination for recipe {recipe!r}"
    assert _is_strictly_within(base, result), (
        f"move succeeded but destination {result!r} escaped base for {recipe!r}"
    )


@pytest.mark.parametrize("recipe", _RECIPES, ids=_IDS)
def test_property_rename_path_contained_or_rejected(
    tmp_path: Path, recipe: list[str]
) -> None:
    base = _seed_base(tmp_path)
    source = base / "rename_src.txt"
    source.write_text("payload", encoding="utf-8")
    target = _target_for(base, recipe)
    expected_within = _is_strictly_within(base, target)
    before = _snapshot(tmp_path)

    try:
        result = filesystem.rename_path(base, source, target)
    except PathOutsideBaseError:
        assert not expected_within, (
            f"guard rejected a contained destination for recipe {recipe!r}"
        )
        assert _snapshot(tmp_path) == before, (
            f"rejected rename mutated filesystem for recipe {recipe!r}"
        )
        return
    except OSError:
        assert expected_within, (
            f"guard permitted an escaping destination for recipe {recipe!r}"
        )
        return

    assert expected_within, f"guard allowed an escaping destination for recipe {recipe!r}"
    assert _is_strictly_within(base, result), (
        f"rename succeeded but destination {result!r} escaped base for {recipe!r}"
    )


@pytest.mark.parametrize("recipe", _RECIPES, ids=_IDS)
def test_property_delete_contained_or_rejected(
    tmp_path: Path, recipe: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    base = _seed_base(tmp_path)
    target = _target_for(base, recipe)
    expected_within = _is_strictly_within(base, target)

    trashed: list[str] = []
    import send2trash

    monkeypatch.setattr(send2trash, "send2trash", lambda p: trashed.append(p))

    before = _snapshot(tmp_path)
    try:
        filesystem.send_to_recycle_bin(target, base=base)
    except PathOutsideBaseError:
        assert not expected_within, (
            f"guard rejected a contained delete target for recipe {recipe!r}"
        )
        assert trashed == [], f"rejected delete still invoked send2trash for {recipe!r}"
        assert _snapshot(tmp_path) == before, (
            f"rejected delete mutated filesystem for recipe {recipe!r}"
        )
        return

    assert expected_within, f"guard allowed an escaping delete target for recipe {recipe!r}"
    assert trashed == [str(target)], (
        f"delete routed {trashed!r} instead of {str(target)!r} for {recipe!r}"
    )
