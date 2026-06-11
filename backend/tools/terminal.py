"""terminal 工具：在沙箱内执行 Shell 命令。

基于 LangChain 内置 ShellTool，叠加两层防护（PRD 要求）：
1. root_dir 沙箱：命令在 backend/ 目录下执行（cwd 限定）。
2. 黑名单：拦截高危指令（rm -rf /、磁盘格式化、关机等）。

说明：这是"防误操作"级别的防护，而非对抗恶意攻击的安全沙箱。
Python REPL / Shell 在本质上无法完全防逃逸，部署到不可信环境前需加容器级隔离。
工具名固定为 `terminal`。
"""
from __future__ import annotations

import re
import subprocess
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from config import MAX_TOOL_RESULT_CHARS, SANDBOX_ROOT

# 高危指令模式（命中即拒绝执行）
_BLACKLIST: list[re.Pattern[str]] = [
    re.compile(r"\brm\s+-rf\s+/(?:\s|$)"),       # rm -rf /
    re.compile(r"\brm\s+-rf\s+~(?:/|\s|$)"),     # rm -rf ~
    re.compile(r"\brm\s+-rf\s+\*"),               # rm -rf *
    re.compile(r":\(\)\s*\{.*\};:"),              # fork bomb :(){ :|:& };:
    re.compile(r"\bmkfs\b"),                       # 格式化文件系统
    re.compile(r"\bdd\s+if=.*of=/dev/"),          # 写裸设备
    re.compile(r">\s*/dev/sd[a-z]"),              # 覆写磁盘
    re.compile(r"\b(shutdown|reboot|halt|poweroff)\b"),
    re.compile(r"\b(mkfs|fdisk|parted)\b"),
    re.compile(r"\bchmod\s+-R\s+777\s+/"),
    re.compile(r"\b(curl|wget)\b.*\|\s*(sh|bash)\b"),  # 下载即执行
]


class TerminalInput(BaseModel):
    command: str = Field(description="要执行的 Shell 命令")


def _is_blocked(command: str) -> str | None:
    for pat in _BLACKLIST:
        if pat.search(command):
            return pat.pattern
    return None


class TerminalTool(BaseTool):
    """在沙箱内执行 Shell 命令，高危指令会被拦截。"""

    name: str = "terminal"
    description: str = (
        "在受限沙箱内执行 Shell 命令（工作目录限定在项目内）。"
        "可用于运行脚本、查看文件列表、管理工作区文件等。"
        "高危命令（如 rm -rf /、关机、格式化）会被拦截。"
    )
    args_schema: Type[BaseModel] = TerminalInput

    def _run(self, command: str) -> str:  # type: ignore[override]
        blocked = _is_blocked(command)
        if blocked:
            return f"[BLOCKED] 命令被安全策略拦截（命中高危模式：{blocked}）。请改用更安全的方式。"
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(SANDBOX_ROOT),
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            return "命令执行超时（>60s），已终止。"
        except Exception as exc:  # noqa: BLE001
            return f"命令执行出错：{exc}"

        out = (result.stdout or "").strip()
        err = (result.stderr or "").strip()
        parts: list[str] = []
        if out:
            parts.append(out)
        if err:
            parts.append(f"[stderr]\n{err}")
        if result.returncode != 0:
            parts.append(f"[exit code: {result.returncode}]")
        output = "\n".join(parts) if parts else "（命令执行完毕，无输出）"
        if len(output) > MAX_TOOL_RESULT_CHARS:
            output = output[:MAX_TOOL_RESULT_CHARS] + "\n\n...[truncated，输出过长已截断]"
        return output

    async def _arun(self, command: str) -> str:  # type: ignore[override]
        return self._run(command)
