"""Core Tools 装配。

按 PRD 第二节，启动时内置 5 个核心工具，工具名严格对齐：
  terminal, python_repl, fetch_url, read_file, search_knowledge_base
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Type

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from langchain_community.tools.file_management import ReadFileTool
from langchain_experimental.tools import PythonREPLTool
from pydantic import BaseModel, Field

from config import MAX_TOOL_RESULT_CHARS, SANDBOX_ROOT, SENSITIVE_FILENAMES
from tools.fetch_url import FetchUrlTool
from tools.terminal import TerminalTool


def _truncate(text: str) -> str:
    """统一截断工具输出，防止超大结果灌入历史持续烧 token。"""
    if text is not None and len(text) > MAX_TOOL_RESULT_CHARS:
        return text[:MAX_TOOL_RESULT_CHARS] + "\n\n...[truncated，输出过长已截断]"
    return text


class _SafeReadFileInput(BaseModel):
    file_path: str = Field(description="要读取的文件路径（相对于项目根目录）")


class SafeReadFileTool(ReadFileTool):
    """ReadFileTool 加固版：限定沙箱、拒读敏感文件、截断超长输出。"""

    name: str = "read_file"
    description: str = (
        "读取项目内指定文件的内容（路径相对于项目根目录）。"
        "这是使用技能的核心：调用技能前必须先用本工具读取其 SKILL.md。"
        "也用于读取记忆文件（如 memory/MEMORY.md）。"
    )
    args_schema: Type[BaseModel] = _SafeReadFileInput

    def _run(  # type: ignore[override]
        self,
        file_path: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        if Path(file_path).name in SENSITIVE_FILENAMES:
            return f"[BLOCKED] 禁止读取敏感文件：{Path(file_path).name}（可能含 API Key 等机密）。"
        result = super()._run(file_path, run_manager=run_manager)
        return _truncate(result)


def _build_read_file() -> BaseTool:
    """ReadFileTool，root_dir 限定在项目沙箱内，禁止读取系统文件与敏感文件。"""
    return SafeReadFileTool(root_dir=str(SANDBOX_ROOT))


class _PyREPLInput(BaseModel):
    query: str = Field(description="要执行的 Python 代码；需要看到结果请用 print()")


class SafePythonREPLTool(PythonREPLTool):
    """PythonREPLTool 加固版：截断超长输出，防止灌入历史持续烧 token。"""

    name: str = "python_repl"
    description: str = (
        "执行 Python 代码并返回标准输出。用于计算、数据处理、解析 JSON、"
        "以及按技能说明书的指示运行代码。需要看到结果时请使用 print()。"
    )
    args_schema: Type[BaseModel] = _PyREPLInput

    def _run(  # type: ignore[override]
        self,
        query: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> str:
        result = super()._run(query, run_manager=run_manager)
        return _truncate(result if isinstance(result, str) else str(result))

    async def _arun(  # type: ignore[override]
        self,
        query: str,
        run_manager: Optional[object] = None,
    ) -> str:
        return self._run(query)


def _build_python_repl() -> BaseTool:
    """PythonREPLTool（加固版）：赋予逻辑计算 / 数据处理 / 脚本执行能力。"""
    return SafePythonREPLTool()


def build_core_tools() -> list[BaseTool]:
    """返回核心工具实例列表。

    search_knowledge_base 在 Phase 4 接入 LlamaIndex；此处延迟导入，
    缺少 RAG 依赖或索引时自动降级跳过，不影响其余工具加载。
    """
    tools: list[BaseTool] = [
        TerminalTool(),
        _build_python_repl(),
        FetchUrlTool(),
        _build_read_file(),
    ]

    try:
        from tools.knowledge_base import build_knowledge_base_tool

        tools.append(build_knowledge_base_tool())
    except Exception as exc:  # noqa: BLE001 —— RAG 依赖/索引未就绪时降级
        print(f"[tools] search_knowledge_base 暂不可用（{exc}），已跳过。")

    return tools
