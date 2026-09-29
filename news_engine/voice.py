from __future__ import annotations

import json
import re
import wave
from pathlib import Path

from .spec import LanguageSpec
from .tts import PiperTTS


def _words(text: str, duration: float) -> list[dict]:
    tokens = [token for token in re.findall(r"\S+", text) if token]
    if not tokens:
        return []
    step = duration / len(tokens)
    return [{"text": token, "start": round(i * step, 3), "end": round((i + 1) * step, 3)} for i, token in enumerate(tokens)]


def write_scene_voice(spec_path: Path, output_dir: Path, language: str, model_dir: Path, platform: str | None = None) -> Path:
    spec = LanguageSpec.model_validate(json.loads(spec_path.read_text()))
    platform = platform or spec_path.stem.rsplit("_", 1)[-1]
    voice_dir = output_dir / "voice" / language / platform
    voice_dir.mkdir(parents=True, exist_ok=True)
    model_name = "en_US-lessac-medium.onnx" if language == "en" else "hi_IN-pratham-medium.onnx"
    backend = PiperTTS(language, model_dir / model_name)
    scenes = []
    for index, scene in enumerate(spec.scenes):
        path = voice_dir / f"scene_{index}.wav"
        backend.synthesize(scene.narration, path)
        with wave.open(str(path), "rb") as wav_file:
            duration = wav_file.getnframes() / wav_file.getframerate()
        scenes.append({"file": str(path.relative_to(output_dir)), "duration": round(duration, 3), "words": _words(scene.narration, duration)})
    manifest = output_dir / f"voice_{language}_{platform}.json"
    manifest.write_text(json.dumps({"language": language, "scenes": scenes}, indent=2, ensure_ascii=False))
    return manifest
