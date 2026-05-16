"""Canonical Event Bus for Hermes Home.

Every input should become a structured event before it is considered for
state, memory, or LLM prompt injection.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .privacy import default_event_scope, normalize_scope


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventBus:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.init_db()

    def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    family_id TEXT NOT NULL,
                    member_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    type TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    visibility TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    raw_json TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_family_time ON events(family_id, created_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_member_time ON events(member_id, created_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_events_type_time ON events(type, created_at DESC)")
            conn.commit()

    def normalize(
        self,
        raw: dict[str, Any],
        *,
        family_id: str,
        event_type: str = "chat_message",
        scope: str | None = None,
    ) -> dict[str, Any]:
        source = raw.get("source") or {}
        payload = {
            "text": raw.get("text") or "",
            "content": raw.get("text") or "",
            "message_id": raw.get("message_id") or "",
            "gateway_id": raw.get("gateway_id") or "",
            "source": source,
        }
        normalized_scope = normalize_scope(scope or raw.get("scope") or raw.get("visibility") or default_event_scope(event_type, payload))
        raw_event_id = raw.get("event_id")
        if not raw_event_id and raw.get("gateway_id") and raw.get("message_id"):
            raw_event_id = f"{family_id}:{raw.get('gateway_id')}:{raw.get('message_id')}"
        return {
            "event_id": str(raw_event_id or uuid.uuid4()),
            "family_id": str(raw.get("family_id") or family_id or "default"),
            "member_id": str(raw.get("member_id") or raw.get("gateway_id") or "unknown"),
            "source": str(source.get("platform") or raw.get("source_name") or "wechat"),
            "type": str(raw.get("type") or event_type),
            "scope": normalized_scope,
            "visibility": normalized_scope,
            "timestamp": str(raw.get("timestamp") or utc_now()),
            "payload": payload,
            "raw": raw,
        }

    def publish(self, event: dict[str, Any]) -> dict[str, Any]:
        event = dict(event)
        event["scope"] = normalize_scope(event.get("scope") or event.get("visibility"))
        event["visibility"] = event["scope"]
        event.setdefault("event_id", str(uuid.uuid4()))
        event.setdefault("timestamp", utc_now())
        event.setdefault("payload", {})
        now = int(time.time())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO events (
                    event_id, family_id, member_id, source, type, scope, visibility,
                    timestamp, created_at, payload_json, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event["event_id"],
                    event.get("family_id") or "default",
                    event.get("member_id") or "unknown",
                    event.get("source") or "unknown",
                    event.get("type") or "unknown",
                    event["scope"],
                    event["visibility"],
                    event["timestamp"],
                    now,
                    json.dumps(event.get("payload") or {}, ensure_ascii=False),
                    json.dumps(event.get("raw") or event, ensure_ascii=False),
                ),
            )
            conn.commit()
        return event

    def publish_raw(self, raw: dict[str, Any], *, family_id: str, event_type: str = "chat_message") -> dict[str, Any]:
        return self.publish(self.normalize(raw, family_id=family_id, event_type=event_type))
