"""Safe delete service."""

from __future__ import annotations

import sys
from pathlib import Path


class SafeDeleteService:
    """Move paths to Windows Recycle Bin."""

    unsupported_message = "Delete is only supported on Windows target"

    def delete_to_trash(self, path: Path) -> None:
        if sys.platform != "win32":
            raise RuntimeError(self.unsupported_message)
        import send2trash

        send2trash.send2trash(str(path))
