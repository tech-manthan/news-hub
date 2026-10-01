from __future__ import annotations

import subprocess
import sys
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VOICE_DIR = ROOT / "data" / "voices"
VOICES = ("en_US-lessac-medium", "hi_IN-pratham-medium", "hi_IN-priyamvada-medium", "hi_IN-rohan-medium")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download local Piper voices used by News Engine.")
    parser.add_argument("voices", nargs="*", help="Piper ids or .onnx filenames; defaults to the standard English and all Hindi voices")
    requested = tuple(Path(value).name.removesuffix(".onnx") for value in parser.parse_args().voices) or VOICES
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    for voice in requested:
        subprocess.run([sys.executable, "-m", "piper.download_voices", "--data-dir", str(VOICE_DIR), voice], check=True)
    print(f"Downloaded local Piper voices to {VOICE_DIR}")


if __name__ == "__main__":
    main()
