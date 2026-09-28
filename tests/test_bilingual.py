import unittest

from news_engine.models import Topic, SourceArticle
from news_engine.scripts import generate_bilingual


class BilingualTests(unittest.TestCase):
    def test_english_and_hindi_shorts_share_the_same_evidence(self):
        topic = Topic(
            id="topic-1",
            query="AI policy",
            headline="New AI policy announced",
            summary="Officials announced a new policy for safer AI systems.",
            sources=[
                SourceArticle(
                    id="source-1",
                    provider="newsapi",
                    publisher="Example News",
                    title="New AI policy announced",
                    description="Officials announced a new policy for safer AI systems.",
                    url="https://example.com/story",
                    published_at="2026-09-28T10:00:00Z",
                )
            ],
        )
        outputs = generate_bilingual(topic)
        self.assertEqual(set(outputs), {"en", "hi"})
        self.assertEqual(outputs["en"].source_ids, outputs["hi"].source_ids)
        self.assertIn("New AI policy announced", outputs["en"].narration)
        self.assertIn("हिंदी खबर", outputs["hi"].narration)


if __name__ == "__main__":
    unittest.main()
