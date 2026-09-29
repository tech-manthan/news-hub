from __future__ import annotations

import argparse
import os
from pathlib import Path

from news_engine.autoreply import AutoReplyConfig, mark_replied, matching_comments
from news_engine.env import load_env
from news_engine.publishers import InstagramPublisher, YouTubePublisher


def main() -> None:
    load_env(Path(".env"))
    parser = argparse.ArgumentParser(description="Reply to matching comments on your own posts")
    parser.add_argument("--instagram-media-id")
    parser.add_argument("--youtube-video-id")
    parser.add_argument("--yes", action="store_true", help="send replies; without this flag only show matches")
    args = parser.parse_args()
    config = AutoReplyConfig(os.getenv("AUTO_REPLY_KEYWORD", "link"), os.getenv("AUTO_REPLY_TEXT", "Here is the link: https://example.com"), Path(os.getenv("AUTO_REPLY_STATE", "data/reply_state.json")))
    jobs = []
    if args.instagram_media_id:
        jobs.append(("instagram", InstagramPublisher(), args.instagram_media_id))
    if args.youtube_video_id:
        jobs.append(("youtube", YouTubePublisher(), args.youtube_video_id))
    if not jobs:
        parser.error("provide --instagram-media-id and/or --youtube-video-id")
    for platform, publisher, post_id in jobs:
        matches = matching_comments(publisher.list_comments(post_id), config)
        print(f"{platform}: {len(matches)} matching comments")
        for comment in matches:
            print(f"  {comment['id']}: {comment['text']}")
            if args.yes:
                publisher.reply_to_comment(comment["id"], config.reply_template)
                mark_replied(config, comment["id"])


if __name__ == "__main__":
    main()
