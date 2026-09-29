from __future__ import annotations

import argparse
import json
from pathlib import Path

from news_engine.env import load_env
from news_engine.publishers import InstagramPublisher, PublisherError, YouTubePublisher


def main() -> None:
    load_env(Path(".env"))
    parser = argparse.ArgumentParser(description="Review and publish a generated news short")
    parser.add_argument("directory", nargs="?", type=Path)
    parser.add_argument("--instagram-setup", action="store_true")
    parser.add_argument("--youtube-setup", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--instagram", action="store_true")
    parser.add_argument("--youtube", action="store_true")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--language", choices=("en", "hi"), default="en")
    args = parser.parse_args()
    instagram, youtube = InstagramPublisher(), YouTubePublisher()
    try:
        if args.instagram_setup:
            print(json.dumps(instagram.setup(), indent=2))
            return
        if args.youtube_setup:
            print(json.dumps(youtube.setup(), indent=2))
            return
        if args.check:
            print("Instagram", json.dumps(instagram.whoami(), indent=2))
            print("YouTube", json.dumps(youtube.whoami(), indent=2))
            return
        if not args.directory or not (args.instagram or args.youtube):
            parser.error("provide a topic directory and --instagram and/or --youtube")
        directory = args.directory.resolve()
        research = json.loads((directory / "research.json").read_text())
        if research.get("approval_status") != "approved":
            raise PublisherError("topic must be approved in the dashboard before publishing")
        platform = "instagram" if args.instagram and not args.youtube else "youtube"
        video = directory / f"short_{args.language}_{platform}.mp4"
        if not video.exists():
            raise PublisherError(f"missing {video}; render the {args.language} short first")
        if not args.yes and input(f"Publish the {args.language} short to the selected platform(s)? [y/N] ").strip().lower() != "y":
            print("Not published.")
            return
        if args.instagram:
            record = directory / f"posted_instagram_{args.language}.json"
            if record.exists():
                raise PublisherError("Instagram already has a publish record for this topic")
            spec = json.loads((directory / f"spec_{args.language}_instagram.json").read_text())
            result = instagram.publish_reel(video, spec.get("instagram_caption", research["headline"]))
            record.write_text(json.dumps(result, indent=2))
            print(f"Instagram: {result['permalink']}")
        if args.youtube:
            record = directory / f"posted_youtube_{args.language}.json"
            if record.exists():
                raise PublisherError("YouTube already has a publish record for this topic")
            spec = json.loads((directory / f"spec_{args.language}_youtube.json").read_text())
            result = youtube.publish_short(video, spec.get("youtube_title", research["headline"]), spec.get("youtube_description", research["summary"]) + "\n\n#Shorts", spec.get("hashtags", ["#news", "#shorts"]))
            record.write_text(json.dumps(result, indent=2))
            print(f"YouTube: {result['url']}")
    except PublisherError as exc:
        raise SystemExit(str(exc))


if __name__ == "__main__":
    main()
