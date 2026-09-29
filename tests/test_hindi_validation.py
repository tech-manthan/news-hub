import unittest

from news_engine.spec import LanguageSpec, validate_spec


class HindiValidationTests(unittest.TestCase):
    def test_hindi_rejects_lowercase_hinglish_in_scene_copy(self):
        spec = LanguageSpec(
            language="hi", title="एआई की खबर", scenes=[
                {"type": "hook_stat", "narration": "AI godfathers ने चेतावनी दी है।", "headline": "एआई चेतावनी", "source_ids": ["s1"]},
                {"type": "image", "narration": "यह तस्वीर कहानी समझाती है।", "headline": "तस्वीर", "source_ids": ["s1"]},
                {"type": "bullets", "narration": "यह खतरा बढ़ रहा है।", "headline": "मुख्य बात", "source_ids": ["s1"], "bullets": ["बड़ा खतरा"]},
                {"type": "image", "narration": "सरकारें तैयारी कर रही हैं।", "headline": "तैयारी", "source_ids": ["s1"]},
                {"type": "cta", "narration": "ताज़ा खबरों के लिए जुड़े रहें।", "headline": "जुड़े रहें", "source_ids": ["s1"]},
            ],
            caption="एआई की खबर", hashtags=["#एआई", "#खबर", "#तकनीक"], youtube_title="एआई की खबर",
            youtube_description="एआई की खबर", youtube_tags=["एआई", "खबर", "तकनीक"], instagram_cta="जुड़े रहें।", youtube_cta="जुड़े रहें।", source_ids=["s1"],
        )
        errors = validate_spec(spec, {"s1"})
        self.assertTrue(any("Devanagari" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
