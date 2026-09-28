from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from .models import ShortScript


class TTSBackend(Protocol):
    language: str

    def synthesize(self, text: str, output: Path) -> None: ...


class KokoroEnglishTTS:
    language = "en"

    def __init__(self, voice: str = "af_heart", speed: float = 1.0):
        self.voice = voice
        self.speed = speed

    def synthesize(self, text: str, output: Path) -> None:
        try:
            import numpy as np
            import soundfile as sf
            from kokoro import KPipeline
        except ImportError as exc:
            raise RuntimeError("English TTS needs kokoro, numpy, and soundfile installed") from exc
        output.parent.mkdir(parents=True, exist_ok=True)
        chunks = [np.asarray(result.audio, dtype=np.float32) for result in KPipeline(lang_code="a")(text, voice=self.voice, speed=self.speed)]
        if not chunks:
            raise RuntimeError("English TTS returned no audio")
        sf.write(output, np.concatenate(chunks), 24000)


class GoogleHindiTTS:
    language = "hi"

    def __init__(self, voice_name: str = "hi-IN-Neural2-A", speaking_rate: float = 1.0):
        self.voice_name = voice_name
        self.speaking_rate = speaking_rate

    def synthesize(self, text: str, output: Path) -> None:
        try:
            from google.cloud import texttospeech
        except ImportError as exc:
            raise RuntimeError("Hindi TTS needs google-cloud-texttospeech and GOOGLE_APPLICATION_CREDENTIALS") from exc
        client = texttospeech.TextToSpeechClient()
        response = client.synthesize_speech(
            input=texttospeech.SynthesisInput(text=text),
            voice=texttospeech.VoiceSelectionParams(language_code="hi-IN", name=self.voice_name),
            audio_config=texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3, speaking_rate=self.speaking_rate),
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(response.audio_content)


def write_voice_artifacts(scripts: dict[str, ShortScript], output_dir: Path, backends: dict[str, TTSBackend]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = {"scripts": {}, "languages": sorted(scripts)}
    for language, script in scripts.items():
        backend = backends.get(language)
        if backend is None:
            raise ValueError(f"no TTS backend configured for {language}")
        if backend.language != language:
            raise ValueError(f"TTS backend language mismatch for {language}")
        extension = ".mp3" if language == "hi" else ".wav"
        path = output_dir / f"voice_{language}{extension}"
        backend.synthesize(script.narration, path)
        manifest["scripts"][language] = {"audio": path.name, "source_ids": list(script.source_ids)}
    manifest_path = output_dir / "voice.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    return manifest_path
