from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VOICE_DIR = ROOT / "data" / "voices"
VOICES = ("en_US-lessac-medium", "hi_IN-pratham-medium")


def main() -> None:
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    for voice in VOICES:
        subprocess.run([sys.executable, "-m", "piper.download_voices", "--data-dir", str(VOICE_DIR), voice], check=True)
    print(f"Downloaded local Piper voices to {VOICE_DIR}")


if __name__ == "__main__":
    main()
