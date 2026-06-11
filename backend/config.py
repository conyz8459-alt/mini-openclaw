"""集中式配置与路径管理。

所有路径在此统一定义，保证 root_dir 沙箱、记忆读写、Skills 扫描共用同一套绝对路径，
避免相对路径在不同工作目录下漂移（透明可控原则）。
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# backend/ 目录（本文件所在目录）
BACKEND_DIR: Path = Path(__file__).resolve().parent

# 加载 backend/.env（若存在）
load_dotenv(BACKEND_DIR / ".env")

# --- 核心目录 ---
MEMORY_DIR: Path = BACKEND_DIR / "memory"
LOGS_DIR: Path = MEMORY_DIR / "logs"
SESSIONS_DIR: Path = BACKEND_DIR / "sessions"
SKILLS_DIR: Path = BACKEND_DIR / "skills"
WORKSPACE_DIR: Path = BACKEND_DIR / "workspace"
KNOWLEDGE_DIR: Path = BACKEND_DIR / "knowledge"
STORAGE_DIR: Path = BACKEND_DIR / "storage"

# Agent 工具的沙箱根目录：限制 terminal / read_file 只能在 backend/ 内活动
SANDBOX_ROOT: Path = BACKEND_DIR

# System Prompt 拼接顺序中用到的文件
SKILLS_SNAPSHOT_FILE: Path = WORKSPACE_DIR / "SKILLS_SNAPSHOT.md"
SOUL_FILE: Path = WORKSPACE_DIR / "SOUL.md"
IDENTITY_FILE: Path = WORKSPACE_DIR / "IDENTITY.md"
USER_FILE: Path = WORKSPACE_DIR / "USER.md"
AGENTS_FILE: Path = WORKSPACE_DIR / "AGENTS.md"
MEMORY_FILE: Path = MEMORY_DIR / "MEMORY.md"

# --- 模型配置 ---
LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
LLM_MODEL: str = os.getenv("LLM_MODEL", "deepseek-chat")
LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.7"))

# --- Embedding 配置（RAG）---
EMBED_API_KEY: str = os.getenv("EMBED_API_KEY") or LLM_API_KEY
EMBED_BASE_URL: str = os.getenv("EMBED_BASE_URL") or LLM_BASE_URL
EMBED_MODEL: str = os.getenv("EMBED_MODEL", "text-embedding-3-small")

# --- 服务 ---
SERVER_PORT: int = int(os.getenv("SERVER_PORT", "8002"))
# 监听地址：默认 127.0.0.1（仅本机）。如需局域网访问，显式设 SERVER_HOST=0.0.0.0。
SERVER_HOST: str = os.getenv("SERVER_HOST", "127.0.0.1")
# 允许的前端来源（CORS）。逗号分隔；默认放行本地开发端口。
CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if o.strip()
]

# 单文件拼接进 System Prompt 的字符上限（超出截断，PRD 第四节）
MAX_FILE_CHARS: int = 20_000

# 单个工具结果回灌给模型 / 存进历史的字符上限（防止大输出累积烧 token）
MAX_TOOL_RESULT_CHARS: int = int(os.getenv("MAX_TOOL_RESULT_CHARS", "8000"))

# 注入模型的历史「轮」数上限（1 轮 = 1 个 user + 其后 assistant/tool 消息）。
# 仅影响发给模型的内容，磁盘上的完整会话不受影响。0 表示不限制。
MAX_HISTORY_TURNS: int = int(os.getenv("MAX_HISTORY_TURNS", "12"))

# Agent 工具禁止读取的敏感文件名（含 API Key 等机密）。
# 注意：.env.example 是无密钥模板，故不在此列，允许 Agent 读取以协助配置。
SENSITIVE_FILENAMES: set[str] = {".env", ".env.local"}


def ensure_dirs() -> None:
    """启动时确保所有核心目录存在。"""
    for d in (
        MEMORY_DIR,
        LOGS_DIR,
        SESSIONS_DIR,
        SKILLS_DIR,
        WORKSPACE_DIR,
        KNOWLEDGE_DIR,
        STORAGE_DIR,
    ):
        d.mkdir(parents=True, exist_ok=True)
