import unittest
from unittest.mock import patch

from news_engine.render import render_settings


class RenderSettingsTests(unittest.TestCase):
    def test_render_settings_reads_saved_appearance_preferences(self):
        with patch.dict("os.environ", {
            "NEWS_BG_PRESET": "forest",
            "NEWS_FONT": "space_grotesk",
            "NEWS_TEMPLATE": "minimal",
        }, clear=False):
            self.assertEqual(render_settings(), {
                "bgPreset": "forest",
                "font": "space_grotesk",
                "template": "minimal",
            })


if __name__ == "__main__":
    unittest.main()
