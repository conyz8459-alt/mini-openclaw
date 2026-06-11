"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Loader2, Paperclip, X, FileText } from "lucide-react";
import { streamChat, getSession, uploadTemp } from "@/lib/api";
import type { ChatMessage, ToolStep } from "./types";
import MessageBubble from "./MessageBubble";

interface ChatPanelProps {
  sessionId: string;
  onFileTouched?: (path: string) => void;
  onExchangeDone?: () => void;
}

interface Attachment {
  filename: string;
  path: string;
}

export default function ChatPanel({ sessionId, onFileTouched, onExchangeDone }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [attachment, setAttachment] = useState<Attachment | null>(null);
  const [uploading, setUploading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<(() => void) | null>(null);

  // 切换会话时：回放该会话的历史文字对话
  useEffect(() => {
    let cancelled = false;
    setMessages([]);
    setAttachment(null);
    getSession(sessionId)
      .then((history) => {
        if (cancelled) return;
        setMessages(history.map((m) => ({ role: m.role, content: m.content })));
      })
      .catch(() => {
        if (!cancelled) setMessages([]);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const onPickFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const res = await uploadTemp(file);
      setAttachment(res);
    } catch {
      // 静默失败，用户可重试
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const send = () => {
    const text = input.trim();
    if ((!text && !attachment) || busy) return;

    // 用户气泡显示原文（带附件提示）；发给后端的消息附上文件路径让 Agent 读
    const displayText = attachment
      ? `${text}\n\n📎 已附文件：${attachment.filename}`
      : text;
    const backendText = attachment
      ? `${text}\n\n[用户上传了一个临时文件，路径为 "${attachment.path}"。如果需要，请用 read_file 工具读取它来协助回答。]`
      : text;

    setInput("");
    setAttachment(null);
    setBusy(true);

    setMessages((prev) => [
      ...prev,
      { role: "user", content: displayText },
      { role: "assistant", content: "", toolSteps: [], streaming: true },
    ]);

    const updateAssistant = (fn: (m: ChatMessage) => ChatMessage) => {
      setMessages((prev) => {
        const next = [...prev];
        for (let i = next.length - 1; i >= 0; i--) {
          if (next[i].role === "assistant") {
            next[i] = fn(next[i]);
            break;
          }
        }
        return next;
      });
    };

    abortRef.current = streamChat(backendText, sessionId, (ev) => {
      switch (ev.type) {
        case "token":
          updateAssistant((m) => ({ ...m, content: m.content + ev.text }));
          break;
        case "tool_start": {
          const step: ToolStep = { name: ev.name, input: ev.input };
          updateAssistant((m) => ({ ...m, toolSteps: [...(m.toolSteps ?? []), step] }));
          const p = ev.input?.file_path ?? ev.input?.path;
          if (ev.name === "read_file" && typeof p === "string") {
            onFileTouched?.(p);
          }
          break;
        }
        case "tool_end":
          updateAssistant((m) => {
            const steps = [...(m.toolSteps ?? [])];
            for (let i = steps.length - 1; i >= 0; i--) {
              if (steps[i].name === ev.name && steps[i].output === undefined) {
                steps[i] = { ...steps[i], output: ev.output };
                break;
              }
            }
            return { ...m, toolSteps: steps };
          });
          break;
        case "usage":
          updateAssistant((m) => ({
            ...m,
            usage: {
              inputTokens: ev.inputTokens,
              outputTokens: ev.outputTokens,
              totalTokens: ev.totalTokens,
            },
          }));
          break;
        case "title":
          // 标题已在后端落盘，done 事件触发的 onExchangeDone 会刷新侧栏拿到它
          break;
        case "final":
          updateAssistant((m) => ({ ...m, content: ev.text || m.content, streaming: false }));
          break;
        case "error":
          updateAssistant((m) => ({
            ...m,
            content: (m.content ? m.content + "\n\n" : "") + `⚠️ 出错：${ev.message}`,
            streaming: false,
          }));
          break;
        case "done":
          setBusy(false);
          abortRef.current = null;
          onExchangeDone?.();
          break;
      }
    });
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-6 py-5">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center text-neutral-400">
            <div className="mb-3 h-12 w-12 rounded-2xl bg-klein/10" />
            <p className="text-sm">开始和 mini OpenClaw 对话</p>
            <p className="mt-1 text-xs">试试：「查询北京天气」或「帮我算算今天运势」</p>
          </div>
        ) : (
          messages.map((m, i) => <MessageBubble key={i} msg={m} />)
        )}
      </div>

      <div className="border-t border-black/5 p-4">
        {attachment && (
          <div className="mb-2 flex items-center gap-1.5 rounded-lg bg-klein-soft px-2.5 py-1.5 text-xs text-klein">
            <FileText size={13} />
            <span className="truncate">{attachment.filename}</span>
            <button onClick={() => setAttachment(null)} className="ml-auto hover:text-klein-light">
              <X size={13} />
            </button>
          </div>
        )}
        <div className="glass flex items-end gap-2 rounded-2xl px-3 py-2 shadow-sm">
          <input ref={fileRef} type="file" onChange={onPickFile} className="hidden" />
          <button
            onClick={() => fileRef.current?.click()}
            disabled={uploading || busy}
            title="上传临时文件（让 Agent 看一下）"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-neutral-400 transition-colors hover:bg-black/5 hover:text-klein disabled:opacity-40"
          >
            {uploading ? <Loader2 size={16} className="animate-spin" /> : <Paperclip size={16} />}
          </button>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            rows={1}
            placeholder="输入消息，Enter 发送，Shift+Enter 换行"
            className="max-h-32 flex-1 resize-none bg-transparent py-1.5 text-sm outline-none placeholder:text-neutral-400"
          />
          <button
            onClick={send}
            disabled={busy || (!input.trim() && !attachment)}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-klein text-white transition-colors hover:bg-klein-light disabled:opacity-40"
          >
            {busy ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </div>
      </div>
    </div>
  );
}
