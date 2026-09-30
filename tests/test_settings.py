import tempfile
import unittest
from pathlib import Path

from news_engine.settings import read_settings, write_settings


class SettingsTests(unittest.TestCase):
    def test_round_trip_keeps_voice_and_appearance_preferences(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            write_settings({
                "ENGLISH_TTS_SPEED": 1.1,
                "HINDI_TTS_SPEED": 0.9,
                "NEWS_BG_PRESET": "sunset",
                "NEWS_FONT": "poppins",
                "NEWS_TEMPLATE": "bulletin",
                "unknown": "must not persist",
            }, path)
            self.assertEqual(read_settings(path), {
                "ENGLISH_TTS_SPEED": "1.1",
                "HINDI_TTS_SPEED": "0.9",
                "NEWS_BG_PRESET": "sunset",
                "NEWS_FONT": "poppins",
                "NEWS_TEMPLATE": "bulletin",
            })
