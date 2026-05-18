#!/usr/bin/env python3
"""Hermes Home master gateway.

Receives messages from slave Hermes gateway profiles, records them centrally,
asks the master Hermes profile for a reply, then sends the reply through the
originating Weixin account.
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import re
import sqlite3
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:
    yaml = None


ROOT = Path("/opt/hermes-home")
CONFIG_PATH = ROOT / "config.yaml"
DB_PATH = ROOT / "home.db"
CONFIG_LOCK = threading.Lock()
HOME_SLAVE_ALLOW_ALL = ["*"]


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    text = CONFIG_PATH.read_text(encoding="utf-8")
    if yaml is not None:
        return yaml.safe_load(text) or {}

    # Tiny fallback parser for the simple config shape we write.
    cfg: dict[str, Any] = {"slaves": {}}
    current_slave: str | None = None
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if indent == 0 and line.endswith(":"):
            section = line[:-1]
            cfg.setdefault(section, {})
            current_slave = None
        elif indent == 2 and line.endswith(":") and "slaves:" in text:
            current_slave = line[:-1]
            cfg.setdefault("slaves", {}).setdefault(current_slave, {})
        elif ":" in line:
            key, value = line.split(":", 1)
            value = value.strip().strip("'\"")
            if current_slave and indent >= 4:
                cfg["slaves"][current_slave][key.strip()] = value
            else:
                cfg[key.strip()] = value
    return cfg


def save_config(cfg: dict[str, Any]) -> None:
    if yaml is None:
        raise RuntimeError("PyYAML is required to update Hermes Home config")
    with CONFIG_LOCK:
        CONFIG_PATH.write_text(
            yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )


def normalize_slave_allowlists() -> None:
    """Registered member gateways should not be pinned to stale WeChat OpenIDs."""
    cfg = load_config()
    slaves = cfg.get("slaves")
    if not isinstance(slaves, dict):
        return
    changed = False
    for gateway_id, slave in slaves.items():
        if not isinstance(slave, dict):
            continue
        if slave.get("allowed_user_ids") != HOME_SLAVE_ALLOW_ALL:
            slave["allowed_user_ids"] = list(HOME_SLAVE_ALLOW_ALL)
            changed = True
            log_line(f"normalized allowlist gateway_id={gateway_id} allowed_user_ids=*")
    if changed:
        save_config(cfg)


def init_db() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS inbound_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at INTEGER NOT NULL,
                gateway_id TEXT NOT NULL,
                member_id TEXT NOT NULL,
                platform TEXT,
                chat_id TEXT,
                user_id TEXT,
                user_name TEXT,
                message_id TEXT,
                text TEXT NOT NULL,
                raw_json TEXT NOT NULL,
                UNIQUE(gateway_id, message_id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outbound_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at INTEGER NOT NULL,
                gateway_id TEXT NOT NULL,
                chat_id TEXT,
                text TEXT NOT NULL,
                status TEXT NOT NULL,
                error TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS family_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at INTEGER NOT NULL,
                occurred_at INTEGER NOT NULL,
                gateway_id TEXT,
                member_id TEXT,
                source TEXT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT,
                importance INTEGER DEFAULT 3,
                raw_json TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_family_logs_occurred_at ON family_logs(occurred_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_family_logs_member_id ON family_logs(member_id)")
        conn.commit()


def log_line(message: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {message}", flush=True)


def read_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if not path.exists():
        return env
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip("'\"")
    return env


def get_slave(cfg: dict[str, Any], gateway_id: str) -> dict[str, Any] | None:
    slaves = cfg.get("slaves") or {}
    if not isinstance(slaves, dict):
        return None
    slave = slaves.get(gateway_id)
    return slave if isinstance(slave, dict) else None


def slave_needs_onboarding(gateway_id: str, slave: dict[str, Any]) -> bool:
    name = str(slave.get("member_name") or "").strip()
    member_id = str(slave.get("member_id") or "").strip()
    return not name or name == gateway_id or name == member_id or re.fullmatch(r"wechat\d+", name) is not None


def extract_member_name(text: str) -> str | None:
    cleaned = re.sub(r"\s+", "", text or "")
    patterns = [
        r"(?:我是|我叫|叫我|你可以叫我)([\u4e00-\u9fffA-Za-z0-9_\-]{1,16})",
        r"(?:这里是|这边是)([\u4e00-\u9fffA-Za-z0-9_\-]{1,16})",
    ]
    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            name = match.group(1).strip("，。,.！!？?")
            if name and name not in {"谁", "什么", "一个人"}:
                return name[:16]
    kinship = [
        "爸爸", "妈妈", "爷爷", "奶奶", "外公", "外婆", "哥哥", "姐姐", "弟弟", "妹妹",
        "老婆", "老公", "儿子", "女儿", "叔叔", "阿姨",
    ]
    for word in kinship:
        if cleaned == word or cleaned.startswith(f"我是{word}") or cleaned.startswith(f"叫我{word}"):
            return word
    return None


def update_slave_member_name(gateway_id: str, member_name: str) -> None:
    cfg = load_config()
    slaves = cfg.setdefault("slaves", {})
    slave = slaves.setdefault(gateway_id, {})
    slave["member_name"] = member_name
    slave.setdefault("member_id", gateway_id)
    save_config(cfg)


def save_member_identity_log(gateway_id: str, member_name: str, event: dict[str, Any]) -> None:
    now = int(time.time())
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO family_logs (
                created_at, occurred_at, gateway_id, member_id, source, title, content, tags, importance, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                now,
                gateway_id,
                member_name,
                str((event.get("source") or {}).get("platform") or ""),
                "成员身份确认",
                f"{gateway_id} 的成员显示名设定为 {member_name}。",
                "成员,身份,onboarding",
                4,
                json.dumps({"event": event, "member_name": member_name}, ensure_ascii=False),
            ),
        )
        conn.commit()


def is_allowed(slave: dict[str, Any], event: dict[str, Any]) -> bool:
    if slave.get("hermes_home"):
        return True
    allowed = slave.get("allowed_user_ids") or []
    if isinstance(allowed, str):
        allowed = [x.strip() for x in allowed.split(",") if x.strip()]
    if not allowed or "*" in allowed:
        return True
    source = event.get("source") or {}
    user_id = str(source.get("user_id") or "")
    chat_id = str(source.get("chat_id") or "")
    return user_id in allowed or chat_id in allowed


def save_inbound(event: dict[str, Any]) -> bool:
    source = event.get("source") or {}
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO inbound_messages (
                    created_at, gateway_id, member_id, platform, chat_id,
                    user_id, user_name, message_id, text, raw_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    int(time.time()),
                    event.get("gateway_id", ""),
                    event.get("member_id", ""),
                    source.get("platform", ""),
                    source.get("chat_id", ""),
                    source.get("user_id", ""),
                    source.get("user_name", ""),
                    event.get("message_id", ""),
                    event.get("text", ""),
                    json.dumps(event, ensure_ascii=False),
                ),
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False


def save_outbound(gateway_id: str, chat_id: str, text: str, status: str, error: str = "") -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO outbound_messages (created_at, gateway_id, chat_id, text, status, error)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (int(time.time()), gateway_id, chat_id, text, status, error),
        )
        conn.commit()


FAMILY_LOG_SIGNAL_WORDS = [
    "记住", "提醒", "以后", "下次", "之前", "上次", "长期", "习惯", "偏好", "喜欢", "不喜欢",
    "约", "安排", "计划", "决定", "承诺", "报名", "预约", "复诊", "体检", "手术", "住院", "用药",
    "生日", "纪念日", "搬家", "结婚", "怀孕", "出生", "毕业", "入学", "升学", "考试", "获奖",
    "升职", "入职", "离职", "买房", "装修", "旅行", "签证", "保险", "合同", "付款", "账单",
    "爸爸", "妈妈", "爷爷", "奶奶", "外公", "外婆", "孩子", "老婆", "老公", "我们家", "全家",
]

TIME_PATTERN = re.compile(r"(\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}|明天|后天|下周|周[一二三四五六日天]|星期[一二三四五六日天]|\d{1,2}点|\d{1,2}:\d{2})")


def should_retrieve_family_logs(text: str) -> bool:
    if TIME_PATTERN.search(text):
        return True
    return any(word in text for word in FAMILY_LOG_SIGNAL_WORDS)


def search_family_logs(text: str, limit: int = 6) -> list[dict[str, Any]]:
    if not should_retrieve_family_logs(text):
        return []
    candidates = [word for word in FAMILY_LOG_SIGNAL_WORDS if word in text]
    candidates += re.findall(r"[\w\u4e00-\u9fff]{2,}", text)[:6]
    seen: set[str] = set()
    terms = [term for term in candidates if not (term in seen or seen.add(term))][:8]
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if terms:
            where = " OR ".join(["title LIKE ? OR content LIKE ? OR tags LIKE ? OR member_id LIKE ?" for _ in terms])
            params: list[Any] = []
            for term in terms:
                params.extend([f"%{term}%", f"%{term}%", f"%{term}%", f"%{term}%"])
            rows = conn.execute(
                f"""
                SELECT * FROM family_logs
                WHERE {where}
                ORDER BY importance DESC, occurred_at DESC
                LIMIT ?
                """,
                [*params, limit],
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT * FROM family_logs
                WHERE importance >= 4
                ORDER BY occurred_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [dict(row) for row in rows]


def format_family_logs(logs: list[dict[str, Any]]) -> str:
    if not logs:
        return ""
    lines = ["可按需参考的共享记忆（只在相关时使用，不要主动暴露内部机制）："]
    for item in logs:
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(int(item.get("occurred_at") or item.get("created_at") or time.time())))
        tags = item.get("tags") or ""
        member = item.get("member_id") or item.get("gateway_id") or "共享"
        lines.append(f"- [{when}] {member}: {item.get('title', '')}。{item.get('content', '')} {tags}".strip())
    return "\n".join(lines)


def parse_log_time(value: str, fallback: int) -> int:
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M", "%Y/%m/%d"):
        try:
            return int(time.mktime(time.strptime(value, fmt)))
        except Exception:
            pass
    return fallback


def save_family_log(entry: dict[str, Any], event: dict[str, Any], slave: dict[str, Any]) -> None:
    now = int(time.time())
    source = event.get("source") or {}
    occurred_at = parse_log_time(str(entry.get("occurred_at") or ""), now)
    tags = entry.get("tags") or []
    if isinstance(tags, list):
        tags = ",".join(str(x).strip() for x in tags if str(x).strip())
    importance = int(entry.get("importance") or 3)
    importance = max(1, min(5, importance))
    title = str(entry.get("title") or "").strip()[:120]
    content = str(entry.get("content") or "").strip()
    if not title or not content:
        return
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO family_logs (
                created_at, occurred_at, gateway_id, member_id, source, title, content, tags, importance, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now,
                occurred_at,
                event.get("gateway_id", ""),
                event.get("member_id", "") or slave.get("member_id", ""),
                str(source.get("platform") or ""),
                title,
                content,
                str(tags),
                importance,
                json.dumps({"event": event, "entry": entry}, ensure_ascii=False),
            ),
        )
        conn.commit()


def maybe_save_family_log(cfg: dict[str, Any], slave: dict[str, Any], event: dict[str, Any], reply: str) -> None:
    if cfg.get("family_log_enabled", True) is False:
        return
    text = event.get("text") or ""
    source = event.get("source") or {}
    member_name = slave.get("member_name") or event.get("member_id") or event.get("gateway_id")
    now_text = time.strftime("%Y-%m-%d %H:%M:%S")
    prompt = f"""你是共享记忆管理员。请使用 shared-memory skill 的保存标准，判断这轮成员对话是否值得长期保存到“共享记忆”。

保存标准要多方面判断，包括但不限于：
- 多人或组织共同相关的事实、决定、承诺、冲突、分工、共识
- 明确时间点、地点、预约、日程、待办、截止日期
- 健康、用药、复诊、学校、工作、财务、合同、居住、旅行等长期有用信息
- 成就、大事件、里程碑，例如获奖、升学、毕业、入职、升职、搬家、结婚、出生、重要纪念日
- 稳定偏好、禁忌、习惯、关系变化、需要以后持续照顾的上下文

不要保存普通寒暄、临时情绪、一次性闲聊、无长期价值的问答。
如果保存，必须给出明确 occurred_at。若消息没有明确发生时间，就使用当前时间。

当前时间：{now_text}
成员：{member_name}
来源：{source.get("platform", "unknown")}
成员消息：{text}
AI回复：{reply}

只输出 JSON，不要解释：
{{
  "save": true/false,
  "occurred_at": "YYYY-MM-DD HH:MM",
  "title": "短标题",
  "content": "可长期检索的一段事实记录",
  "tags": ["健康","日程","成就","组织决定","偏好","大事件"] 中选择或自定义,
  "importance": 1-5
}}
"""
    try:
        raw = run_hermes(cfg, prompt)
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return
        entry = json.loads(raw[start:end + 1])
        if entry.get("save") is True:
            save_family_log(entry, event, slave)
            log_line(f"family log saved gateway_id={event.get('gateway_id')} title={entry.get('title')}")
    except Exception as exc:
        log_line(f"family log skip error gateway_id={event.get('gateway_id')}: {exc}")


def build_prompt(cfg: dict[str, Any], slave: dict[str, Any], event: dict[str, Any]) -> str:
    source = event.get("source") or {}
    member_name = slave.get("member_name") or event.get("member_id") or event.get("gateway_id")
    household = cfg.get("household_name") or cfg.get("workspace_name") or "组织"
    text = event.get("text") or ""
    family_context = format_family_logs(search_family_logs(text))
    family_context_block = f"\n{family_context}\n" if family_context else ""
    return f"""你是 {household} 的主网关 agent。
如当前问题涉及长期共享事实、共享记忆检索结果、多人共同背景、日程、健康、成就或大事件，请按 shared-memory skill 的原则处理。

当前消息来自成员：{member_name}
来源渠道：{source.get("platform", "unknown")}
会话类型：{source.get("chat_type", "dm")}

请只回复要发给这个成员的一段微信消息。不要解释系统架构，不要输出 JSON。
如果用户要求控制门锁、支付、下单、安防关闭等高风险动作，必须先要求确认。
{family_context_block}

成员消息：
{text}
"""


def run_hermes(cfg: dict[str, Any], prompt: str) -> str:
    hermes_bin = cfg.get("hermes_bin") or "/usr/local/lib/hermes-agent/venv/bin/hermes"
    profile = cfg.get("master_profile") or "default"
    timeout = int(cfg.get("hermes_timeout_seconds") or 240)
    cmd = [str(hermes_bin)]
    if profile and profile != "default":
        cmd += ["-p", str(profile)]
    cmd += ["-z", prompt]
    env = os.environ.copy()
    env["HERMES_ACCEPT_HOOKS"] = "1"
    proc = subprocess.run(
        cmd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        env=env,
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(err[-1000:] or f"hermes exited with {proc.returncode}")
    reply = (proc.stdout or "").strip()
    return reply or "我这边没有生成有效回复。"


async def send_weixin(slave: dict[str, Any], chat_id: str, message: str) -> dict[str, Any]:
    hermes_home = Path(slave.get("hermes_home") or "")
    env = read_env_file(hermes_home / ".env")
    if not env:
        raise RuntimeError(f"missing slave env: {hermes_home / '.env'}")

    os.environ["HERMES_HOME"] = str(hermes_home)
    os.environ["WEIXIN_ACCOUNT_ID"] = env.get("WEIXIN_ACCOUNT_ID", "")
    os.environ["WEIXIN_TOKEN"] = env.get("WEIXIN_TOKEN", "")
    os.environ["WEIXIN_BASE_URL"] = env.get("WEIXIN_BASE_URL", "https://ilinkai.weixin.qq.com")
    os.environ["WEIXIN_CDN_BASE_URL"] = env.get("WEIXIN_CDN_BASE_URL", "https://novac2c.cdn.weixin.qq.com/c2c")
    sys.path.insert(0, "/usr/local/lib/hermes-agent")
    from gateway.platforms.weixin import send_weixin_direct

    extra = {
        "account_id": os.environ["WEIXIN_ACCOUNT_ID"],
        "base_url": os.environ["WEIXIN_BASE_URL"],
        "cdn_base_url": os.environ["WEIXIN_CDN_BASE_URL"],
    }
    return await send_weixin_direct(extra=extra, token=os.environ["WEIXIN_TOKEN"], chat_id=chat_id, message=message)


def process_event(event: dict[str, Any]) -> None:
    cfg = load_config()
    gateway_id = str(event.get("gateway_id") or "")
    slave = get_slave(cfg, gateway_id)
    source = event.get("source") or {}
    chat_id = str(source.get("chat_id") or "")
    if not slave:
        log_line(f"drop unknown gateway_id={gateway_id}")
        return
    if not is_allowed(slave, event):
        log_line(f"drop unauthorized gateway_id={gateway_id} user={source.get('user_id')}")
        return
    if not save_inbound(event):
        log_line(f"duplicate gateway_id={gateway_id} message_id={event.get('message_id')}")
        return
    if slave_needs_onboarding(gateway_id, slave):
        member_name = extract_member_name(event.get("text") or "")
        if member_name:
            try:
                update_slave_member_name(gateway_id, member_name)
                save_member_identity_log(gateway_id, member_name, event)
                slave["member_name"] = member_name
                reply = f"好的，我记住了。之后我会把这个微信网关显示为“{member_name}”。"
                log_line(f"onboarding set gateway_id={gateway_id} member_name={member_name}")
            except Exception as exc:
                reply = "我识别到你的称呼了，但保存身份时出了点问题，稍后可以再告诉我一次。"
                log_line(f"onboarding save error gateway_id={gateway_id}: {exc}")
        else:
            reply = "欢迎加入 Hermes。我需要先知道怎么称呼你，请直接回复一句，比如“我是张三”“我叫小王”或“叫我李经理”。"
            log_line(f"onboarding ask gateway_id={gateway_id}")
        try:
            result = asyncio.run(send_weixin(slave, chat_id, reply))
            if result.get("error"):
                raise RuntimeError(result["error"])
            save_outbound(gateway_id, chat_id, reply, "sent")
        except Exception as exc:
            save_outbound(gateway_id, chat_id, reply, "error", str(exc))
            log_line(f"send error gateway_id={gateway_id}: {exc}")
        return
    try:
        prompt = build_prompt(cfg, slave, event)
        reply = run_hermes(cfg, prompt)
    except Exception as exc:
        reply = "主网关暂时没有成功生成回复，请稍后再试。"
        log_line(f"hermes error gateway_id={gateway_id}: {exc}")
    try:
        maybe_save_family_log(cfg, slave, event, reply)
    except Exception as exc:
        log_line(f"family log error gateway_id={gateway_id}: {exc}")
    try:
        result = asyncio.run(send_weixin(slave, chat_id, reply))
        if result.get("error"):
            raise RuntimeError(result["error"])
        save_outbound(gateway_id, chat_id, reply, "sent")
        log_line(f"sent gateway_id={gateway_id} chat_id={chat_id}")
    except Exception as exc:
        save_outbound(gateway_id, chat_id, reply, "error", str(exc))
        log_line(f"send error gateway_id={gateway_id}: {exc}")


work_queue: "queue.Queue[dict[str, Any]]" = queue.Queue()


def worker() -> None:
    while True:
        event = work_queue.get()
        try:
            process_event(event)
        finally:
            work_queue.task_done()


class Handler(BaseHTTPRequestHandler):
    server_version = "HermesHomeMaster/0.1"

    def _json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(200, {"ok": True, "queue": work_queue.qsize()})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/incoming":
            self._json(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(min(length, 262144))
            event = json.loads(raw.decode("utf-8"))
            if not isinstance(event, dict):
                raise ValueError("payload must be object")
            work_queue.put(event)
            self._json(202, {"accepted": True})
        except Exception as exc:
            self._json(400, {"accepted": False, "error": str(exc)})

    def log_message(self, fmt: str, *args: Any) -> None:
        log_line(fmt % args)


def main() -> None:
    normalize_slave_allowlists()
    init_db()
    cfg = load_config()
    host = str(cfg.get("listen_host") or "127.0.0.1")
    port = int(cfg.get("listen_port") or 18080)
    workers = int(cfg.get("workers") or 1)
    for _ in range(max(1, workers)):
        threading.Thread(target=worker, daemon=True).start()
    httpd = ThreadingHTTPServer((host, port), Handler)
    log_line(f"master listening on {host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
