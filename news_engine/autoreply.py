from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AutoReplyConfig:
    keyword: str
    reply_template: str
    state_path: Path

    def __post_init__(self) -> None:
        if not self.keyword.strip():
            raise ValueError("auto-reply keyword cannot be empty")
        if not self.reply_template.strip():
            raise ValueError("auto-reply text cannot be empty")


def load_state(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return set(json.loads(path.read_text()).get("replied_comment_ids", []))


def save_state(path: Path, ids: set[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"replied_comment_ids": sorted(ids)}, indent=2))


def matching_comments(comments: list[dict], config: AutoReplyConfig) -> list[dict]:
    """Deterministic substring matching; the bot never asks an LLM to choose targets."""
    replied = load_state(config.state_path)
    return [comment for comment in comments if comment.get("id") not in replied and config.keyword.casefold() in str(comment.get("text", "")).casefold()]


def mark_replied(config: AutoReplyConfig, comment_id: str) -> None:
    ids = load_state(config.state_path)
    ids.add(comment_id)
    save_state(config.state_path, ids)
