from __future__ import annotations

import os
from pathlib import Path


def load_env(path: Path) -> None:
    """Small dependency-free .env loader for the local dashboard and CLI."""
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip().strip("'\"")
        os.environ.setdefault(key, value)
