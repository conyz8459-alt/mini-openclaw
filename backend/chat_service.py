"""对话服务：驱动 Agent 并把 LangGraph 事件流转成 SSE 事件。

SSE 事件类型（前端据此渲染思考链）：
  - token        : 助手回复的增量文本
  - tool_start   : 开始调用某工具（含工具名与入参）
  - tool_end     : 工具返回结果
  - final        : 本轮最终完整回复
  - error        : 出错信息
  - done         : 流结束标记
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from agent_core import generate_session_title, get_agent
from session_store import get_title, load_session, save_session, set_title, window_history


def _sse(event: str, data: dict[str, Any]) -> str:
    """格式化为一条 SSE 记录。"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_chat(message: str, session_id: str) -> AsyncIterator[str]:
    """运行一轮对话，逐事件 yield SSE 字符串。"""
    agent = get_agent()
    full_history = load_session(session_id)
    is_first_turn = len(full_history) == 0  # 本轮之前无任何历史 => 首轮
    full_history.append(HumanMessage(content=message))
    # 仅给模型注入最近若干轮（省 token）；磁盘仍保存完整历史
    history = window_history(full_history)
    # 窗口外的旧消息（本轮不注入，但要保留以便完整持久化）
    dropped = full_history[: len(full_history) - len(history)]

    final_messages: list[Any] = []
    final_text = ""

    try:
        async for event in agent.astream_events(
            {"messages": history}, version="v2"
        ):
            kind = event.get("event")

            if kind == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                text = getattr(chunk, "content", "") if chunk else ""
                if text:
                    final_text += text
                    yield _sse("token", {"text": text})

            elif kind == "on_tool_start":
                yield _sse(
                    "tool_start",
                    {
                        "name": event.get("name", ""),
                        "input": event["data"].get("input", {}),
                    },
                )

            elif kind == "on_tool_end":
                output = event["data"].get("output")
                # output 可能是 ToolMessage 或原始值
                content = getattr(output, "content", output)
                yield _sse(
                    "tool_end",
                    {"name": event.get("name", ""), "output": str(content)[:2000]},
                )

            elif kind == "on_chain_end":
                # 顶层链结束时拿到完整消息列表，用于持久化
                data_out = event["data"].get("output")
                if isinstance(data_out, dict) and "messages" in data_out:
                    final_messages = data_out["messages"]

        # 持久化：把窗口外的旧消息拼回 Agent 返回的窗口内消息，保存完整历史
        if final_messages:
            save_session(session_id, dropped + list(final_messages))
        else:
            history.append(AIMessage(content=final_text))
            save_session(session_id, dropped + history)

        # 汇总本轮 token 用量（一轮可能含多次模型调用，累加所有 AIMessage 的 usage）
        usage = _collect_usage(final_messages)
        if usage:
            yield _sse("usage", usage)

        # 首轮对话且尚无标题时，据内容自动提炼一个会话标题
        if is_first_turn and not get_title(session_id) and final_text.strip():
            try:
                title = await generate_session_title(message, final_text)
                if title:
                    set_title(session_id, title)
                    yield _sse("title", {"session_id": session_id, "title": title})
            except Exception:  # noqa: BLE001 —— 命名失败不影响对话主流程
                pass

        yield _sse("final", {"text": final_text})
        yield _sse("done", {})

    except Exception as exc:  # noqa: BLE001
        yield _sse("error", {"message": str(exc)})
        yield _sse("done", {})


def _collect_usage(messages: list[Any]) -> dict[str, int]:
    """累加消息列表中所有 AIMessage 的 token 用量。无数据时返回空 dict。"""
    input_t = output_t = total_t = 0
    found = False
    for m in messages:
        meta = getattr(m, "usage_metadata", None)
        if not meta:
            continue
        found = True
        input_t += int(meta.get("input_tokens", 0) or 0)
        output_t += int(meta.get("output_tokens", 0) or 0)
        total_t += int(meta.get("total_tokens", 0) or 0)
    if not found:
        return {}
    # 个别后端只给 input/output，total 缺失时兜底相加
    if total_t == 0:
        total_t = input_t + output_t
    return {"input_tokens": input_t, "output_tokens": output_t, "total_tokens": total_t}
