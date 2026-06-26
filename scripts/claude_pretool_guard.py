"""Claude PreToolUse guard for Project Tracker.

Reads hook JSON from stdin. Blocks dangerous Bash commands and runs the
repo pre-commit gate before Claude-initiated git commits.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path("D:/Ibrahim/Projects/project_tracker")


def deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
    )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    if payload.get("tool_name") != "Bash":
        return 0

    command = str(payload.get("tool_input", {}).get("command", ""))
    compact = " ".join(command.split())

    if re.search(r"\bgit\s+push\b.*\s-(?:f|[-\w]*force)", compact):
        deny("Blocked dangerous git push force command.")
        return 0

    if re.search(r"\brm\s+-[A-Za-z]*r[A-Za-z]*f|\brm\s+-[A-Za-z]*f[A-Za-z]*r", compact):
        deny("Blocked rm -rf. Use explicit safer delete path and approval.")
        return 0

    if re.search(r"\bgit\s+commit\b", compact):
        hook = ROOT / "scripts" / "pre-commit"
        result = subprocess.run(["bash", str(hook)], cwd=ROOT, text=True, capture_output=True)
        if result.returncode != 0:
            output = (result.stdout + result.stderr).strip()[-4000:]
            deny(f"pre-commit gate failed before git commit:\n{output}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
