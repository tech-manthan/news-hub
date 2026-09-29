from __future__ import annotations

import json
import os
import sys
import threading
import webbrowser
from datetime import timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from news_engine.pipeline import write_research  # noqa: E402
from news_engine.claude_script import write_specs  # noqa: E402
from news_engine.env import load_env  # noqa: E402
from news_engine.sources import NewsApiProvider, SourceConfig, SourceAuthError, select_topic  # noqa: E402
from news_engine.research import PublicRSSProvider, google_news_feed  # noqa: E402
from news_engine.store import NewsStore  # noqa: E402
from news_engine.scripts import generate_bilingual  # noqa: E402
from news_engine.models import ShortScript, Topic, SourceArticle  # noqa: E402
from news_engine.voice import write_scene_voice  # noqa: E402
from news_engine.render import render_platforms  # noqa: E402
from news_engine.assets import write_assets  # noqa: E402
from news_engine.spec import LanguageSpec, validate_spec  # noqa: E402

OUTPUT = ROOT / "output"
STORE_PATH = ROOT / "data" / "news.db"
STATIC = Path(__file__).with_name("static")
load_env(ROOT / ".env")


def demo_topic() -> dict:
    return {
        "id": "demo-ai-policy",
        "query": "technology",
        "headline": "AI regulation is moving from debate to implementation",
        "summary": "Governments are publishing practical rules for safer artificial intelligence systems, putting transparency and accountability at the center of deployment.",
        "confidence": 0.82,
        "approval_status": "pending",
        "sources": [
            {"id": "demo-source-1", "provider": "demo", "publisher": "Authenticated News Desk", "title": "AI regulation moves to implementation", "description": "Governments are publishing practical rules for safer AI systems.", "url": "https://example.com/ai-regulation", "published_at": "2026-09-28T09:30:00Z"},
            {"id": "demo-source-2", "provider": "demo", "publisher": "Public Policy Monitor", "title": "New standards focus on transparency", "description": "New standards focus on transparency and accountability.", "url": "https://example.com/ai-standards", "published_at": "2026-09-28T08:45:00Z"},
        ],
        "demo": True,
    }


def read_json(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def topic_from_dir(folder: Path) -> dict:
    research = read_json(folder / "research.json") or {}
    research["id"] = folder.name
    research["demo"] = False
    for language in ("en", "hi"):
        for platform in ("instagram", "youtube"):
            research[f"spec_{language}_{platform}"] = read_json(folder / f"spec_{language}_{platform}.json")
            research[f"has_video_{language}_{platform}"] = (folder / f"short_{language}_{platform}.mp4").exists()
    research["spec_en"] = research.get("spec_en_instagram")
    research["spec_hi"] = research.get("spec_hi_instagram")
    research["has_voice"] = any(folder.glob("voice_*.json"))
    research["stage_status"] = {
        "research": (folder / "research.json").exists(),
        "script": any(folder.glob("spec_*_*.json")),
        "assets": (folder / "assets.json").exists(),
        "voice": any(folder.glob("voice_*_*.json")),
        "render": any(folder.glob("short_*_*.mp4")),
    }
    for platform in ("instagram", "youtube"):
        for language in ("en", "hi"):
            research[f"posted_{platform}_{language}"] = read_json(folder / f"posted_{platform}_{language}.json")
    return research


def list_topics() -> list[dict]:
    topics = [topic_from_dir(folder) for folder in OUTPUT.iterdir() if folder.is_dir()] if OUTPUT.exists() else []
    return sorted(topics, key=lambda topic: topic.get("id", ""), reverse=True)


def configured() -> bool:
    return bool(os.getenv("NEWSAPI_KEY", "").strip())


class DashboardHandler(BaseHTTPRequestHandler):
    server_version = "NewsEngineUI/0.1"

    def log_message(self, fmt, *args):
        return

    def send_json(self, payload: dict | list, status: int = 200):
        data = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_file(self, path: Path, content_type: str):
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if parsed.path == "/":
            return self.send_file(STATIC / "index.html", "text/html; charset=utf-8")
        if parsed.path == "/static/style.css":
            return self.send_file(STATIC / "style.css", "text/css; charset=utf-8")
        if parsed.path == "/static/app.js":
            return self.send_file(STATIC / "app.js", "text/javascript; charset=utf-8")
        if parsed.path.startswith("/media/topics/"):
            parts = parsed.path.split("/")
            if len(parts) == 5 and parts[-1].startswith("short_") and parts[-1].endswith(".mp4"):
                path = OUTPUT / Path(unquote(parts[3])).name / parts[4]
                if path.exists():
                    return self.send_file(path, "video/mp4")
            return self.send_json({"error": "media not found"}, 404)
        if parsed.path == "/api/status":
            return self.send_json({"provider": "NewsAPI" if configured() else "Google News RSS", "authenticated": configured(), "demo_available": True, "output_count": len(list_topics())})
        if parsed.path == "/api/topics":
            topics = list_topics()
            return self.send_json(topics or [demo_topic()])
        if parsed.path.startswith("/api/topics/"):
            topic_id = unquote(parsed.path.rsplit("/", 1)[-1])
            topic = next((topic for topic in list_topics() if topic["id"] == topic_id), None)
            return self.send_json(topic or (demo_topic() if topic_id == "demo-ai-policy" else {"error": "topic not found"}), 200 if topic or topic_id == "demo-ai-policy" else 404)
        self.send_error(404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/topics":
            payload = self.body()
            query = str(payload.get("query", "technology")).strip() or "technology"
            try:
                provider = NewsApiProvider(SourceConfig(name="newsapi", api_key=os.environ["NEWSAPI_KEY"])) if configured() else PublicRSSProvider(google_news_feed(os.getenv("NEWS_LANGUAGE", "en")))
                topic = select_topic([provider], query, max_age=timedelta(hours=48), minimum_sources=1)
                folder = OUTPUT / topic.id
                store = NewsStore(STORE_PATH)
                write_research(topic, folder, store)
                store.close()
                return self.send_json(topic.to_dict(), 201)
            except (SourceAuthError, ValueError, RuntimeError) as exc:
                return self.send_json({"error": str(exc)}, 400)
        if parsed.path.startswith("/api/topics/") and parsed.path.endswith("/approve"):
            topic_id = unquote(parsed.path.split("/")[3])
            store = NewsStore(STORE_PATH)
            store.approve(topic_id)
            store.close()
            research_path = OUTPUT / Path(topic_id).name / "research.json"
            research = read_json(research_path)
            if research is not None:
                research["approval_status"] = "approved"
                research_path.write_text(json.dumps(research, indent=2, ensure_ascii=False))
            for topic in list_topics():
                if topic["id"] == topic_id:
                    topic["approval_status"] = "approved"
                    return self.send_json(topic)
            if topic_id == "demo-ai-policy":
                topic = demo_topic()
                topic["approval_status"] = "approved"
                return self.send_json(topic)
            return self.send_json({"error": "topic not found"}, 404)
        if parsed.path.startswith("/api/topics/") and parsed.path.endswith("/stage"):
            return self._run_stage(unquote(parsed.path.split("/")[3]), self.body().get("stage", ""))
        if parsed.path.startswith("/api/topics/") and parsed.path.endswith("/script"):
            topic_id = unquote(parsed.path.split("/")[3])
            folder = OUTPUT / Path(topic_id).name
            research = read_json(folder / "research.json") or {}
            try:
                topic = Topic(
                    id=topic_id, query=research.get("query", "technology"), headline=research["headline"],
                    summary=research["summary"], sources=tuple(SourceArticle(**source) for source in research["sources"]),
                    confidence=research.get("confidence", 0.0), approval_status=research.get("approval_status", "pending"),
                )
                return self.send_json({"ok": True, "specs": {key: str(path.name) for key, path in write_specs(topic, folder).items()}})
            except (KeyError, RuntimeError, ValueError) as exc:
                return self.send_json({"error": str(exc)}, 400)
        if parsed.path.startswith("/api/topics/") and "/spec/" in parsed.path:
            parts = parsed.path.split("/")
            if len(parts) != 7:
                return self.send_json({"error": "spec path must be /api/topics/{id}/spec/{en|hi}/{instagram|youtube}"}, 400)
            topic_id, language, platform = unquote(parts[3]), parts[5], parts[6]
            if language not in ("en", "hi") or platform not in ("instagram", "youtube"):
                return self.send_json({"error": "invalid language or platform"}, 400)
            folder = OUTPUT / Path(topic_id).name
            research = read_json(folder / "research.json") or {}
            try:
                spec = LanguageSpec.model_validate(self.body().get("spec", {}))
                errors = validate_spec(spec, {source["id"] for source in research["sources"]})
                if errors:
                    return self.send_json({"error": "; ".join(errors)}, 400)
                path = folder / f"spec_{language}_{platform}.json"
                path.write_text(json.dumps(spec.model_dump(), indent=2, ensure_ascii=False))
                return self.send_json({"ok": True, "spec": spec.model_dump()})
            except (KeyError, ValueError) as exc:
                return self.send_json({"error": str(exc)}, 400)
        if parsed.path.startswith("/api/topics/") and parsed.path.endswith("/voice"):
            topic_id = unquote(parsed.path.split("/")[3])
            topic = next((topic for topic in list_topics() if topic["id"] == topic_id), None)
            if not topic:
                return self.send_json({"error": "voice generation needs a saved live topic; demo mode has no audio"}, 400)
            try:
                model_dir = Path(os.getenv("TTS_MODEL_DIR", "data/voices"))
                manifests = {}
                for language in ("en", "hi"):
                    for platform in ("instagram", "youtube"):
                        manifests[f"{language}_{platform}"] = read_json(write_scene_voice(OUTPUT / topic_id / f"spec_{language}_{platform}.json", OUTPUT / topic_id, language, model_dir, platform))
                return self.send_json({"ok": True, "manifests": manifests})
            except (RuntimeError, ValueError, KeyError) as exc:
                return self.send_json({"error": str(exc)}, 400)
        if parsed.path.startswith("/api/topics/") and parsed.path.endswith("/render"):
            topic_id = unquote(parsed.path.split("/")[3])
            folder = OUTPUT / Path(topic_id).name
            try:
                outputs = render_platforms(folder)
                return self.send_json({"ok": True, "videos": {key: str(path.name) for key, path in outputs.items()}})
            except (RuntimeError, FileNotFoundError, KeyError) as exc:
                return self.send_json({"error": str(exc)}, 400)
        if parsed.path.startswith("/api/topics/") and parsed.path.endswith("/publish/instagram"):
            return self._publish_platform(unquote(parsed.path.split("/")[3]), "instagram", self.body().get("language", "en"))
        if parsed.path.startswith("/api/topics/") and parsed.path.endswith("/publish/youtube"):
            return self._publish_platform(unquote(parsed.path.split("/")[3]), "youtube", self.body().get("language", "en"))
        self.send_error(404)

    def _publish_platform(self, topic_id: str, platform: str, language: str = "en"):
        folder = OUTPUT / Path(topic_id).name
        research = read_json(folder / "research.json") or {}
        if research.get("approval_status") != "approved":
            return self.send_json({"error": "approve this topic before publishing"}, 400)
        if language not in ("en", "hi"):
            return self.send_json({"error": "language must be en or hi"}, 400)
        record = folder / f"posted_{platform}_{language}.json"
        if record.exists():
            return self.send_json({"error": f"already published to {platform}"}, 409)
        try:
            from news_engine.publishers import InstagramPublisher, YouTubePublisher
            video = folder / f"short_{language}_{platform}.mp4"
            spec = research.get(f"spec_{language}_{platform}") or {}
            if platform == "instagram":
                result = InstagramPublisher().publish_reel(video, spec.get("caption", research.get("headline", "News update")))
            else:
                result = YouTubePublisher().publish_short(video, spec.get("youtube_title", research.get("headline", "News update")), spec.get("youtube_description", research.get("summary", "")) + "\n\n#Shorts", spec.get("youtube_tags", ["news", "shorts"]))
            record.write_text(json.dumps(result, indent=2, ensure_ascii=False))
            return self.send_json(result, 201)
        except (RuntimeError, FileNotFoundError, KeyError) as exc:
            return self.send_json({"error": str(exc)}, 400)

    def _run_stage(self, topic_id: str, stage: str):
        """Run one restartable pipeline stage from the dashboard."""
        allowed = {"script", "assets", "voice", "render"}
        if stage not in allowed:
            return self.send_json({"error": f"stage must be one of: {', '.join(sorted(allowed))}"}, 400)
        folder = OUTPUT / Path(topic_id).name
        research_path = folder / "research.json"
        if not research_path.exists():
            return self.send_json({"error": "research.json is missing; fetch the topic first"}, 400)
        try:
            research = read_json(research_path) or {}
            if stage == "script":
                topic = Topic(
                    id=topic_id, query=research.get("query", "technology"), headline=research["headline"],
                    summary=research["summary"], sources=tuple(SourceArticle(**source) for source in research["sources"]),
                    confidence=research.get("confidence", 0.0), approval_status=research.get("approval_status", "pending"),
                )
                result = {key: str(path.name) for key, path in write_specs(topic, folder).items()}
            elif stage == "assets":
                result = {"assets": str(write_assets(research_path, folder, browser=os.getenv("PUBLIC_RESEARCH_BROWSER", "0") == "1").name)}
            elif stage == "voice":
                model_dir = Path(os.getenv("TTS_MODEL_DIR", "data/voices"))
                result = {}
                for language in ("en", "hi"):
                    for platform in ("instagram", "youtube"):
                        result[f"{language}_{platform}"] = str(write_scene_voice(folder / f"spec_{language}_{platform}.json", folder, language, model_dir, platform).name)
            else:
                result = {key: str(path.name) for key, path in render_platforms(folder).items()}
            return self.send_json({"ok": True, "stage": stage, "result": result, "topic": topic_from_dir(folder)})
        except (RuntimeError, FileNotFoundError, KeyError, ValueError, TypeError) as exc:
            return self.send_json({"error": str(exc)}, 400)


def serve():
    port = int(os.getenv("NEWS_UI_PORT", "8765"))
    server = ThreadingHTTPServer(("127.0.0.1", port), DashboardHandler)
    print(f"News Engine dashboard: http://127.0.0.1:{port}", flush=True)
    if os.getenv("NEWS_UI_OPEN", "1") == "1":
        threading.Timer(0.35, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    serve()
