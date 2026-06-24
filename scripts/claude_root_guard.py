#!/usr/bin/env python3
"""Claude Code hook: enforce repo-root execution for Project Tracker.

Blocks expensive/wrong-root commands when Claude runs from .claude/worktrees/*
instead of the real project root the user runs manually.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path("D:/Ibrahim/Projects/project_tracker").resolve()
WORKTREE_MARKER = "/.claude/worktrees/"

RISKY_COMMAND_RE = re.compile(
    r"(project_tracker\.main|pytest|npm\s+--prefix\s+frontend|npm\s+run|graphify|vite|svelte-check)",
    re.IGNORECASE,
)


def norm(value: str) -> str:
    return value.replace("\\", "/")


def hook(payload: dict) -> dict | None:
    tool = payload.get("tool_name", "")
    tool_input = payload.get("tool_input", {}) or {}

    cwd_s = norm(str(Path(os.getcwd()).resolve()))

    if tool == "Bash":
        command = str(tool_input.get("command", ""))
        command_s = norm(command)
        in_claude_worktree = WORKTREE_MARKER in cwd_s or WORKTREE_MARKER in command_s
        risky = bool(RISKY_COMMAND_RE.search(command))

        if in_claude_worktree and risky:
            return {
                "continue": False,
                "stopReason": (
                    "BLOCKED wrong-root run. App/tests/build/graphify must run from "
                    f"{REPO_ROOT}, not .claude/worktrees/*. User runs app with: "
                    "D:/Ibrahim/Projects/project_tracker/.venv/Scripts/python.exe -m main. "
                    "Re-run using repo-root absolute paths or start the session from repo root."
                ),
            }

        if in_claude_worktree:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": (
                        "ROOT GUARD: You are in a Claude worktree. For Project Tracker, "
                        f"app/tests/build/graphify must target {REPO_ROOT}. "
                        "Do not compare runtime UI from a worktree."
                    ),
                }
            }

    if tool in {"Write", "Edit", "NotebookEdit"}:
        file_path = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
        if WORKTREE_MARKER in norm(file_path):
            return {
                "continue": False,
                "stopReason": (
                    "BLOCKED worktree edit. Edit the real repo root instead: "
                    f"{REPO_ROOT}. Do not patch .claude/worktrees/* for Project Tracker."
                ),
            }

    return None


def main() -> int:
    try:
        result = hook(json.load(sys.stdin))
        if result:
            print(json.dumps(result))
    except Exception as exc:
        # Fail open: bad hook must not brick Claude, but still warn the model.
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "additionalContext": f"Root guard hook failed open: {exc}",
                    }
                }
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
