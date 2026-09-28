import json
import unittest
from datetime import datetime, timezone

from news_engine.sources import NewsApiProvider, SourceConfig, SourceAuthError, select_topic


class FakeTransport:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get_json(self, url, params, headers, timeout):
        self.calls.append((url, params, headers, timeout))
        return self.payload


class SourceTests(unittest.TestCase):
    def test_provider_requires_api_key_and_sends_it_only_to_configured_provider(self):
        transport = FakeTransport({"articles": []})
        with self.assertRaises(SourceAuthError):
            NewsApiProvider(SourceConfig(name="newsapi", api_key=""), transport=transport)

        provider = NewsApiProvider(SourceConfig(name="newsapi", api_key="secret"), transport=transport)
        provider.search("technology")
        _, params, _, _ = transport.calls[0]
        self.assertEqual(params["apiKey"], "secret")

    def test_articles_keep_provenance_and_topic_deduplicates_urls(self):
        payload = {
            "articles": [
                {
                    "title": "A verified story",
                    "description": "Evidence one",
                    "url": "https://example.com/a",
                    "publishedAt": "2026-09-28T10:00:00Z",
                    "source": {"name": "Example"},
                },
                {
                    "title": "A duplicate",
                    "description": "Evidence duplicate",
                    "url": "https://example.com/a",
                    "publishedAt": "2026-09-28T09:00:00Z",
                    "source": {"name": "Example"},
                },
            ]
        }
        provider = NewsApiProvider(SourceConfig(name="newsapi", api_key="secret"), transport=FakeTransport(payload))
        topic = select_topic([provider], "technology", now=datetime(2026, 9, 28, 12, tzinfo=timezone.utc))
        self.assertEqual(len(topic.sources), 1)
        self.assertEqual(topic.sources[0].url, "https://example.com/a")
        self.assertEqual(topic.sources[0].provider, "newsapi")
        json.dumps(topic.to_dict())


if __name__ == "__main__":
    unittest.main()
