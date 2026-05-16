"""Elderly and household health event analyzer."""

from __future__ import annotations

from typing import Any

from core.privacy import SUMMARY_ONLY


class ElderlyHealthAnalyzer:
    name = "elderly_health"

    HEALTH = ["复诊", "体检", "住院", "手术", "吃药", "用药", "血压", "血糖", "头晕", "发烧", "咳嗽", "疼"]
    ELDERLY = ["爷爷", "奶奶", "外公", "外婆", "老人"]

    def analyze(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        if event.get("type") != "chat_message":
            return []
        text = str((event.get("payload") or {}).get("text") or "")
        health_hits = sum(1 for word in self.HEALTH if word in text)
        if not health_hits:
            return []
        elderly_hits = sum(1 for word in self.ELDERLY if word in text)
        importance = 4 if elderly_hits else 3
        return [{
            "type": "health/event",
            "scope": SUMMARY_ONLY,
            "value": min(0.95, 0.45 + health_hits * 0.12),
            "confidence": min(0.86, 0.45 + health_hits * 0.1),
            "ttl": None,
            "importance": importance,
            "decay": 0,
            "summary": "家庭健康相关事件信号",
        }]
