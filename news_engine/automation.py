from __future__ import annotations

import os
import threading
from datetime import timedelta
from pathlib import Path

from .assets import write_assets
from .claude_script import write_specs
from .niches.news import NewsAdapter
from .pipeline import write_research
from .render import render_platforms
from .store import NewsStore
from .voice import write_scene_voice


class TrendingAutomation:
    """Local discovery/build loop. It never approves or publishes anything."""

    def __init__(self, root: Path):
        self.root = root
        self.output = root / "output"
        self.stop_event = threading.Event()
        self.thread: threading.Thread | None = None
        self.lock = threading.Lock()
        self.state = {"running": False, "query": "trending news", "interval_minutes": 60, "last_run": None, "last_topic": None, "last_error": None}

    def start(self, query: str, interval_minutes: int) -> dict:
        interval_minutes = max(5, min(1440, int(interval_minutes)))
        with self.lock:
            if self.thread and self.thread.is_alive():
                self.state.update({"query": query, "interval_minutes": interval_minutes})
                return dict(self.state)
            self.stop_event.clear()
            self.state.update({"running": True, "query": query or "trending news", "interval_minutes": interval_minutes, "last_error": None})
            self.thread = threading.Thread(target=self._loop, name="news-trending-automation", daemon=True)
            self.thread.start()
            return dict(self.state)

    def stop(self) -> dict:
        self.stop_event.set()
        with self.lock:
            self.state["running"] = False
        return dict(self.state)

    def snapshot(self) -> dict:
        with self.lock:
            return dict(self.state)

    def _loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                self._build_latest()
            except Exception as exc:  # the loop must stay alive after one bad source/build
                with self.lock:
                    self.state["last_error"] = str(exc)
            with self.lock:
                interval = self.state["interval_minutes"]
            if self.stop_event.wait(interval * 60):
                break
        with self.lock:
            self.state["running"] = False

    def _build_latest(self) -> None:
        query = self.snapshot()["query"]
        adapter = NewsAdapter()
        opts = {
            "query": query,
            "newsapi_key": os.getenv("NEWSAPI_KEY", ""),
            "language": os.getenv("NEWS_LANGUAGE", "en"),
            # Automation always captures a source visual; the fallback card handles
            # Google News shells and paywalled/JS-only pages without scraping around them.
            "browser": True,
            "max_age_hours": float(os.getenv("NEWS_MAX_AGE_HOURS", "48")),
            "minimum_sources": int(os.getenv("NEWS_MINIMUM_SOURCES", "1")),
        }
        topic = adapter.pick(opts)
        folder = self.output / topic.id
        if (folder / "research.json").exists():
            with self.lock:
                self.state["last_topic"] = topic.id
                self.state["last_run"] = topic.headline
            return
        folder.mkdir(parents=True, exist_ok=True)
        store = NewsStore(self.root / "data" / "news.db")
        try:
            research_path = write_research(topic, folder, store)
        finally:
            store.close()
        write_specs(topic, folder)
        write_assets(research_path, folder, browser=opts["browser"])
        model_dir = Path(os.getenv("TTS_MODEL_DIR", "data/voices"))
        for language in ("en", "hi"):
            voice_name = os.getenv(f"{'ENGLISH' if language == 'en' else 'HINDI'}_TTS_VOICE")
            for platform in ("instagram", "youtube"):
                write_scene_voice(folder / f"spec_{language}_{platform}.json", folder, language, model_dir, platform, voice_name)
        render_platforms(folder)
        with self.lock:
            self.state["last_topic"] = topic.id
            self.state["last_run"] = topic.headline
            self.state["last_error"] = None
