from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class SourceArticle:
    id: str
    provider: str
    publisher: str
    title: str
    description: str
    url: str
    published_at: str

    def published_datetime(self) -> datetime:
        return datetime.fromisoformat(self.published_at.replace("Z", "+00:00")).astimezone(timezone.utc)


@dataclass
class Topic:
    id: str
    query: str
    headline: str
    summary: str
    sources: list[SourceArticle]
    confidence: float = 0.0
    approval_status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ShortScript:
    language: str
    title: str
    narration: str
    source_ids: tuple[str, ...]
    approval_status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"source_ids": list(self.source_ids)}
