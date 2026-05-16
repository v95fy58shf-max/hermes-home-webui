"""TTL and decay worker for family states and memories."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path


TTL = {
    "temporary_emotion": 24 * 3600,
    "emotion/stress": 48 * 3600,
    "conflict": 72 * 3600,
    "preference": None,
    "habit": None,
    "health/history": None,
}


class DecayWorker:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def run_once(self) -> dict[str, int]:
        now = int(time.time())
        with sqlite3.connect(self.db_path) as conn:
            expired = conn.execute(
                """
                UPDATE family_states
                SET archived = 1
                WHERE archived = 0 AND expires_at IS NOT NULL AND expires_at <= ?
                """,
                (now,),
            ).rowcount
            decayed = conn.execute(
                """
                UPDATE family_states
                SET importance = MAX(1, importance - decay),
                    confidence = MAX(0, confidence - decay * 0.05)
                WHERE archived = 0 AND decay > 0
                """,
            ).rowcount
            conn.commit()
        return {"expired": int(expired or 0), "decayed": int(decayed or 0)}

