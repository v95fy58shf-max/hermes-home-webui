"""Family relationship signal analyzer."""

from __future__ import annotations

from typing import Any

from core.privacy import SUMMARY_ONLY


class FamilyRelationAnalyzer:
    name = "family_relation"

    MEMBERS = ["妈妈", "爸爸", "孩子", "儿子", "女儿", "爷爷", "奶奶", "老婆", "老公"]
    TENSION = ["吵架", "讨厌", "不理", "生气", "冲突", "烦", "不想见", "骂"]
    SUPPORT = ["帮", "照顾", "陪", "支持", "安慰", "谢谢", "辛苦"]

    def analyze(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        if event.get("type") != "chat_message":
            return []
        text = str((event.get("payload") or {}).get("text") or "")
        mentions = [member for member in self.MEMBERS if member in text]
        if not mentions:
            return []
        tension_hits = sum(1 for word in self.TENSION if word in text)
        support_hits = sum(1 for word in self.SUPPORT if word in text)
        states: list[dict[str, Any]] = []
        if tension_hits:
            states.append({
                "type": "relationship/tension",
                "scope": SUMMARY_ONLY,
                "value": min(0.95, 0.35 + tension_hits * 0.16),
                "confidence": min(0.82, 0.42 + tension_hits * 0.1),
                "ttl": 72 * 3600,
                "importance": 3,
                "decay": 0.12,
                "summary": "家庭关系压力信号升高",
                "related_members": mentions,
            })
        if support_hits:
            states.append({
                "type": "relationship/support",
                "scope": SUMMARY_ONLY,
                "value": min(0.95, 0.35 + support_hits * 0.16),
                "confidence": min(0.82, 0.42 + support_hits * 0.1),
                "ttl": 7 * 24 * 3600,
                "importance": 3,
                "decay": 0.05,
                "summary": "家庭支持行为信号",
                "related_members": mentions,
            })
        return states
