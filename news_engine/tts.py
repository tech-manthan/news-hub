from __future__ import annotations

import json
import wave
from pathlib import Path
from typing import Protocol

from .models import ShortScript

DEFAULT_VOICE_MODELS = {"en": "en_US-lessac-medium.onnx", "hi": "hi_IN-pratham-medium.onnx"}


def available_voices(model_dir: Path, language: str) -> list[str]:
    prefix = "en_" if language == "en" else "hi_"
    return sorted(path.name for path in model_dir.glob(f"{prefix}*.onnx"))


def resolve_voice_model(model_dir: Path, language: str, voice_name: str | None = None) -> Path:
    name = Path(voice_name or DEFAULT_VOICE_MODELS[language]).name
    if not name.endswith(".onnx") or not name.startswith("en_" if language == "en" else "hi_"):
        raise ValueError(f"invalid {language} Piper voice: {name}")
    return model_dir / name


class TTSBackend(Protocol):
    language: str

    def synthesize(self, text: str, output: Path) -> None: ...


class PiperTTS:
    """Local Piper voice. The model and its voice files stay on disk; no API is used."""

    def __init__(self, language: str, model_path: Path, speed: float = 1.0):
        self.language = language
        self.model_path = model_path
        self.speed = speed

    def synthesize(self, text: str, output: Path) -> None:
        if not self.model_path.exists():
            raise RuntimeError(
                f"Piper model missing: {self.model_path}. Run `python scripts/setup_tts.py` first."
            )
        try:
            from piper import PiperVoice, SynthesisConfig
        except ImportError as exc:
            raise RuntimeError("Install local open-source TTS with `python -m pip install piper-tts`") from exc
        output.parent.mkdir(parents=True, exist_ok=True)
        voice = PiperVoice.load(str(self.model_path))
        # Piper's length scale is inverse speed: 1.0 is normal, lower is faster.
        config = SynthesisConfig(length_scale=max(0.5, min(2.0, 1.0 / self.speed)))
        with wave.open(str(output), "wb") as wav_file:
            voice.synthesize_wav(text, wav_file, syn_config=config)


def write_voice_artifacts(scripts: dict[str, ShortScript], output_dir: Path, backends: dict[str, TTSBackend]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"scripts": {}, "languages": sorted(scripts)}
    for language, script in scripts.items():
        backend = backends.get(language)
        if backend is None:
            raise ValueError(f"no TTS backend configured for {language}")
        if backend.language != language:
            raise ValueError(f"TTS backend language mismatch for {language}")
        path = output_dir / f"voice_{language}.wav"
        backend.synthesize(script.narration, path)
        manifest["scripts"][language] = {"audio": path.name, "source_ids": list(script.source_ids)}
    manifest_path = output_dir / "voice.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    return manifest_path
