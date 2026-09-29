from __future__ import annotations

import argparse
from pathlib import Path

from news_engine.scheduler import launch_agent_command, write_launch_agent


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a safe macOS schedule for building news shorts")
    parser.add_argument("--query", default="technology")
    parser.add_argument("--hour", type=int, default=9)
    parser.add_argument("--minute", type=int, default=0)
    parser.add_argument("--output", type=Path, default=Path("data/com.newsengine.build.plist"))
    args = parser.parse_args()
    path = write_launch_agent(args.output, args.query, args.hour, args.minute)
    print(path)
    print(f"Load it with: {launch_agent_command(path)}")


if __name__ == "__main__":
    main()
