"""Agent 编排核心（PRD 第一节强制 create_agent，禁用 AgentExecutor/create_react_agent）。

- 模型：ChatOpenAI，base_url 兼容 DeepSeek / OpenRouter / Claude。
- System Prompt：用 @dynamic_prompt 中间件，每次模型请求前实时拼接 6 段 prompt
  （技能快照随文件变化即时反映，无需重启）。
- 运行时：create_agent 返回 LangGraph CompiledStateGraph，支持 astream_events 流式。
"""
from __future__ import annotations

from functools import lru_cache

from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt
from langchain_openai import ChatOpenAI

from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TEMPERATURE
from prompt_builder import build_system_prompt
from tools import build_core_tools


@dynamic_prompt
def _dynamic_system_prompt(request) -> str:  # type: ignore[no-untyped-def]
    """每次模型调用前实时生成 System Prompt（6 段动态拼接）。"""
    return build_system_prompt()


def _build_model() -> ChatOpenAI:
    if not LLM_API_KEY:
        raise RuntimeError(
            "未配置 LLM_API_KEY。请复制 backend/.env.example 为 backend/.env 并填入 API Key。"
        )
    return ChatOpenAI(
        model=LLM_MODEL,
        base_url=LLM_BASE_URL,
        api_key=LLM_API_KEY,
        temperature=LLM_TEMPERATURE,
        stream_usage=True,  # 流式响应带 token 用量（usage_metadata），供前端显示成本
    )


@lru_cache(maxsize=1)
def get_agent():
    """构建并缓存 Agent（CompiledStateGraph）。

    工具集与模型在进程内固定；System Prompt 由中间件动态生成，故可安全缓存。
    """
    model = _build_model()
    tools = build_core_tools()
    agent = create_agent(
        model,
        tools=tools,
        middleware=[_dynamic_system_prompt],
    )
    return agent


async def generate_session_title(user_msg: str, assistant_msg: str) -> str:
    """据首轮对话内容提炼一个简短中文标题（用于会话自动命名）。

    复用对话模型，但不挂工具/不带 System Prompt，单次轻量调用。
    失败时抛异常由调用方兜底。
    """
    model = _build_model()
    prompt = (
        "请根据下面这轮对话，提炼一个简短的会话标题。"
        "要求：6~12 个字以内，用中文，概括对话主题，"
        "不要加引号、标点、序号或「标题：」之类前缀，只输出标题本身。\n\n"
        f"用户：{user_msg[:500]}\n"
        f"助手：{assistant_msg[:500]}\n\n"
        "标题："
    )
    resp = await model.ainvoke(prompt)
    title = str(getattr(resp, "content", "") or "").strip()
    # 清洗：去掉可能的引号/换行，限制长度
    title = title.replace("\n", " ").strip(" \"'“”「」：:。.")
    return title[:20]
