from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from news_engine.assets import write_assets
from news_engine.claude_script import write_specs
from news_engine.env import load_env
from news_engine.niches.news import NewsAdapter
from news_engine.pipeline import write_research
from news_engine.render import render_platforms
from news_engine.store import NewsStore
from news_engine.voice import write_scene_voice

STAGES = ("research", "script", "assets", "voice", "render")


def _topic_from_research(path: Path):
    from news_engine.models import SourceArticle, Topic

    data = json.loads(path.read_text())
    sources = tuple(SourceArticle(**source) for source in data["sources"])
    return Topic(
        id=data["id"], query=data.get("query", "technology"), headline=data["headline"],
        summary=data["summary"], sources=sources, confidence=data.get("confidence", 0.0),
        approval_status=data.get("approval_status", "pending"),
    )


def main() -> None:
    load_env(Path(".env"))
    parser = argparse.ArgumentParser(description="Build bilingual news shorts, one resumable stage at a time")
    parser.add_argument("--query", default=os.getenv("NEWS_QUERY", "technology"))
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--dir", type=Path, help="resume an existing topic directory")
    parser.add_argument("--stages", default=",".join(STAGES), help="comma-separated stages: research,script,assets,voice,render")
    parser.add_argument("--dry-run", action="store_true", help="fetch and score only")
    parser.add_argument("--approve", action="store_true", help="approve the selected topic for later publishing")
    args = parser.parse_args()
    stages = tuple(stage.strip() for stage in args.stages.split(",") if stage.strip())
    unknown = set(stages) - set(STAGES)
    if unknown:
        parser.error(f"unknown stages: {', '.join(sorted(unknown))}")

    store = NewsStore(Path("data/news.db"))
    try:
        adapter = NewsAdapter()
        opts = {
            "query": args.query,
            "newsapi_key": os.getenv("NEWSAPI_KEY", ""),
            "language": os.getenv("NEWS_LANGUAGE", "en"),
            "browser": os.getenv("PUBLIC_RESEARCH_BROWSER", "0") == "1",
            "max_age_hours": float(os.getenv("NEWS_MAX_AGE_HOURS", "48")),
            "minimum_sources": int(os.getenv("NEWS_MINIMUM_SOURCES", "2")),
        }
        if args.dir:
            output_dir = args.dir.resolve()
            research_path = output_dir / "research.json"
            if not research_path.exists():
                raise SystemExit(f"missing {research_path}")
            topic = _topic_from_research(research_path)
        else:
            topic = adapter.pick(opts)
            if args.dry_run:
                print(f"topic={topic.id} headline={topic.headline!r} sources={len(topic.sources)} confidence={topic.confidence}")
                return
            output_dir = args.output / topic.id
            research_path = write_research(topic, output_dir, store)
        if args.approve:
            store.approve(topic.id)
            topic.approval_status = "approved"
            write_research(topic, output_dir, store)
        if args.dry_run:
            print(f"topic={topic.id} headline={topic.headline!r} sources={len(topic.sources)} confidence={topic.confidence}")
            return

        print(f"topic={topic.id} output={output_dir}")
        if "research" in stages and not research_path.exists():
            write_research(topic, output_dir, store)
        if "script" in stages:
            for path in write_specs(topic, output_dir):
                print(f"script: {path}")
        if "assets" in stages:
            print(f"assets: {write_assets(research_path, output_dir, browser=opts['browser'])}")
        if "voice" in stages:
            model_dir = Path(os.getenv("TTS_MODEL_DIR", "data/voices"))
            for language in ("en", "hi"):
                for platform in ("instagram", "youtube"):
                    spec_path = output_dir / f"spec_{language}_{platform}.json"
                    print(f"voice: {write_scene_voice(spec_path, output_dir, language, model_dir=model_dir, platform=platform)}")
        if "render" in stages:
            for key, path in render_platforms(output_dir).items():
                print(f"video_{key}: {path}")
    finally:
        store.close()


if __name__ == "__main__":
    main()
