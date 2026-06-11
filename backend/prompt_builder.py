"""System Prompt 动态拼接（PRD 第四节）。

按固定顺序拼接 6 部分：
  1. SKILLS_SNAPSHOT.md (能力列表，实时生成)
  2. SOUL.md            (核心设定)
  3. IDENTITY.md        (自我认知)
  4. USER.md            (用户画像)
  5. AGENTS.md          (行为准则 & 记忆操作指南)
  6. MEMORY.md          (长期记忆)

截断策略：单文件超过 MAX_FILE_CHARS 字符时截断并追加 ...[truncated]。
"""
from __future__ import annotations

from pathlib import Path

from config import (
    AGENTS_FILE,
    IDENTITY_FILE,
    MAX_FILE_CHARS,
    MEMORY_FILE,
    SOUL_FILE,
    USER_FILE,
)
from skills_manager import generate_snapshot


def _read_truncated(path: Path) -> str:
    """读取文件；不存在返回空串；超长则截断并标注。"""
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8")
    if len(text) > MAX_FILE_CHARS:
        text = text[:MAX_FILE_CHARS] + "\n...[truncated]"
    return text.strip()


def build_system_prompt() -> str:
    """实时生成并拼接 6 段 System Prompt。"""
    # 第 1 段：实时扫描技能并生成快照
    snapshot = generate_snapshot()
    if len(snapshot) > MAX_FILE_CHARS:
        snapshot = snapshot[:MAX_FILE_CHARS] + "\n...[truncated]"

    sections: list[tuple[str, str]] = [
        ("AVAILABLE SKILLS (能力列表)", snapshot),
        ("SOUL (核心设定)", _read_truncated(SOUL_FILE)),
        ("IDENTITY (自我认知)", _read_truncated(IDENTITY_FILE)),
        ("USER PROFILE (用户画像)", _read_truncated(USER_FILE)),
        ("OPERATING GUIDE (行为准则 & 记忆操作指南)", _read_truncated(AGENTS_FILE)),
        ("LONG-TERM MEMORY (长期记忆)", _read_truncated(MEMORY_FILE)),
    ]

    parts: list[str] = []
    for title, body in sections:
        if not body:
            continue
        parts.append(f"# ===== {title} =====\n\n{body}")

    return "\n\n".join(parts)
