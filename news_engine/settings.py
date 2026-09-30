from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SETTINGS_PATH = Path("data/settings.json")
SETTING_KEYS = (
    "NEWS_QUERY", "NEWS_LANGUAGE", "NEWS_MAX_AGE_HOURS", "NEWS_MINIMUM_SOURCES",
    "PUBLIC_RESEARCH_BROWSER", "REMOTION_RENDER", "NEWS_UI_PORT", "NEWS_UI_OPEN",
    "ENGLISH_TTS_VOICE", "HINDI_TTS_VOICE", "AUTO_REPLY_KEYWORD", "AUTO_REPLY_TEXT",
)


def read_settings(path: Path = SETTINGS_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        raw: Any = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return {key: str(raw[key]) for key in SETTING_KEYS if key in raw}


def write_settings(values: dict[str, Any], path: Path = SETTINGS_PATH) -> dict[str, str]:
    clean = {key: str(values[key]) for key in SETTING_KEYS if key in values and values[key] is not None}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean, indent=2, ensure_ascii=False))
    return clean
