from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote_plus, urlparse
from xml.etree import ElementTree

from .models import SourceArticle


@dataclass(frozen=True)
class PublicFeed:
    """An explicitly configured public feed. No login, paywall, or arbitrary URL crawling."""

    name: str
    rss_url_template: str
    allowed_domains: tuple[str, ...]

    def url_for(self, query: str) -> str:
        return self.rss_url_template.format(query=quote_plus(query))


class PublicRSSProvider:
    def __init__(self, feed: PublicFeed, fetcher=None):
        self.feed = feed
        self.fetcher = fetcher or self._fetch

    def _fetch(self, url: str) -> str:
        import requests

        response = requests.get(url, headers={"User-Agent": "news-engine/0.1 (+local research)"}, timeout=30)
        response.raise_for_status()
        return response.text

    def search(self, query: str, *, limit: int = 20) -> list[SourceArticle]:
        root = ElementTree.fromstring(self.fetcher(self.feed.url_for(query)))
        articles: list[SourceArticle] = []
        for item in root.findall(".//item")[:limit]:
            title = _clean(item.findtext("title", ""))
            url = _clean(item.findtext("link", ""))
            if not title or not _allowed(url, self.feed.allowed_domains):
                continue
            published = _published(item.findtext("pubDate", ""))
            description = _clean(item.findtext("description", ""))
            source = item.find("source")
            publisher = _clean(source.text if source is not None else "") or urlparse(url).hostname or self.feed.name
            articles.append(SourceArticle(
                id=hashlib.sha256(url.encode()).hexdigest()[:16], provider=self.feed.name,
                publisher=publisher, title=title, description=description, url=url,
                published_at=published,
            ))
        return articles


def google_news_feed(language: str = "en") -> PublicFeed:
    if language == "hi":
        return PublicFeed("google-news-public-hi", "https://news.google.com/rss/search?q={query}&hl=hi&gl=IN&ceid=IN:hi", ("news.google.com",))
    return PublicFeed("google-news-public-en", "https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en", ("news.google.com",))


class BrowserArticleEnricher:
    """Optional Playwright fallback for configured article pages, kept intentionally narrow."""

    def __init__(self, allowed_domains: tuple[str, ...], timeout_ms: int = 30_000):
        self.allowed_domains = allowed_domains
        self.timeout_ms = timeout_ms

    def extract(self, article: SourceArticle) -> SourceArticle:
        if not _allowed(article.url, self.allowed_domains):
            raise ValueError(f"browser source is not allowlisted: {article.url}")
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Install browser research with `python -m pip install playwright` and run `playwright install chromium`") from exc
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(article.url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                text = re.sub(r"\s+", " ", page.locator("body").inner_text(timeout=self.timeout_ms)).strip()
                description = text[:600] if text else article.description
                title = _clean(page.title()) or article.title
                return SourceArticle(article.id, article.provider, article.publisher, title, description, article.url, article.published_at)
            finally:
                browser.close()


class BrowserBackedProvider:
    def __init__(self, provider, enricher: BrowserArticleEnricher):
        self.provider = provider
        self.enricher = enricher

    def search(self, query: str, **kwargs) -> list[SourceArticle]:
        return [self.enricher.extract(article) for article in self.provider.search(query, **kwargs)]


def _allowed(url: str, domains: tuple[str, ...]) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.hostname) and any(parsed.hostname == domain or parsed.hostname.endswith("." + domain) for domain in domains)


def _published(value: str) -> str:
    if value:
        try:
            return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        except (TypeError, ValueError, OverflowError):
            pass
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", value or "")).strip()
