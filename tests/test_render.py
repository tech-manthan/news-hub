import unittest
from pathlib import Path

from news_engine.render import _remotion_static_props


class RenderTests(unittest.TestCase):
    def test_remotion_props_use_relative_static_file_paths(self):
        props = _remotion_static_props(Path("output/topic-123"), Path("audio_en_instagram.wav"))
        self.assertEqual(props["audio"], "news-engine/topic-123/audio_en_instagram.wav")
        self.assertEqual(props["assets"], "news-engine/topic-123/assets")
        self.assertFalse(Path(props["audio"]).is_absolute())

    def test_remotion_props_support_isolated_concurrent_render_directories(self):
        props = _remotion_static_props(Path("output/topic-123"), Path("audio_en_youtube.wav"), "topic-123-en-youtube-a1b2c3d4")
        self.assertEqual(props["audio"], "news-engine/topic-123-en-youtube-a1b2c3d4/audio_en_youtube.wav")


if __name__ == "__main__":
    unittest.main()
