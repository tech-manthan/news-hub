import tempfile
import unittest
from pathlib import Path

from ui.server import DashboardHandler, research_error_message


class _ClosedSocket:
    def write(self, data):
        raise BrokenPipeError(32, "Broken pipe")


class _Handler(DashboardHandler):
    def __init__(self, path):
        self.wfile = _ClosedSocket()
        self.path = path

    def send_response(self, status):
        pass

    def send_header(self, name, value):
        pass

    def end_headers(self):
        pass


class MediaServerTests(unittest.TestCase):
    def test_send_file_ignores_client_disconnect(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "preview.mp4"
            path.write_bytes(b"video")
            _Handler(path).send_file(path, "video/mp4")

    def test_research_network_errors_are_actionable(self):
        message = research_error_message(ConnectionError("NameResolutionError: news.google.com"))
        self.assertIn("internet/DNS", message)
        self.assertIn("NewsAPI", message)


if __name__ == "__main__":
    unittest.main()
