"""Property-based test for Property 6: name validation is total.

Design Correctness Property 6 (prd-completion design.md):
    For any candidate name, the validator returns a definite valid/invalid
    result and never accepts forbidden characters, reserved device names,
    trailing space/dot, empty, or >255-char names.

**Validates: Requirements 5.1, 6.2**

This property is exercised against both name validators in the codebase:

* ``core.rules.validate_windows_folder_name`` — folder names,
  forbidden chars ``\\ / : * ? " < > |``, raises ``InvalidFolderNameError``.
* ``infrastructure.filesystem.validate_file_name`` — file
  names, forbidden chars ``< > : " / \\ | ? *``, raises
  ``InvalidFileNameError``.

Implementation note
-------------------
The PRD v3.1 dependency baseline does not include ``hypothesis`` and the
release-candidate hard rules forbid adding dependencies, so this property test
uses the standard library ``random`` module to generate a large, diverse space
of candidate names. Generation is seeded per-example and the failing
seed/example is surfaced on assertion failure so any counterexample is
reproducible. No filesystem is touched: both validators are pure functions that
either return ``None`` (valid) or raise their documented exception (invalid).
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

import pytest

from core.exceptions import (
    InvalidFileNameError,
    InvalidFolderNameError,
)
from core.rules import (
    WINDOWS_INVALID_FOLDER_CHARS,
    WINDOWS_RESERVED_NAMES,
    validate_windows_folder_name,
)
from infrastructure.filesystem import (
    FILE_NAME_INVALID_CHARS,
    MAX_FILE_NAME_LENGTH,
    validate_file_name,
)

# Number of randomly generated examples per validator per property run.
EXAMPLE_COUNT = 400

# Characters that are always safe in both validators (no forbidden chars, not
# space/dot which could become a trailing violation handled separately).
_SAFE_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_()[]{}#$%&+=,;'~"

# Unicode characters that are not forbidden by either validator. Used to ensure
# the validators stay total over non-ASCII input.
_UNICODE_CHARS = "проекتمشروع项目-éüñ漢字🚀"

# The union of every character either validator treats as forbidden. A name
# free of these (and not otherwise invalid) must be accepted by both.
_ALL_FORBIDDEN_CHARS = WINDOWS_INVALID_FOLDER_CHARS | FILE_NAME_INVALID_CHARS

_RESERVED_SAMPLES = sorted(WINDOWS_RESERVED_NAMES)


@dataclass(frozen=True)
class _Validator:
    """A name validator paired with the exception it raises on invalid input."""

    name: str
    func: Callable[[str], None]
    error: type[Exception]
    forbidden_chars: frozenset[str]
    # Req 5.1 forbids a trailing space/dot for folder names; Req 6.2 does NOT
    # impose that rule for file names (it lists only empty, 1-255, forbidden
    # chars, and reserved device names). The flag keeps the expected-verdict
    # logic faithful to each validator's authoritative requirement.
    rejects_trailing_space_dot: bool


_VALIDATORS = (
    _Validator(
        name="validate_windows_folder_name",
        func=validate_windows_folder_name,
        error=InvalidFolderNameError,
        forbidden_chars=WINDOWS_INVALID_FOLDER_CHARS,
        rejects_trailing_space_dot=True,
    ),
    _Validator(
        name="validate_file_name",
        func=validate_file_name,
        error=InvalidFileNameError,
        forbidden_chars=FILE_NAME_INVALID_CHARS,
        rejects_trailing_space_dot=False,
    ),
)


def _rand_safe_name(rng: random.Random) -> str:
    """A plausibly-valid name built only from safe (non-forbidden) chars.

    The result may still be invalid (e.g. it could randomly match a reserved
    stem like ``CON``) which is fine: the property only asserts totality and the
    expected-acceptance reasoning is computed from the name itself.
    """
    length = rng.randint(1, 30)
    pool = _SAFE_CHARS + (_UNICODE_CHARS if rng.random() < 0.3 else "")
    return "".join(rng.choice(pool) for _ in range(length))


def _make_candidate(rng: random.Random) -> str:
    """Generate one candidate name from a diverse space of name shapes."""
    kind = rng.randrange(11)

    if kind == 0:
        # Empty name.
        return ""
    if kind == 1:
        # Oversized name (> 255 chars).
        return "a" * rng.randint(256, 600)
    if kind == 2:
        # Otherwise-valid name with a trailing space or dot.
        return _rand_safe_name(rng) + rng.choice([" ", "."])
    if kind == 3:
        # Name containing at least one forbidden char (from either set).
        base = list(_rand_safe_name(rng))
        forbidden = rng.choice(sorted(_ALL_FORBIDDEN_CHARS))
        base.insert(rng.randint(0, len(base)), forbidden)
        return "".join(base)
    if kind == 4:
        # A reserved device name, exact.
        return rng.choice(_RESERVED_SAMPLES)
    if kind == 5:
        # A reserved device name with an extension (stem is still reserved).
        return rng.choice(_RESERVED_SAMPLES) + rng.choice([".txt", ".log", ".DAT"])
    if kind == 6:
        # A reserved name in mixed/lower case (matching is case-insensitive).
        return rng.choice(_RESERVED_SAMPLES).lower()
    if kind == 7:
        # Unicode-heavy name.
        length = rng.randint(1, 30)
        return "".join(rng.choice(_UNICODE_CHARS) for _ in range(length))
    if kind == 8:
        # Boundary lengths around the 255 limit.
        return "a" * rng.choice([254, 255, 256])
    if kind == 9:
        # Name with internal (non-trailing) space/dot, otherwise safe.
        core = _rand_safe_name(rng)
        return core + rng.choice([" ", "."]) + _rand_safe_name(rng)
    # Default: a plausibly-valid safe name.
    return _rand_safe_name(rng)


def _expected_invalid(name: str, validator: _Validator) -> bool:
    """Return True iff ``name`` must be rejected by ``validator``.

    Mirrors the documented rules so the test can assert not just totality but
    correctness of the valid/invalid verdict for every candidate.
    """
    if name == "":
        return True
    if len(name) > MAX_FILE_NAME_LENGTH:  # 255 for both validators
        return True
    if validator.rejects_trailing_space_dot and name[-1] in {" ", "."}:
        return True
    if any(ch in validator.forbidden_chars for ch in name):
        return True
    stem = name.split(".", 1)[0].upper()
    if stem in WINDOWS_RESERVED_NAMES:
        return True
    return False


@pytest.mark.parametrize("validator", _VALIDATORS, ids=lambda v: v.name)
def test_name_validation_is_total(validator: _Validator) -> None:
    """Property 6: validation is total and never accepts an invalid name.

    For every generated candidate the validator must produce a definite
    verdict: either it returns ``None`` (valid) or it raises its documented
    exception (invalid). It must never raise any other exception type, and it
    must never accept a name that violates a documented rule.
    """
    for example_index in range(EXAMPLE_COUNT):
        seed = example_index
        rng = random.Random(seed)
        name = _make_candidate(rng)
        should_be_invalid = _expected_invalid(name, validator)

        try:
            result = validator.func(name)
        except validator.error:
            # Definite "invalid" verdict via the documented exception.
            assert should_be_invalid, (
                f"{validator.name} rejected a name that should be valid for "
                f"seed={seed}: {name!r}"
            )
            continue
        except Exception as exc:  # pragma: no cover - totality violation
            raise AssertionError(
                f"{validator.name} raised an undocumented {type(exc).__name__} "
                f"for seed={seed}, name={name!r}: {exc}"
            ) from exc

        # No exception -> definite "valid" verdict. It must return None and the
        # name must not violate any documented rule (never accepts forbidden/
        # reserved/trailing/empty/oversized names).
        assert result is None, (
            f"{validator.name} returned a non-None value {result!r} for "
            f"seed={seed}, name={name!r}"
        )
        assert not should_be_invalid, (
            f"{validator.name} ACCEPTED an invalid name for seed={seed}: "
            f"{name!r}"
        )


@pytest.mark.parametrize("validator", _VALIDATORS, ids=lambda v: v.name)
def test_each_forbidden_char_is_always_rejected(validator: _Validator) -> None:
    """Every forbidden character causes rejection regardless of placement."""
    for seed, ch in enumerate(sorted(validator.forbidden_chars)):
        rng = random.Random(1000 + seed)
        prefix = _rand_safe_name(rng)
        suffix = _rand_safe_name(rng)
        name = f"{prefix}{ch}{suffix}"
        with pytest.raises(validator.error):
            validator.func(name)


@pytest.mark.parametrize("validator", _VALIDATORS, ids=lambda v: v.name)
def test_reserved_names_always_rejected(validator: _Validator) -> None:
    """Reserved device names are rejected bare, extended, and case-folded."""
    for reserved in _RESERVED_SAMPLES:
        for candidate in (reserved, reserved.lower(), f"{reserved}.txt"):
            with pytest.raises(validator.error):
                validator.func(candidate)
