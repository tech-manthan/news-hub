from __future__ import annotations

import argparse
import os
from datetime import timedelta
from pathlib import Path

from news_engine.pipeline import write_topic_artifacts
from news_engine.sources import NewsApiProvider, SourceConfig, select_topic
from news_engine.store import NewsStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate authenticated English and Hindi news-short artifacts")
    parser.add_argument("--query", default=os.getenv("NEWS_QUERY", "technology"))
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--dry-run", action="store_true", help="fetch and score a topic without writing artifacts")
    parser.add_argument("--approve", action="store_true", help="approve the fetched topic for a later publishing stage")
    args = parser.parse_args()
    api_key = os.getenv("NEWSAPI_KEY", "")
    provider = NewsApiProvider(SourceConfig(name="newsapi", api_key=api_key))
    topic = select_topic(
        [provider],
        args.query,
        max_age=timedelta(hours=float(os.getenv("NEWS_MAX_AGE_HOURS", "48"))),
        minimum_sources=int(os.getenv("NEWS_MINIMUM_SOURCES", "1")),
    )
    if args.dry_run:
        print(f"topic={topic.id} headline={topic.headline!r} sources={len(topic.sources)} confidence={topic.confidence}")
        return
    store = NewsStore(Path("data/news.db"))
    if args.approve:
        store.approve(topic.id)
        topic.approval_status = "approved"
    paths = write_topic_artifacts(topic, args.output / topic.id, store)
    print(f"topic={topic.id} confidence={topic.confidence} approval={topic.approval_status}")
    for name, path in paths.items():
        print(f"{name}: {path}")
    store.close()


if __name__ == "__main__":
    main()
