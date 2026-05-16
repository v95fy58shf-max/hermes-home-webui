from __future__ import annotations

import json
import os
import urllib.request


MASTER_URL = os.getenv("HERMES_HOME_MASTER_URL", "http://127.0.0.1:18080/incoming")
GATEWAY_ID = os.getenv("HERMES_HOME_GATEWAY_ID", "home-slave")
MEMBER_ID = os.getenv("HERMES_HOME_MEMBER_ID", GATEWAY_ID)


def _source_to_dict(source):
    platform = getattr(source, "platform", None)
    if hasattr(platform, "value"):
        platform = platform.value
    return {
        "platform": platform or "",
        "user_id": getattr(source, "user_id", "") or "",
        "chat_id": getattr(source, "chat_id", "") or "",
        "user_name": getattr(source, "user_name", "") or "",
        "chat_type": getattr(source, "chat_type", "") or "",
    }


def relay_to_master(**kwargs):
    event = kwargs.get("event")
    if event is None:
        return {"action": "allow"}
    text = getattr(event, "text", "") or ""
    if not text.strip():
        return {"action": "allow"}

    payload = {
        "gateway_id": GATEWAY_ID,
        "member_id": MEMBER_ID,
        "message_id": getattr(event, "message_id", "") or "",
        "text": text,
        "source": _source_to_dict(getattr(event, "source", None)),
    }
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        MASTER_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as response:
            if 200 <= response.status < 300:
                return {"action": "skip", "reason": "relayed-to-home-master"}
    except Exception:
        return {"action": "allow"}
    return {"action": "allow"}


def register(ctx):
    ctx.register_hook("pre_gateway_dispatch", relay_to_master)
