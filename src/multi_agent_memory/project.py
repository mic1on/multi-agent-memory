"""Best-effort project identity detection without requiring Git."""
from __future__ import annotations
import os
from pathlib import Path

def detect_project(cwd: str | Path | None = None) -> tuple[str, Path] | None:
    """Return a stable local project name and root for a directory, if found."""
    current = Path(cwd or os.getcwd()).expanduser().resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate.name, candidate
    return None
