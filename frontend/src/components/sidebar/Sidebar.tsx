"use client";

import { useEffect, useRef, useState } from "react";
import { Plus, MessageCircle, Upload, FileText, Loader2, Pencil, Trash2, Check, X } from "lucide-react";
import clsx from "clsx";
import {
  type SessionInfo,
  type KnowledgeFile,
  uploadKnowledge,
  listKnowledge,
  deleteKnowledge,
} from "@/lib/api";

interface SidebarProps {
  sessions: SessionInfo[];
  activeSession: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onRename: (id: string, newId: string) => void;
}

export default function Sidebar({
  sessions,
  activeSession,
  onSelect,
  onNew,
  onDelete,
  onRename,
}: SidebarProps) {
  const [kbFiles, setKbFiles] = useState<KnowledgeFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [msg, setMsg] = useState<string>("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draftName, setDraftName] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const refreshKb = () => {
    listKnowledge()
      .then(setKbFiles)
      .catch(() => setKbFiles([]));
  };

  const onDeleteKb = async (name: string) => {
    if (!confirm(`确定从知识库删除「${name}」？将同时移除其检索索引。`)) return;
    try {
      await deleteKnowledge(name);
      setMsg(`已删除：${name}`);
    } catch (err) {
      setMsg(`✕ ${(err as Error).message}`);
    } finally {
      refreshKb();
      setTimeout(() => setMsg(""), 3000);
    }
  };

  useEffect(() => {
    refreshKb();
  }, []);

  const onPick = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setMsg("");
    try {
      const name = await uploadKnowledge(file);
      setMsg(`已上传：${name}`);
      refreshKb();
    } catch (err) {
      setMsg(`✕ ${(err as Error).message}`);
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
      setTimeout(() => setMsg(""), 3000);
    }
  };

  return (
    <aside className="glass flex w-60 shrink-0 flex-col border-r border-black/5">
      <div className="p-3">
        <button
          onClick={onNew}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-klein px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-klein-light"
        >
          <Plus size={16} />
          新建会话
        </button>
      </div>

      <div className="px-3 pb-1 text-xs font-medium uppercase tracking-wide text-neutral-400">
        历史会话
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-3">
        {sessions.length === 0 ? (
          <div className="px-3 py-6 text-center text-xs text-neutral-400">
            暂无会话
          </div>
        ) : (
          sessions.map((s) => {
            const isActive = activeSession === s.session_id;
            const isEditing = editingId === s.session_id;

            const commitRename = () => {
              const name = draftName.trim();
              if (name && name !== s.title) onRename(s.session_id, name);
              setEditingId(null);
            };

            return (
              <div
                key={s.session_id}
                className={clsx(
                  "group mb-1 flex items-center rounded-lg px-2 py-2 transition-colors",
                  isActive ? "bg-klein-soft" : "hover:bg-black/5"
                )}
              >
                {isEditing ? (
                  <div className="flex flex-1 items-center gap-1">
                    <input
                      autoFocus
                      value={draftName}
                      onChange={(e) => setDraftName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") commitRename();
                        if (e.key === "Escape") setEditingId(null);
                      }}
                      className="min-w-0 flex-1 rounded border border-klein/40 bg-white px-1.5 py-0.5 text-sm outline-none"
                    />
                    <button onClick={commitRename} title="确认" className="shrink-0 text-klein hover:text-klein-light">
                      <Check size={14} />
                    </button>
                    <button onClick={() => setEditingId(null)} title="取消" className="shrink-0 text-neutral-400 hover:text-neutral-600">
                      <X size={14} />
                    </button>
                  </div>
                ) : (
                  <>
                    <button
                      onClick={() => onSelect(s.session_id)}
                      className="flex min-w-0 flex-1 flex-col gap-0.5 text-left"
                    >
                      <div className="flex items-center gap-1.5 text-sm font-medium text-neutral-800">
                        <MessageCircle size={13} className="shrink-0 text-klein" />
                        <span className="truncate">{s.title}</span>
                      </div>
                      {s.preview && (
                        <span className="truncate pl-5 text-xs text-neutral-400">
                          {s.preview}
                        </span>
                      )}
                    </button>
                    <div className="ml-1 flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
                      <button
                        onClick={() => {
                          setEditingId(s.session_id);
                          setDraftName(s.title);
                        }}
                        title="重命名"
                        className="rounded p-1 text-neutral-400 hover:bg-black/5 hover:text-klein"
                      >
                        <Pencil size={13} />
                      </button>
                      <button
                        onClick={() => {
                          if (confirm(`确定删除会话「${s.title}」？此操作不可撤销。`)) {
                            onDelete(s.session_id);
                          }
                        }}
                        title="删除"
                        className="rounded p-1 text-neutral-400 hover:bg-red-50 hover:text-red-500"
                      >
                        <Trash2 size={13} />
                      </button>
                    </div>
                  </>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* 知识库上传区 */}
      <div className="border-t border-black/5 p-3">
        <div className="mb-2 flex items-center justify-between text-xs font-medium uppercase tracking-wide text-neutral-400">
          <span>知识库</span>
          <span className="text-[10px] normal-case">{kbFiles.length} 个文件</span>
        </div>

        {kbFiles.length > 0 && (
          <div className="mb-2 max-h-24 space-y-0.5 overflow-y-auto">
            {kbFiles.map((f) => (
              <div
                key={f.name}
                className="group flex items-center gap-1.5 rounded px-1 py-0.5 text-xs text-neutral-500 hover:bg-black/5"
                title={f.name}
              >
                <FileText size={11} className="shrink-0 text-klein" />
                <span className="truncate">{f.name}</span>
                <button
                  onClick={() => onDeleteKb(f.name)}
                  title="从知识库删除"
                  className="ml-auto shrink-0 rounded p-0.5 text-neutral-400 opacity-0 transition-opacity hover:bg-red-50 hover:text-red-500 group-hover:opacity-100"
                >
                  <Trash2 size={11} />
                </button>
              </div>
            ))}
          </div>
        )}

        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.md,.txt"
          onChange={onPick}
          className="hidden"
        />
        <button
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-dashed border-klein/40 px-3 py-2 text-xs text-klein transition-colors hover:bg-klein-soft disabled:opacity-50"
        >
          {uploading ? (
            <Loader2 size={13} className="animate-spin" />
          ) : (
            <Upload size={13} />
          )}
          {uploading ? "上传中…" : "上传文件 (PDF/MD/TXT)"}
        </button>
        {msg && (
          <div className="mt-1.5 truncate text-center text-[11px] text-neutral-500">
            {msg}
          </div>
        )}
      </div>
    </aside>
  );
}
