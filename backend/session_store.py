"""会话持久化（PRD 第四节 4）。

路径：backend/sessions/{session_name}.json
格式：标准 JSON 数组，每条消息含 role(user/assistant/tool) 与 content，
      助手的工具调用与工具结果一并保留，便于前端回放思考链。

在 LangChain BaseMessage 与可序列化 dict 之间双向转换。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from config import MAX_HISTORY_TURNS, SESSIONS_DIR

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9_\-]")

# 标题索引文件：session_id -> 显示标题（与文件名解耦，支持中文标题）
_TITLES_FILE = "_titles.json"


def _titles_path() -> Path:
    return SESSIONS_DIR / _TITLES_FILE


def _load_titles() -> dict[str, str]:
    path = _titles_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _save_titles(titles: dict[str, str]) -> None:
    path = _titles_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(titles, ensure_ascii=False, indent=2), encoding="utf-8")


def get_title(session_id: str) -> str | None:
    """返回会话的显示标题；未命名则返回 None。"""
    return _load_titles().get(session_id)


def set_title(session_id: str, title: str) -> None:
    """设置会话显示标题（不改文件名）。"""
    titles = _load_titles()
    titles[session_id] = title
    _save_titles(titles)


def window_history(
    messages: list[BaseMessage], max_turns: int = MAX_HISTORY_TURNS
) -> list[BaseMessage]:
    """对注入模型的历史做滑动窗口，只保留最近 max_turns 轮。

    一「轮」以一条 HumanMessage 为起点。窗口边界必须落在 HumanMessage 上，
    以保证 AIMessage.tool_calls 与其后的 ToolMessage 成对出现，
    避免截断产生「孤儿 tool 消息」导致模型 API 报错。

    max_turns <= 0 表示不限制。仅影响发给模型的内容，磁盘会话不受影响。
    """
    if max_turns <= 0 or not messages:
        return messages

    # 找到每个 HumanMessage 的下标（每个标志一轮的开始）
    human_idx = [i for i, m in enumerate(messages) if isinstance(m, HumanMessage)]
    if len(human_idx) <= max_turns:
        return messages

    # 从倒数第 max_turns 个 HumanMessage 处起截，保证轮的完整性
    start = human_idx[-max_turns]
    return messages[start:]



def _session_path(session_id: str) -> Path:
    safe = _SAFE_NAME.sub("_", session_id) or "default"
    return SESSIONS_DIR / f"{safe}.json"


def _message_to_dict(msg: BaseMessage) -> dict[str, Any]:
    role = {
        "human": "user",
        "ai": "assistant",
        "tool": "tool",
        "system": "system",
    }.get(msg.type, msg.type)
    data: dict[str, Any] = {"role": role, "content": msg.content}
    # 保留 AI 消息的工具调用，供回放
    tool_calls = getattr(msg, "tool_calls", None)
    if tool_calls:
        data["tool_calls"] = tool_calls
    # 保留工具结果对应的调用 id
    if isinstance(msg, ToolMessage):
        data["tool_call_id"] = msg.tool_call_id
        data["name"] = msg.name
    return data


def _dict_to_message(d: dict[str, Any]) -> BaseMessage:
    role = d.get("role")
    content = d.get("content", "")
    if role == "user":
        return HumanMessage(content=content)
    if role == "assistant":
        return AIMessage(content=content, tool_calls=d.get("tool_calls", []) or [])
    if role == "tool":
        return ToolMessage(
            content=content,
            tool_call_id=d.get("tool_call_id", ""),
            name=d.get("name"),
        )
    if role == "system":
        return SystemMessage(content=content)
    return HumanMessage(content=content)


def load_session(session_id: str) -> list[BaseMessage]:
    """读取历史消息（不含 System Prompt，System 每次动态拼接）。"""
    path = _session_path(session_id)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return [_dict_to_message(d) for d in raw if d.get("role") != "system"]


def read_session_raw(session_id: str) -> list[dict[str, Any]]:
    """读取会话原始 dict 列表（供前端回放，仅保留 user/assistant 的文字内容）。"""
    path = _session_path(session_id)
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    out: list[dict[str, Any]] = []
    for d in raw:
        role = d.get("role")
        if role not in ("user", "assistant"):
            continue
        content = d.get("content", "")
        # 跳过纯工具调用、无文字内容的助手消息
        if isinstance(content, str) and content.strip():
            out.append({"role": role, "content": content})
    return out


def save_session(session_id: str, messages: list[BaseMessage]) -> None:
    """覆盖写入完整消息列表（跳过 System 消息）。"""
    path = _session_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    serializable = [
        _message_to_dict(m) for m in messages if not isinstance(m, SystemMessage)
    ]
    path.write_text(
        json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def delete_session(session_id: str) -> bool:
    """删除会话文件，并清理其标题索引项。返回是否确实删除了文件。"""
    path = _session_path(session_id)
    titles = _load_titles()
    if titles.pop(session_id, None) is not None:
        _save_titles(titles)
    if path.exists():
        path.unlink()
        return True
    return False


def rename_session(session_id: str, new_title: str) -> str:
    """重命名会话 = 修改其显示标题（文件名/ session_id 不变）。

    返回生效的新标题。源会话不存在时抛 FileNotFoundError。
    """
    if not _session_path(session_id).exists():
        raise FileNotFoundError(session_id)
    title = new_title.strip()
    if not title:
        raise ValueError("标题不能为空")
    set_title(session_id, title)
    return title


def list_sessions() -> list[dict[str, Any]]:
    """列出所有历史会话（id + 显示标题 + 消息数 + 首条用户消息预览）。"""
    sessions: list[dict[str, Any]] = []
    if not SESSIONS_DIR.exists():
        return sessions
    titles = _load_titles()
    for path in sorted(SESSIONS_DIR.glob("*.json")):
        if path.name == _TITLES_FILE:  # 跳过标题索引文件本身
            continue
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        preview = ""
        for d in raw:
            if d.get("role") == "user":
                preview = str(d.get("content", ""))[:50]
                break
        sid = path.stem
        sessions.append(
            {
                "session_id": sid,
                "title": titles.get(sid) or sid,
                "message_count": len(raw),
                "preview": preview,
            }
        )
    return sessions
