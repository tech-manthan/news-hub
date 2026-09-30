import unittest

from news_engine.tts import KOKORO_VOICES, available_backends


class TTSBackendTests(unittest.TestCase):
    def test_kokoro_is_an_available_local_backend(self):
        self.assertIn("kokoro", available_backends())
        self.assertIn("am_michael", KOKORO_VOICES)


if __name__ == "__main__":
    unittest.main()
