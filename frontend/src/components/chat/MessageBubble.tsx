"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import clsx from "clsx";
import type { ChatMessage } from "./types";
import ThoughtChain from "./ThoughtChain";

export default function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";

  return (
    <div className={clsx("flex w-full", isUser ? "justify-end" : "justify-start")}>
      <div className={clsx("max-w-[80%]", isUser && "flex flex-col items-end")}>
        {/* 助手的思考链显示在气泡上方 */}
        {!isUser && msg.toolSteps && msg.toolSteps.length > 0 && (
          <ThoughtChain steps={msg.toolSteps} />
        )}

        <div
          className={clsx(
            "rounded-2xl px-4 py-2.5 text-[14px] leading-relaxed",
            isUser
              ? "bg-klein text-white"
              : "glass text-neutral-800 shadow-sm"
          )}
        >
          {isUser ? (
            <span className="whitespace-pre-wrap">{msg.content}</span>
          ) : (
            <div className={clsx("md-body", msg.streaming && !msg.content && "cursor-blink")}>
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {msg.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* 助手消息：本轮 token 用量（成本可视化） */}
        {!isUser && msg.usage && msg.usage.totalTokens > 0 && (
          <div
            className="mt-1 px-1 text-[11px] text-neutral-400"
            title={`输入 ${msg.usage.inputTokens} + 输出 ${msg.usage.outputTokens} = ${msg.usage.totalTokens} tokens（本轮）`}
          >
            {msg.usage.totalTokens.toLocaleString()} tokens
          </div>
        )}
      </div>
    </div>
  );
}
