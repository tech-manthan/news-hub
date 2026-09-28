from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from urllib.parse import urlparse

from .models import SourceArticle, Topic


class SourceAuthError(RuntimeError):
    """Raised when an authenticated source is not configured correctly."""


class SourceTransport(Protocol):
    def get_json(self, url: str, params: dict[str, str], headers: dict[str, str], timeout: float) -> dict[str, Any]: ...


class RequestsTransport:
    def get_json(self, url: str, params: dict[str, str], headers: dict[str, str], timeout: float) -> dict[str, Any]:
        import requests

        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()


@dataclass(frozen=True)
class SourceConfig:
    name: str
    api_key: str
    endpoint: str = "https://newsapi.org/v2/everything"
    allowed_domains: tuple[str, ...] = ()


class NewsApiProvider:
    """NewsAPI adapter. It never fetches a URL outside the provider response allowlist."""

    def __init__(self, config: SourceConfig, transport: SourceTransport | None = None):
        if not config.api_key.strip():
            raise SourceAuthError(f"{config.name} requires an API key")
        if urlparse(config.endpoint).scheme != "https":
            raise SourceAuthError("news provider endpoint must use HTTPS")
        self.config = config
        self.transport = transport or RequestsTransport()

    def search(self, query: str, *, language: str = "en", page_size: int = 20) -> list[SourceArticle]:
        payload = self.transport.get_json(
            self.config.endpoint,
            {"q": query, "language": language, "pageSize": str(page_size), "sortBy": "publishedAt", "apiKey": self.config.api_key},
            {"Accept": "application/json"},
            30,
        )
        if payload.get("status") not in (None, "ok"):
            raise RuntimeError(f"{self.config.name} rejected the request: {payload.get('message', 'unknown error')}")
        articles: list[SourceArticle] = []
        for raw in payload.get("articles", []):
            url = str(raw.get("url", ""))
            if not url or not _allowed_url(url, self.config.allowed_domains):
                continue
            title = _clean(str(raw.get("title", "")))
            description = _clean(str(raw.get("description", "")))
            if not title or not raw.get("publishedAt"):
                continue
            articles.append(SourceArticle(
                id=hashlib.sha256(url.encode()).hexdigest()[:16],
                provider=self.config.name,
                publisher=str((raw.get("source") or {}).get("name") or "Unknown publisher"),
                title=title,
                description=description,
                url=url,
                published_at=str(raw["publishedAt"]),
            ))
        return articles


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _allowed_url(url: str, domains: tuple[str, ...]) -> bool:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        return False
    return not domains or any(parsed.hostname == domain or parsed.hostname.endswith("." + domain) for domain in domains)


def select_topic(
    providers: list[NewsApiProvider],
    query: str,
    *,
    now: datetime | None = None,
    max_age: timedelta = timedelta(days=2),
    minimum_sources: int = 1,
) -> Topic:
    if not providers:
        raise ValueError("at least one authenticated news provider is required")
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    found: list[SourceArticle] = []
    for provider in providers:
        found.extend(provider.search(query))
    unique: dict[str, SourceArticle] = {}
    for article in found:
        if now - article.published_datetime() <= max_age:
            unique.setdefault(article.url, article)
    articles = sorted(unique.values(), key=lambda item: item.published_datetime(), reverse=True)
    if len(articles) < minimum_sources:
        raise ValueError(f"not enough fresh authenticated sources for {query!r}")
    headline = articles[0].title
    summary = next((a.description for a in articles if a.description), headline)
    source_count = len({a.publisher for a in articles})
    provider_count = len({a.provider for a in articles})
    confidence = min(1.0, 0.45 + min(source_count, 3) * 0.15 + min(provider_count, 2) * 0.125 + (0.1 if len(articles) >= 2 else 0))
    return Topic(
        id=hashlib.sha256((query + "|" + "|".join(a.id for a in articles)).encode()).hexdigest()[:16],
        query=query,
        headline=headline,
        summary=summary,
        sources=articles,
        confidence=round(confidence, 3),
    )
