import sqlite3
from datetime import datetime, date
from typing import Optional

from desktop.config import HISTORY_DB_FILE


class HistoryDB:
    def __init__(self):
        HISTORY_DB_FILE.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(HISTORY_DB_FILE), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS transcriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                text TEXT NOT NULL,
                raw_text TEXT,
                duration_sec REAL,
                source TEXT DEFAULT 'asr',
                word_count INTEGER DEFAULT 0
            )
        """)
        self._conn.commit()

    def add_entry(
        self,
        text: str,
        raw_text: Optional[str] = None,
        duration_sec: float = 0.0,
        source: str = "asr",
    ) -> int:
        word_count = len(text.split())
        cursor = self._conn.execute(
            "INSERT INTO transcriptions (timestamp, text, raw_text, duration_sec, source, word_count) VALUES (?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), text, raw_text, duration_sec, source, word_count),
        )
        self._conn.commit()
        return cursor.lastrowid

    def get_recent(self, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM transcriptions ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_today_stats(self) -> dict:
        today = date.today().isoformat()
        row = self._conn.execute(
            "SELECT COUNT(*) as uses, COALESCE(SUM(word_count), 0) as words FROM transcriptions WHERE timestamp LIKE ?",
            (today + "%",),
        ).fetchone()
        return {"uses": row["uses"], "words": row["words"]}

    def get_total_stats(self) -> dict:
        row = self._conn.execute(
            "SELECT COUNT(*) as uses, COALESCE(SUM(word_count), 0) as words FROM transcriptions"
        ).fetchone()
        return {"uses": row["uses"], "words": row["words"]}

    def search(self, query: str, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM transcriptions WHERE text LIKE ? ORDER BY id DESC LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_entry(self, entry_id: int):
        self._conn.execute("DELETE FROM transcriptions WHERE id = ?", (entry_id,))
        self._conn.commit()

    def clear(self):
        self._conn.execute("DELETE FROM transcriptions")
        self._conn.commit()

    def close(self):
        self._conn.close()
