import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--timings", required=True)
    parser.add_argument("--voice", required=True)
    parser.add_argument("--speed", type=float, default=1.0)
    args = parser.parse_args()
    sample_rate = 24000
    pipe = KPipeline(lang_code=args.voice[0], repo_id="hexgrad/Kokoro-82M")
    chunks, words, offset = [], [], 0.0
    for result in pipe(Path(args.text).read_text(encoding="utf-8"), voice=args.voice, speed=args.speed):
        audio = np.asarray(result.audio, dtype=np.float32)
        for token in result.tokens or []:
            if token.start_ts is not None and token.end_ts is not None:
                words.append({"text": token.text, "start": round(offset + token.start_ts, 3), "end": round(offset + token.end_ts, 3)})
        chunks.append(audio)
        offset += len(audio) / sample_rate
    if not chunks:
        raise RuntimeError("Kokoro returned no audio")
    audio = np.concatenate(chunks)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    sf.write(args.output, audio, sample_rate)
    Path(args.timings).write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
