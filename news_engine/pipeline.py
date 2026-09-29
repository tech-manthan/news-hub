from __future__ import annotations

import json
from pathlib import Path

from .models import Topic
from .scripts import generate_bilingual
from .store import NewsStore


def write_topic_artifacts(topic: Topic, output_dir: Path, store: NewsStore) -> dict[str, Path]:
    """Write research and both scripts; refuse to label artifacts publishable before approval."""
    store.save_topic(topic)
    output_dir.mkdir(parents=True, exist_ok=True)
    research_path = output_dir / "research.json"
    research_path.write_text(json.dumps(topic.to_dict(), indent=2, ensure_ascii=False))
    scripts = generate_bilingual(topic)
    paths: dict[str, Path] = {"research": research_path}
    for language, script in scripts.items():
        path = output_dir / f"spec_{language}.json"
        path.write_text(json.dumps(script.to_dict(), indent=2, ensure_ascii=False))
        paths[language] = path
    return paths


def write_research(topic: Topic, output_dir: Path, store: NewsStore) -> Path:
    store.save_topic(topic)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "research.json"
    path.write_text(json.dumps(topic.to_dict(), indent=2, ensure_ascii=False))
    return path


def require_approved(store: NewsStore, topic: Topic) -> None:
    if topic.confidence < 0.6:
        raise PermissionError("topic confidence is below the publish threshold; obtain more independent sources")
    if not store.is_approved(topic.id):
        raise PermissionError(f"topic {topic.id} requires human approval before publishing")
