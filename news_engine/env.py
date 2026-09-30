from __future__ import annotations

import os
import json
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
    settings_path = path.parent / "data" / "settings.json"
    try:
        saved = json.loads(settings_path.read_text())
    except (OSError, ValueError):
        saved = {}
    allowed = {
        "NEWS_QUERY", "NEWS_LANGUAGE", "NEWS_MAX_AGE_HOURS", "NEWS_MINIMUM_SOURCES",
        "PUBLIC_RESEARCH_BROWSER", "REMOTION_RENDER", "NEWS_UI_PORT", "NEWS_UI_OPEN",
        "ENGLISH_TTS_VOICE", "HINDI_TTS_VOICE", "ENGLISH_TTS_SPEED", "HINDI_TTS_SPEED",
        "NEWS_BG_PRESET", "NEWS_FONT", "NEWS_TEMPLATE", "AUTO_REPLY_KEYWORD", "AUTO_REPLY_TEXT",
    }
    for key, value in saved.items():
        if key in allowed:
            os.environ[key] = str(value)
