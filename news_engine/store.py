from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import Topic


class NewsStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS topics (id TEXT PRIMARY KEY, payload TEXT NOT NULL, approval_status TEXT NOT NULL)")
        self.conn.commit()

    def save_topic(self, topic: Topic) -> None:
        self.conn.execute("INSERT OR REPLACE INTO topics VALUES (?, ?, ?)", (topic.id, json.dumps(topic.to_dict(), ensure_ascii=False), topic.approval_status))
        self.conn.commit()

    def approve(self, topic_id: str) -> None:
        self.conn.execute("UPDATE topics SET approval_status='approved' WHERE id=?", (topic_id,))
        self.conn.commit()

    def is_approved(self, topic_id: str) -> bool:
        row = self.conn.execute("SELECT approval_status FROM topics WHERE id=?", (topic_id,)).fetchone()
        return bool(row and row[0] == "approved")

    def close(self) -> None:
        self.conn.close()
