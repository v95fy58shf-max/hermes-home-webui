"""Sleep signal analyzer."""

from __future__ import annotations

from typing import Any

from core.privacy import PRIVATE


class SleepAnalyzer:
    name = "sleep"

    SIGNALS = ["睡不着", "失眠", "没睡好", "熬夜", "困", "早醒", "睡眠"]

    def analyze(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        if event.get("type") != "chat_message":
            return []
        text = str((event.get("payload") or {}).get("text") or "")
        hits = sum(1 for word in self.SIGNALS if word in text)
        if not hits:
            return []
        return [{
            "type": "sleep/quality",
            "scope": PRIVATE,
            "value": max(0.05, 0.75 - hits * 0.18),
            "confidence": min(0.82, 0.44 + hits * 0.12),
            "ttl": 72 * 3600,
            "importance": 3,
            "decay": 0.1,
        }]
