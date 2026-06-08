# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Project Tracker DBS (Windows-only).

This spec bundles the Vite frontend output (``web/static/``) and the runtime
``assets/`` directory as data so the packaged pywebview app can serve the
Svelte UI and load email/command templates.

WINDOWS-ONLY. Do NOT run PyInstaller (or evaluate this spec) on Linux/macOS.
A platform guard below refuses evaluation on any non-Windows platform with a
clear "unsupported on this platform" message and a non-zero exit. Packaging is
a manual Windows step performed only after the Windows manual RC test gate
passes (see ``docs/windows-manual-test-checklist.md``).

Dependency policy: packaging must NOT add, remove, or upgrade any dependency.
PyInstaller is already declared in ``pyproject.toml`` / ``requirements.txt``.
Any dependency change requires explicit user approval before it is made.

Build (Windows, manual):
    python scripts/package.py
or directly:
    pyinstaller project_tracker_dbs.spec --noconfirm
"""

import sys
from pathlib import Path

# ── Platform guard: refuse to package on non-Windows ─────────────────────────
if sys.platform != "win32":
    raise SystemExit(
        "Packaging is unsupported on this platform ({0}). "
        "project_tracker_dbs.spec is Windows-only and PyInstaller must never be "
        "run on Linux/macOS. Refusing to package.".format(sys.platform)
    )

# ``__file__`` is not defined while PyInstaller execs a spec; SPECPATH is the
# directory containing this spec file (the repo root).
REPO_ROOT = Path(SPECPATH).resolve()  # noqa: F821  (SPECPATH injected by PyInstaller)

ENTRY_SCRIPT = str(REPO_ROOT / "project_tracker" / "main.py")
STATIC_DIR = REPO_ROOT / "web" / "static"
ASSETS_DIR = REPO_ROOT / "assets"

# Validate required data inputs exist before building.
for required in (STATIC_DIR, ASSETS_DIR):
    if not required.is_dir():
        raise SystemExit(
            "Missing required data directory for packaging: {0}. "
            "Run `npm --prefix frontend run build` before packaging so "
            "`web/static/` exists.".format(required)
        )

# Bundle web/static and assets as data, preserving their relative layout so the
# pywebview HTTP server and template loaders resolve the same paths at runtime.
datas = [
    (str(STATIC_DIR), "web/static"),
    (str(ASSETS_DIR), "assets"),
]

# pywebview / Windows integrations are imported lazily and guarded at runtime;
# list them here so PyInstaller bundles them even when imports are deferred.
hiddenimports = [
    "webview",
    "webview.platforms.edgechromium",
    "apscheduler",
    "apscheduler.schedulers.background",
    "dateutil",
    "send2trash",
]


block_cipher = None


a = Analysis(  # noqa: F821  (PyInstaller injects Analysis)
    [ENTRY_SCRIPT],
    pathex=[str(REPO_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt6"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ProjectTrackerDBS",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ProjectTrackerDBS",
)
