import unittest

from news_engine.research import PublicFeed, PublicRSSProvider, google_news_feed


class ResearchTests(unittest.TestCase):
    def test_public_rss_provider_is_allowlisted_and_normalizes_provenance(self):
        xml = """<rss><channel><item><title>Story &amp; update</title><link>https://news.google.com/articles/abc</link><description>Evidence</description><pubDate>Mon, 28 Sep 2026 10:00:00 GMT</pubDate><source>Desk</source></item><item><title>Unsafe</title><link>http://evil.example/story</link></item></channel></rss>"""
        provider = PublicRSSProvider(PublicFeed("fixture", "https://news.google.com/rss?q={query}", ("news.google.com",)), fetcher=lambda _: xml)
        articles = provider.search("AI")
        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].provider, "fixture")
        self.assertEqual(articles[0].publisher, "Desk")
        self.assertEqual(google_news_feed("hi").allowed_domains, ("news.google.com",))


if __name__ == "__main__":
    unittest.main()
