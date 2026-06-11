// 后端 API 封装（端口 8002）。包含普通请求与 SSE 流式对话。

export const API_BASE = "http://localhost:8002";

export interface SessionInfo {
  session_id: string;
  title: string;
  message_count: number;
  preview: string;
}

// SSE 事件类型，对应后端 chat_service.py 的事件
export type ChatEvent =
  | { type: "token"; text: string }
  | { type: "tool_start"; name: string; input: Record<string, unknown> }
  | { type: "tool_end"; name: string; output: string }
  | { type: "usage"; inputTokens: number; outputTokens: number; totalTokens: number }
  | { type: "title"; sessionId: string; title: string }
  | { type: "final"; text: string }
  | { type: "error"; message: string }
  | { type: "done" };

// 读取文件内容
export async function readFile(path: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/files?path=${encodeURIComponent(path)}`);
  if (!res.ok) throw new Error(`读取失败：${path}`);
  const data = await res.json();
  return data.content as string;
}

// 保存文件内容
export async function saveFile(path: string, content: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/files`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path, content }),
  });
  if (!res.ok) throw new Error(`保存失败：${path}`);
}

// 获取历史会话列表
export async function listSessions(): Promise<SessionInfo[]> {
  const res = await fetch(`${API_BASE}/api/sessions`);
  if (!res.ok) throw new Error("获取会话列表失败");
  const data = await res.json();
  return data.sessions as SessionInfo[];
}

// 删除会话
export async function deleteSession(sessionId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/sessions/${encodeURIComponent(sessionId)}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail ?? "删除会话失败");
  }
}

// 重命名会话（修改显示标题，session_id 不变），返回生效的标题
export async function renameSession(sessionId: string, newTitle: string): Promise<string> {
  const res = await fetch(`${API_BASE}/api/sessions/${encodeURIComponent(sessionId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ new_id: newTitle }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail ?? "重命名失败");
  }
  const data = await res.json();
  return data.title as string;
}

export interface KnowledgeFile {
  name: string;
  size: number;
}

// 上传文件到知识库（RAG）
export async function uploadKnowledge(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/upload`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail ?? "上传失败");
  }
  const data = await res.json();
  return data.filename as string;
}

// 列出知识库文件
export async function listKnowledge(): Promise<KnowledgeFile[]> {
  const res = await fetch(`${API_BASE}/api/knowledge`);
  if (!res.ok) throw new Error("获取知识库列表失败");
  const data = await res.json();
  return data.files as KnowledgeFile[];
}

// 删除知识库文件（同步移除其索引节点）
export async function deleteKnowledge(filename: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/knowledge/${encodeURIComponent(filename)}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail ?? "删除失败");
  }
}

export interface SkillInfo {
  name: string;
  description: string;
  location: string;
}

// 列出所有技能（供检查器动态显示）
export async function listSkills(): Promise<SkillInfo[]> {
  const res = await fetch(`${API_BASE}/api/skills`);
  if (!res.ok) throw new Error("获取技能列表失败");
  const data = await res.json();
  return data.skills as SkillInfo[];
}

// 读取单个会话的消息（历史回放）
export interface ReplayMessage {
  role: "user" | "assistant";
  content: string;
}

export async function getSession(sessionId: string): Promise<ReplayMessage[]> {
  const res = await fetch(`${API_BASE}/api/sessions/${encodeURIComponent(sessionId)}`);
  if (!res.ok) throw new Error("读取会话失败");
  const data = await res.json();
  return data.messages as ReplayMessage[];
}

// 上传临时文件（不进知识库，供 Agent 用 read_file 读取）
export async function uploadTemp(file: File): Promise<{ filename: string; path: string }> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/upload/temp`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail ?? "上传失败");
  }
  const data = await res.json();
  return { filename: data.filename as string, path: data.path as string };
}

// 流式对话：逐事件回调。返回一个可中止的函数。
export function streamChat(
  message: string,
  sessionId: string,
  onEvent: (ev: ChatEvent) => void
): () => void {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, session_id: sessionId, stream: true }),
        signal: controller.signal,
      });
      if (!res.body) throw new Error("无响应流");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // SSE 以空行分隔事件块
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() ?? "";
        for (const block of blocks) {
          const ev = parseSSEBlock(block);
          if (ev) onEvent(ev);
        }
      }
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        onEvent({ type: "error", message: (err as Error).message });
        onEvent({ type: "done" });
      }
    }
  })();

  return () => controller.abort();
}

function parseSSEBlock(block: string): ChatEvent | null {
  const lines = block.split("\n");
  let event = "";
  let dataStr = "";
  for (const line of lines) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataStr += line.slice(5).trim();
  }
  if (!event) return null;
  let data: Record<string, unknown> = {};
  if (dataStr) {
    try {
      data = JSON.parse(dataStr);
    } catch {
      data = {};
    }
  }
  switch (event) {
    case "token":
      return { type: "token", text: String(data.text ?? "") };
    case "tool_start":
      return {
        type: "tool_start",
        name: String(data.name ?? ""),
        input: (data.input as Record<string, unknown>) ?? {},
      };
    case "tool_end":
      return { type: "tool_end", name: String(data.name ?? ""), output: String(data.output ?? "") };
    case "usage":
      return {
        type: "usage",
        inputTokens: Number(data.input_tokens ?? 0),
        outputTokens: Number(data.output_tokens ?? 0),
        totalTokens: Number(data.total_tokens ?? 0),
      };
    case "title":
      return {
        type: "title",
        sessionId: String(data.session_id ?? ""),
        title: String(data.title ?? ""),
      };
    case "final":
      return { type: "final", text: String(data.text ?? "") };
    case "error":
      return { type: "error", message: String(data.message ?? "未知错误") };
    case "done":
      return { type: "done" };
    default:
      return null;
  }
}
