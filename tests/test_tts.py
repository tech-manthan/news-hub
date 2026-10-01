import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from news_engine.tts import (
    KOKORO_VOICES,
    PiperTTS,
    available_backends,
    normalize_voice_id,
    voice_catalog,
)


class TTSBackendTests(unittest.TestCase):
    def test_kokoro_is_an_available_local_backend(self):
        self.assertIn("kokoro", available_backends())
        self.assertIn("am_michael", KOKORO_VOICES)

    def test_voice_id_accepts_the_filename_shown_by_the_dashboard(self):
        self.assertEqual(normalize_voice_id("hi_IN-rohan-medium.onnx"), "hi_IN-rohan-medium")

    def test_offline_catalog_includes_the_official_hindi_choices(self):
        from news_engine import tts

        previous = tts._VOICE_CATALOG_CACHE
        try:
            tts._VOICE_CATALOG_CACHE = {"en": [], "hi": [
                "hi_IN-pratham-medium.onnx",
                "hi_IN-priyamvada-medium.onnx",
                "hi_IN-rohan-medium.onnx",
            ]}
            self.assertEqual(len(voice_catalog("hi")), 3)
            self.assertIn("hi_IN-rohan-medium.onnx", voice_catalog("hi"))
        finally:
            tts._VOICE_CATALOG_CACHE = previous

    def test_missing_model_explains_how_to_install_that_specific_voice(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / "preview.wav"
            with self.assertRaisesRegex(RuntimeError, "hi_IN-rohan-medium.*piper.download_voices"):
                PiperTTS("hi", Path(directory) / "hi_IN-rohan-medium.onnx").synthesize("नमस्ते", output)


if __name__ == "__main__":
    unittest.main()
