import unittest

from news_engine.niches.news import CATEGORY_PRESETS


class CategoryPresetTests(unittest.TestCase):
    def test_newsroom_includes_core_beats(self):
        for category in ("trending", "india", "world", "technology", "business", "sports", "entertainment", "science"):
            self.assertTrue(CATEGORY_PRESETS[category]["label"])
            self.assertTrue(CATEGORY_PRESETS[category]["query"])


if __name__ == "__main__":
    unittest.main()
