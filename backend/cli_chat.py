"""命令行对话测试入口（无需前端，验证 Agent + Skills + 记忆闭环）。

用法：
    cd backend
    python cli_chat.py

需先配置 backend/.env（参考 .env.example）。
"""
from __future__ import annotations

import asyncio
import json

from chat_service import stream_chat


async def _chat_once(message: str, session_id: str) -> None:
    async for sse in stream_chat(message, session_id):
        # 解析 SSE：event: xxx \n data: {...}
        lines = sse.strip().splitlines()
        if len(lines) < 2:
            continue
        event = lines[0].removeprefix("event: ").strip()
        data = json.loads(lines[1].removeprefix("data: ").strip())

        if event == "token":
            print(data["text"], end="", flush=True)
        elif event == "tool_start":
            print(f"\n  🔧 [调用工具] {data['name']}  入参={data['input']}", flush=True)
        elif event == "tool_end":
            preview = data["output"][:200].replace("\n", " ")
            print(f"  📤 [工具结果] {preview}", flush=True)
        elif event == "error":
            print(f"\n  ❌ 错误：{data['message']}", flush=True)
        elif event == "final":
            print()  # 收尾换行


async def main() -> None:
    session_id = "cli_session"
    print("Mini-OpenClaw CLI —— 输入消息开始对话，输入 exit 退出。\n")
    while True:
        try:
            msg = input("你 > ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if msg.lower() in {"exit", "quit", "q"}:
            break
        if not msg:
            continue
        print("Agent > ", end="", flush=True)
        await _chat_once(msg, session_id)
        print()


if __name__ == "__main__":
    asyncio.run(main())
