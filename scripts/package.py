#!/usr/bin/env python3
"""Windows-only packaging entry point with a non-Windows refuse guard.

This script is the single supported way to build a distributable package of
Project Tracker DBS. Packaging uses PyInstaller and the repo-root spec file
``project_tracker_dbs.spec``.

Hard boundaries (see ``.kiro/steering/manual-test-and-packaging.md`` and
``release-candidate-rules.md``):

* Packaging runs ONLY on Windows, and ONLY after the Windows manual RC test
  gate has passed (``docs/windows-manual-test-checklist.md``).
* PyInstaller MUST NOT be run on Linux. This script's refuse path is the guard:
  on any non-Windows platform it prints a clear "unsupported on this platform"
  message and exits non-zero WITHOUT importing or invoking PyInstaller.
* Packaging MUST NOT add, remove, or upgrade any dependency. PyInstaller is
  already declared in ``pyproject.toml`` / ``requirements.txt``. Any dependency
  change requires explicit user approval before it is made.

The refuse path IS Linux-runnable (and is exercised by automated checks); the
Windows build path is manual and is never triggered on Linux.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Exit codes
EXIT_OK = 0
EXIT_UNSUPPORTED_PLATFORM = 2
EXIT_MISSING_ARTIFACTS = 3

REPO_ROOT = Path(__file__).resolve().parent.parent
SPEC_FILE = REPO_ROOT / "project_tracker_dbs.spec"
STATIC_DIR = REPO_ROOT / "web" / "static"
ASSETS_DIR = REPO_ROOT / "assets"

UNSUPPORTED_MESSAGE = (
    "Packaging is unsupported on this platform ({platform}). "
    "Project Tracker DBS can only be packaged on Windows (sys.platform == 'win32'), "
    "and only after the Windows manual RC test gate has passed. "
    "PyInstaller must never be run on Linux/macOS. Refusing to package."
)

DEPENDENCY_APPROVAL_REMINDER = (
    "Reminder: packaging must NOT add, remove, or upgrade any dependency. "
    "PyInstaller is already declared. Any dependency change requires explicit "
    "user approval before it is made."
)


def is_windows() -> bool:
    """Return True only on Windows."""
    return sys.platform == "win32"


def _verify_build_inputs() -> list[str]:
    """Return a list of human-readable problems with required build inputs."""
    problems: list[str] = []
    if not SPEC_FILE.is_file():
        problems.append(f"Missing PyInstaller spec: {SPEC_FILE}")
    if not STATIC_DIR.is_dir():
        problems.append(
            f"Missing frontend build output: {STATIC_DIR} "
            "(run `npm --prefix frontend run build` first)"
        )
    if not ASSETS_DIR.is_dir():
        problems.append(f"Missing assets directory: {ASSETS_DIR}")
    return problems


def package(argv: list[str] | None = None) -> int:
    """Run the platform guard and, on Windows only, the PyInstaller build.

    On any non-Windows platform this refuses to package, prints a clear
    message to stderr, and returns a non-zero exit code without importing or
    invoking PyInstaller.
    """
    argv = list(sys.argv[1:] if argv is None else argv)

    # ── Platform guard (refuse path) ─────────────────────────────────────
    if not is_windows():
        print(UNSUPPORTED_MESSAGE.format(platform=sys.platform), file=sys.stderr)
        return EXIT_UNSUPPORTED_PLATFORM

    # ── Windows build path (manual only; never reached on Linux) ─────────
    print(DEPENDENCY_APPROVAL_REMINDER, file=sys.stderr)

    problems = _verify_build_inputs()
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        return EXIT_MISSING_ARTIFACTS

    # Import PyInstaller lazily so this module stays importable on Linux.
    import PyInstaller.__main__ as pyinstaller_main  # noqa: PLC0415

    pyinstaller_args = [str(SPEC_FILE), "--noconfirm", *argv]
    print(f"Running PyInstaller: {' '.join(pyinstaller_args)}", file=sys.stderr)
    pyinstaller_main.run(pyinstaller_args)
    return EXIT_OK


def main() -> int:
    """Console entry point."""
    return package()


if __name__ == "__main__":
    raise SystemExit(main())
