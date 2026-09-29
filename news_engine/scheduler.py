from __future__ import annotations

import plistlib
import shlex
import sys
from pathlib import Path


def write_launch_agent(path: Path, query: str, hour: int = 9, minute: int = 0) -> Path:
    """Create a macOS LaunchAgent that builds research and scripts; it never publishes."""
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("hour must be 0-23 and minute must be 0-59")
    root = Path(__file__).resolve().parent.parent
    run = root / "run.py"
    command = [sys.executable, str(run), "--query", query, "--stages", "research,script,assets,voice,render"]
    payload = {
        "Label": "com.newsengine.build",
        "ProgramArguments": command,
        "WorkingDirectory": str(root),
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "StandardOutPath": str(root / "data" / "scheduler.log"),
        "StandardErrorPath": str(root / "data" / "scheduler.error.log"),
        "RunAtLoad": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(plistlib.dumps(payload))
    return path


def launch_agent_command(path: Path) -> str:
    return f"launchctl load {shlex.quote(str(path))}"
