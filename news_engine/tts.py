from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from urllib.request import urlopen
import wave
from pathlib import Path
from typing import Protocol

from .models import ShortScript

DEFAULT_VOICE_MODELS = {"en": "en_US-lessac-medium.onnx", "hi": "hi_IN-pratham-medium.onnx"}
OFFLINE_PIPER_CATALOG = {
    "en": ["en_US-amy-medium.onnx", "en_US-lessac-medium.onnx", "en_US-libritts_r-medium.onnx", "en_US-ryan-medium.onnx"],
    "hi": [
        "hi_IN-pratham-medium.onnx",
        "hi_IN-priyamvada-medium.onnx",
        "hi_IN-rohan-medium.onnx",
    ],
}
PIPER_VOICES_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/voices.json?download=true"
_VOICE_CATALOG_CACHE: dict[str, list[str]] | None = None
KOKORO_VOICES = {
    "af_heart": "Heart (US, female)", "af_bella": "Bella (US, female)", "af_nicole": "Nicole (US, female)",
    "af_sarah": "Sarah (US, female)", "af_sky": "Sky (US, female)", "af_nova": "Nova (US, female)",
    "af_alloy": "Alloy (US, female)", "af_aoede": "Aoede (US, female)", "af_jessica": "Jessica (US, female)",
    "af_kore": "Kore (US, female)", "af_river": "River (US, female)", "am_michael": "Michael (US, male)",
    "am_adam": "Adam (US, male)", "am_eric": "Eric (US, male)", "am_liam": "Liam (US, male)",
    "am_onyx": "Onyx (US, male)", "am_echo": "Echo (US, male)", "am_fenrir": "Fenrir (US, male)",
    "am_puck": "Puck (US, male)", "am_santa": "Santa (US, male)", "bf_emma": "Emma (UK, female)",
    "bf_isabella": "Isabella (UK, female)", "bf_alice": "Alice (UK, female)", "bf_lily": "Lily (UK, female)",
    "bm_george": "George (UK, male)", "bm_lewis": "Lewis (UK, male)", "bm_daniel": "Daniel (UK, male)",
    "bm_fable": "Fable (UK, male)",
}


def available_backends() -> list[str]:
    return ["piper", "kokoro"]


def resolve_kokoro_python() -> Path:
    configured = os.getenv("KOKORO_PYTHON", "").strip()
    candidates = [Path(configured)] if configured else []
    candidates += [Path(__file__).resolve().parents[2] / "reel-engine" / ".venv" / "bin" / "python", Path(sys.executable)]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    raise RuntimeError("Kokoro Python environment not found. Set KOKORO_PYTHON to reel-engine/.venv/bin/python.")


def available_voices(model_dir: Path, language: str) -> list[str]:
    prefix = "en_" if language == "en" else "hi_"
    return sorted(path.name for path in model_dir.glob(f"{prefix}*.onnx"))


def voice_catalog(language: str) -> list[str]:
    """Return official Piper model ids, falling back to known local defaults offline."""
    global _VOICE_CATALOG_CACHE
    if _VOICE_CATALOG_CACHE is None:
        try:
            with urlopen(PIPER_VOICES_URL, timeout=4) as response:
                catalog = json.load(response)
            _VOICE_CATALOG_CACHE = {
                "en": sorted(f"{name}.onnx" for name in catalog if name.startswith("en_")),
                "hi": sorted(f"{name}.onnx" for name in catalog if name.startswith("hi_")),
            }
        except (OSError, ValueError, TimeoutError):
            _VOICE_CATALOG_CACHE = {language: list(voices) for language, voices in OFFLINE_PIPER_CATALOG.items()}
    return _VOICE_CATALOG_CACHE.get(language, [])


def normalize_voice_id(voice_name: str) -> str:
    """Accept either Piper's model id or the .onnx filename shown in the UI."""
    name = Path(voice_name.strip()).name
    return name[:-5] if name.endswith(".onnx") else name


def resolve_voice_model(model_dir: Path, language: str, voice_name: str | None = None) -> Path:
    name = normalize_voice_id(voice_name or DEFAULT_VOICE_MODELS[language]) + ".onnx"
    if not name.endswith(".onnx") or not name.startswith("en_" if language == "en" else "hi_"):
        raise ValueError(f"invalid {language} Piper voice: {name}")
    return model_dir / name


class TTSBackend(Protocol):
    language: str

    def synthesize(self, text: str, output: Path) -> list[dict] | None: ...


class PiperTTS:
    """Local Piper voice. The model and its voice files stay on disk; no API is used."""

    def __init__(self, language: str, model_path: Path, speed: float = 1.0):
        self.language = language
        self.model_path = model_path
        self.speed = speed

    def synthesize(self, text: str, output: Path) -> None:
        if not self.model_path.exists():
            voice_id = self.model_path.stem
            raise RuntimeError(
                f"Piper model missing: {voice_id} at {self.model_path}. "
                f"Install this voice from Settings, or run `python -m piper.download_voices "
                f"--data-dir {self.model_path.parent} {voice_id}`."
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


class KokoroTTS:
    """Reuse reel-engine's local Kokoro installation without downloading another model."""

    language = "en"

    def __init__(self, voice: str, speed: float = 1.0):
        self.voice = voice
        self.speed = speed

    def synthesize(self, text: str, output: Path) -> list[dict]:
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="news-kokoro-") as directory:
            root = Path(directory)
            text_path = root / "text.txt"
            timings_path = root / "timings.json"
            text_path.write_text(text, encoding="utf-8")
            command = [str(resolve_kokoro_python()), str(Path(__file__).resolve().parents[1] / "scripts" / "kokoro_synth.py"), "--text", str(text_path), "--output", str(output), "--timings", str(timings_path), "--voice", self.voice, "--speed", str(self.speed)]
            result = subprocess.run(command, cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stderr[-1200:] or "Kokoro synthesis failed")
            return json.loads(timings_path.read_text()) if timings_path.exists() else []


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
