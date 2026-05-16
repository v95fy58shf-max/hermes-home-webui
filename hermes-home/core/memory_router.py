"""Privacy-aware memory/state router for prompt injection."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

from .privacy import AGENT_SAFE, FAMILY_SHARED, PRIVATE, SUMMARY_ONLY, sanitize_for_scope


class MemoryRouter:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def route(self, query: str, *, family_id: str, member_id: str, limit: int = 8) -> dict[str, list[dict[str, Any]]]:
        route = self._choose_route(query)
        allowed_scopes = {FAMILY_SHARED, SUMMARY_ONLY, AGENT_SAFE}
        if route.get("self_private"):
            allowed_scopes.add(PRIVATE)
        return {
            "states": self.search_states(family_id, member_id, route["state_types"], allowed_scopes, limit),
            "logs": self.search_logs(query, family_id, allowed_scopes, limit),
        }

    def _choose_route(self, query: str) -> dict[str, Any]:
        text = query or ""
        state_types: list[str] = []
        if any(word in text for word in ["压力", "情绪", "心情", "状态", "最近怎么样", "还好吗", "累", "烦"]):
            state_types += ["emotion/stress", "emotion/negative", "emotion/positive"]
        if any(word in text for word in ["关系", "吵架", "妈妈", "爸爸", "孩子", "儿子", "女儿", "家里"]):
            state_types += ["relationship/tension", "relationship/support"]
        if any(word in text for word in ["睡", "睡眠", "失眠", "睡不着", "熬夜"]):
            state_types.append("sleep/quality")
        if any(word in text for word in ["健康", "复诊", "用药", "医院", "血压", "血糖", "发烧"]):
            state_types += ["health/event", "health/history"]
        return {
            "state_types": list(dict.fromkeys(state_types)),
            "self_private": any(word in text for word in ["我", "自己", "我的", "本人"]),
        }

    def search_states(
        self,
        family_id: str,
        member_id: str,
        state_types: list[str],
        allowed_scopes: set[str],
        limit: int,
    ) -> list[dict[str, Any]]:
        if not state_types:
            return []
        placeholders = ",".join("?" for _ in state_types)
        scope_placeholders = ",".join("?" for _ in allowed_scopes)
        params = [family_id, member_id, *state_types, *allowed_scopes, limit]
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"""
                SELECT * FROM family_states
                WHERE family_id = ? AND member_id = ? AND type IN ({placeholders})
                  AND scope IN ({scope_placeholders}) AND archived = 0
                ORDER BY confidence DESC, updated_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    def search_logs(self, query: str, family_id: str, allowed_scopes: set[str], limit: int) -> list[dict[str, Any]]:
        terms = [term for term in query.replace("，", " ").replace("。", " ").split() if len(term) >= 2][:6]
        if not terms:
            return []
        scope_placeholders = ",".join("?" for _ in allowed_scopes)
        where = " OR ".join(["title LIKE ? OR content LIKE ? OR tags LIKE ?" for _ in terms])
        params: list[Any] = []
        for term in terms:
            params.extend([f"%{term}%", f"%{term}%", f"%{term}%"])
        params.extend([family_id, family_id, *allowed_scopes, limit])
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                f"""
                SELECT * FROM family_logs
                WHERE ({where}) AND COALESCE(family_id, ?) = ? AND scope IN ({scope_placeholders})
                ORDER BY importance DESC, occurred_at DESC
                LIMIT ?
                """,
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    def format_for_prompt(self, routed: dict[str, list[dict[str, Any]]]) -> str:
        lines: list[str] = []
        if routed.get("states"):
            lines.append("可按需参考的家庭状态摘要（已按隐私范围过滤，不要暴露私人原文）：")
            for item in routed["states"]:
                payload = sanitize_for_scope(dict(item), str(item.get("scope") or SUMMARY_ONLY))
                lines.append(
                    f"- {item.get('member_id')}: {item.get('type')}={item.get('value')} "
                    f"trend={item.get('trend')} confidence={item.get('confidence')} {payload.get('summary', '')}"
                )
        if routed.get("logs"):
            lines.append("可按需参考的家庭日志（只在相关时使用）：")
            for item in routed["logs"]:
                when = time.strftime("%Y-%m-%d %H:%M", time.localtime(int(item.get("occurred_at") or time.time())))
                lines.append(f"- [{when}] {item.get('member_id') or '家庭'}: {item.get('title')}。{item.get('content')}")
        return "\n".join(lines)
