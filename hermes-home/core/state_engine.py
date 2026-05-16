"""State Engine for Hermes Home.

The state engine turns events into structured, time-bound household states.
It intentionally stores state objects instead of only saving raw text.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .privacy import PRIVATE, normalize_scope


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class StateEngine:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.init_db()

    def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS family_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    state_id TEXT NOT NULL UNIQUE,
                    family_id TEXT NOT NULL,
                    member_id TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    type TEXT NOT NULL,
                    value REAL,
                    value_json TEXT,
                    trend TEXT,
                    confidence REAL NOT NULL DEFAULT 0,
                    ttl INTEGER,
                    importance REAL NOT NULL DEFAULT 3,
                    decay REAL NOT NULL DEFAULT 0,
                    expires_at INTEGER,
                    archived INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    source_event_id TEXT,
                    raw_json TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_family_states_lookup ON family_states(family_id, member_id, type, archived)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_family_states_scope ON family_states(scope, archived)")
            conn.commit()

    def upsert_state(self, state: dict[str, Any]) -> dict[str, Any]:
        state = dict(state)
        now_text = now_iso()
        now_epoch = int(time.time())
        state.setdefault("state_id", str(uuid.uuid4()))
        state.setdefault("scope", PRIVATE)
        state["scope"] = normalize_scope(state.get("scope"))
        state.setdefault("trend", "stable")
        state.setdefault("confidence", 0.5)
        state.setdefault("importance", 3)
        ttl = state.get("ttl")
        expires_at = now_epoch + int(ttl) if ttl else None
        value = state.get("value")
        value_json = json.dumps(value, ensure_ascii=False) if not isinstance(value, (int, float, type(None))) else None
        numeric_value = float(value) if isinstance(value, (int, float)) else None
        with sqlite3.connect(self.db_path) as conn:
            existing = conn.execute(
                """
                SELECT state_id, value, confidence, updated_at
                FROM family_states
                WHERE family_id = ? AND member_id = ? AND type = ? AND scope = ? AND archived = 0
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (state.get("family_id"), state.get("member_id"), state.get("type"), state["scope"]),
            ).fetchone()
            if existing:
                previous = existing[1]
                trend = state.get("trend") or self._trend(previous, numeric_value)
                conn.execute(
                    """
                    UPDATE family_states
                    SET value = ?, value_json = ?, trend = ?, confidence = ?, ttl = ?, importance = ?,
                        decay = ?, expires_at = ?, updated_at = ?, source_event_id = ?, raw_json = ?
                    WHERE state_id = ?
                    """,
                    (
                        numeric_value,
                        value_json,
                        trend,
                        float(state.get("confidence") or 0),
                        ttl,
                        float(state.get("importance") or 3),
                        float(state.get("decay") or 0),
                        expires_at,
                        now_text,
                        state.get("source_event_id") or "",
                        json.dumps(state, ensure_ascii=False),
                        existing[0],
                    ),
                )
                state["state_id"] = existing[0]
                state["trend"] = trend
            else:
                conn.execute(
                    """
                    INSERT INTO family_states (
                        state_id, family_id, member_id, scope, type, value, value_json, trend,
                        confidence, ttl, importance, decay, expires_at, archived, created_at,
                        updated_at, source_event_id, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
                    """,
                    (
                        state["state_id"],
                        state.get("family_id") or "default",
                        state.get("member_id") or "unknown",
                        state["scope"],
                        state.get("type") or "unknown",
                        numeric_value,
                        value_json,
                        state.get("trend") or "stable",
                        float(state.get("confidence") or 0),
                        ttl,
                        float(state.get("importance") or 3),
                        float(state.get("decay") or 0),
                        expires_at,
                        now_text,
                        now_text,
                        state.get("source_event_id") or "",
                        json.dumps(state, ensure_ascii=False),
                    ),
                )
            conn.commit()
        state["updated_at"] = now_text
        return state

    def process_event(self, event: dict[str, Any], analyzers: list[Any] | None = None) -> list[dict[str, Any]]:
        states: list[dict[str, Any]] = []
        analyzers = analyzers or []
        for analyzer in analyzers:
            produced = analyzer.analyze(event)
            if isinstance(produced, dict):
                produced = [produced]
            for state in produced or []:
                if not isinstance(state, dict):
                    continue
                state.setdefault("family_id", event.get("family_id"))
                state.setdefault("member_id", event.get("member_id"))
                state.setdefault("scope", event.get("scope"))
                state.setdefault("source_event_id", event.get("event_id"))
                states.append(self.upsert_state(state))
        return states

    @staticmethod
    def _trend(previous: float | None, current: float | None) -> str:
        if previous is None or current is None:
            return "stable"
        if current > previous + 0.08:
            return "up"
        if current < previous - 0.08:
            return "down"
        return "stable"

