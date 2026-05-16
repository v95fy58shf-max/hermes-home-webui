"""Low-token emotion and stress analyzer."""

from __future__ import annotations

from typing import Any

from core.privacy import PRIVATE


class EmotionAnalyzer:
    name = "emotion"

    STRESS = ["压力", "焦虑", "烦", "崩溃", "紧张", "撑不住", "失眠", "难受", "心累"]
    POSITIVE = ["开心", "高兴", "顺利", "放心", "舒服", "轻松", "喜欢"]
    NEGATIVE = ["讨厌", "生气", "委屈", "害怕", "难过", "不想", "失望"]

    def analyze(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        if event.get("type") != "chat_message":
            return []
        text = str((event.get("payload") or {}).get("text") or "")
        states: list[dict[str, Any]] = []
        stress_hits = sum(1 for word in self.STRESS if word in text)
        negative_hits = sum(1 for word in self.NEGATIVE if word in text)
        positive_hits = sum(1 for word in self.POSITIVE if word in text)
        if stress_hits:
            states.append({
                "type": "emotion/stress",
                "scope": PRIVATE,
                "value": min(0.95, 0.45 + stress_hits * 0.14 + negative_hits * 0.08),
                "confidence": min(0.9, 0.45 + stress_hits * 0.12),
                "ttl": 48 * 3600,
                "importance": 2 + min(2, stress_hits),
                "decay": 0.15,
            })
        if negative_hits:
            states.append({
                "type": "emotion/negative",
                "scope": PRIVATE,
                "value": min(0.95, 0.4 + negative_hits * 0.15),
                "confidence": min(0.85, 0.42 + negative_hits * 0.1),
                "ttl": 24 * 3600,
                "importance": 2,
                "decay": 0.2,
            })
        if positive_hits:
            states.append({
                "type": "emotion/positive",
                "scope": PRIVATE,
                "value": min(0.95, 0.4 + positive_hits * 0.15),
                "confidence": min(0.85, 0.42 + positive_hits * 0.1),
                "ttl": 24 * 3600,
                "importance": 2,
                "decay": 0.2,
            })
        return states
