import tempfile
import unittest
from pathlib import Path

from news_engine.models import Topic
from news_engine.store import NewsStore


class StoreTests(unittest.TestCase):
    def test_topics_are_not_publishable_until_approved(self):
        with tempfile.TemporaryDirectory() as directory:
            store = NewsStore(Path(directory) / "news.db")
            topic = Topic("topic-1", "query", "headline", "summary", [])
            store.save_topic(topic)
            self.assertFalse(store.is_approved(topic.id))
            store.approve(topic.id)
            self.assertTrue(store.is_approved(topic.id))
            store.close()

    def test_delete_removes_topic_and_approval(self):
        with tempfile.TemporaryDirectory() as directory:
            store = NewsStore(Path(directory) / "news.db")
            topic = Topic("topic-delete", "query", "headline", "summary", [])
            store.save_topic(topic)
            store.approve(topic.id)
            store.delete(topic.id)
            self.assertFalse(store.is_approved(topic.id))
            store.close()


if __name__ == "__main__":
    unittest.main()
