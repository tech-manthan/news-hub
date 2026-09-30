from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from ..models import SourceArticle, Topic
from ..research import BrowserArticleEnricher, BrowserBackedProvider, PublicRSSProvider, google_news_feed
from ..sources import NewsApiProvider, SourceConfig, select_topic

CATEGORY_PRESETS = {
    "trending": {"label": "Trending now", "query": "latest breaking news"},
    "india": {"label": "India", "query": "India latest news"},
    "world": {"label": "World", "query": "world latest news"},
    "technology": {"label": "Technology", "query": "technology AI startups"},
    "business": {"label": "Business", "query": "business markets economy"},
    "sports": {"label": "Sports", "query": "sports cricket football"},
    "entertainment": {"label": "Entertainment", "query": "entertainment movies music"},
    "science": {"label": "Science", "query": "science space research"},
}


@dataclass
class NewsAdapter:
    """The pipeline-facing niche contract, analogous to reel-engine's niche modules."""

    def get_candidates(self, opts: dict) -> list[SourceArticle]:
        query = opts.get("query", "technology")
        api_key = opts.get("newsapi_key", "")
        if api_key:
            provider = NewsApiProvider(SourceConfig(name="newsapi", api_key=api_key))
        else:
            provider = PublicRSSProvider(google_news_feed(opts.get("language", "en")))
            if opts.get("browser"):
                provider = BrowserBackedProvider(provider, BrowserArticleEnricher(("news.google.com",)))
        return provider.search(query)

    def is_good(self, item: SourceArticle) -> bool:
        return bool(item.title.strip() and item.url.startswith("https://") and item.description.strip())

    def enrich(self, item: SourceArticle, opts: dict) -> SourceArticle:
        if not opts.get("browser"):
            return item
        return BrowserArticleEnricher(("news.google.com",)).extract(item)

    def pick(self, opts: dict) -> Topic:
        api_key = opts.get("newsapi_key", "")
        if api_key:
            provider = NewsApiProvider(SourceConfig(name="newsapi", api_key=api_key))
        else:
            provider = PublicRSSProvider(google_news_feed(opts.get("language", "en")))
            if opts.get("browser"):
                provider = BrowserBackedProvider(provider, BrowserArticleEnricher(("news.google.com",)))
        return select_topic([provider], opts.get("query", "technology"), max_age=timedelta(hours=float(opts.get("max_age_hours", 48))), minimum_sources=int(opts.get("minimum_sources", 1)))

    def script_context(self, research: dict) -> dict:
        return {"brief": research.get("summary", ""), "sources": research.get("sources", []), "urls": [source["url"] for source in research.get("sources", [])]}
