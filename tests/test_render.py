import unittest
from pathlib import Path

from news_engine.render import _remotion_static_props


class RenderTests(unittest.TestCase):
    def test_remotion_props_use_relative_static_file_paths(self):
        props = _remotion_static_props(Path("output/topic-123"), Path("audio_en_instagram.wav"))
        self.assertEqual(props["audio"], "news-engine/topic-123/audio_en_instagram.wav")
        self.assertEqual(props["assets"], "news-engine/topic-123/assets")
        self.assertFalse(Path(props["audio"]).is_absolute())


if __name__ == "__main__":
    unittest.main()
