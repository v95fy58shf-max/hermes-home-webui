"""Privacy scopes for Hermes Home events, states, and memories."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class PrivacyScope(StrEnum):
    PRIVATE = "private"
    FAMILY_SHARED = "family_shared"
    SUMMARY_ONLY = "summary_only"
    PARENT_VISIBLE = "parent_visible"
    SYSTEM_ONLY = "system_only"
    AGENT_SAFE = "agent_safe"


PRIVATE = PrivacyScope.PRIVATE.value
FAMILY_SHARED = PrivacyScope.FAMILY_SHARED.value
SUMMARY_ONLY = PrivacyScope.SUMMARY_ONLY.value
PARENT_VISIBLE = PrivacyScope.PARENT_VISIBLE.value
SYSTEM_ONLY = PrivacyScope.SYSTEM_ONLY.value
AGENT_SAFE = PrivacyScope.AGENT_SAFE.value

VALID_SCOPES = {scope.value for scope in PrivacyScope}


def normalize_scope(scope: str | None, default: PrivacyScope = PrivacyScope.PRIVATE) -> str:
    value = str(scope or "").strip().lower()
    return value if value in VALID_SCOPES else default.value


def default_event_scope(event_type: str, payload: dict[str, Any] | None = None) -> str:
    payload = payload or {}
    if event_type in {"device_status", "nas_status", "system_metric"}:
        return SYSTEM_ONLY
    if event_type in {"member_joined", "member_renamed", "family_decision", "schedule"}:
        return FAMILY_SHARED
    if event_type in {"emotion_event", "health_event", "relationship_signal"}:
        return PRIVATE
    if event_type == "chat_message":
        text = str(payload.get("text") or payload.get("content") or "")
        private_signals = ["讨厌", "不想说", "别告诉", "秘密", "压力", "难受", "焦虑", "害怕"]
        if any(signal in text for signal in private_signals):
            return PRIVATE
    return PRIVATE


def can_inject(scope: str, allowed_scopes: set[str]) -> bool:
    normalized = normalize_scope(scope)
    return normalized in allowed_scopes or AGENT_SAFE in allowed_scopes


def sanitize_for_scope(payload: dict[str, Any], scope: str) -> dict[str, Any]:
    normalized = normalize_scope(scope)
    if normalized in {PRIVATE, SYSTEM_ONLY}:
        return {
            "summary": payload.get("summary") or payload.get("title") or "private state available",
            "redacted": True,
        }
    if normalized == SUMMARY_ONLY:
        return {
            "summary": payload.get("summary") or payload.get("content") or payload.get("text") or "",
            "redacted": True,
        }
    return dict(payload)
