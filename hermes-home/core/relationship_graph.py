"""Relationship graph for family state."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class RelationshipGraph:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.init_db()

    def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS relationship_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    family_id TEXT NOT NULL,
                    member_a TEXT NOT NULL,
                    member_b TEXT NOT NULL,
                    trust REAL NOT NULL DEFAULT 0.5,
                    tension REAL NOT NULL DEFAULT 0,
                    support REAL NOT NULL DEFAULT 0.5,
                    confidence REAL NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    raw_json TEXT,
                    UNIQUE(family_id, member_a, member_b)
                )
                """
            )
            conn.commit()

    def update_edge(self, family_id: str, member_a: str, member_b: str, delta: dict[str, float], raw: dict[str, Any] | None = None) -> None:
        if member_a == member_b:
            return
        a, b = sorted([member_a, member_b])
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO relationship_edges (
                    family_id, member_a, member_b, trust, tension, support, confidence, updated_at, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(family_id, member_a, member_b) DO UPDATE SET
                    trust = MIN(1, MAX(0, trust + excluded.trust - 0.5)),
                    tension = MIN(1, MAX(0, tension + excluded.tension)),
                    support = MIN(1, MAX(0, support + excluded.support - 0.5)),
                    confidence = MAX(confidence, excluded.confidence),
                    updated_at = excluded.updated_at,
                    raw_json = excluded.raw_json
                """,
                (
                    family_id,
                    a,
                    b,
                    0.5 + float(delta.get("trust", 0)),
                    float(delta.get("tension", 0)),
                    0.5 + float(delta.get("support", 0)),
                    float(delta.get("confidence", 0.5)),
                    now,
                    json.dumps(raw or delta, ensure_ascii=False),
                ),
            )
            conn.commit()

