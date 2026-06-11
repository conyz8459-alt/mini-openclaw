"use client";

import { useCallback, useEffect, useState } from "react";
import { Rabbit, Plus } from "lucide-react";
import Navbar from "@/components/Navbar";
import Sidebar from "@/components/sidebar/Sidebar";
import ChatPanel from "@/components/chat/ChatPanel";
import Inspector from "@/components/editor/Inspector";
import { listSessions, deleteSession, renameSession, type SessionInfo } from "@/lib/api";

export default function Home() {
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [activeSession, setActiveSession] = useState<string | null>(null);
  const [inspectFile, setInspectFile] = useState<string | null>(null);

  const refreshSessions = useCallback(() => {
    listSessions()
      .then(setSessions)
      .catch(() => setSessions([]));
  }, []);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  const onNew = () => {
    const id = `session_${Date.now().toString(36)}`;
    setActiveSession(id);
  };

  const onDelete = async (id: string) => {
    try {
      await deleteSession(id);
    } catch {
      // 删除失败（如会话从未落盘）忽略，刷新即可
    }
    // 删的是当前会话时，回到空状态（让用户自己决定新建还是进历史）
    if (id === activeSession) {
      setActiveSession(null);
    }
    refreshSessions();
  };

  const onRename = async (id: string, newTitle: string) => {
    try {
      await renameSession(id, newTitle);
    } catch (err) {
      alert((err as Error).message);
    }
    refreshSessions();
  };

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <Navbar />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          sessions={sessions}
          activeSession={activeSession}
          onSelect={setActiveSession}
          onNew={onNew}
          onDelete={onDelete}
          onRename={onRename}
        />
        <main className="flex flex-1 overflow-hidden">
          <section className="flex flex-1 flex-col overflow-hidden">
            {activeSession ? (
              <ChatPanel
                sessionId={activeSession}
                onFileTouched={setInspectFile}
                onExchangeDone={refreshSessions}
              />
            ) : (
              <div className="flex h-full flex-col items-center justify-center text-center text-neutral-400">
                <Rabbit size={48} className="mb-4 text-klein/30" />
                <p className="mb-1 text-sm text-neutral-500">还没有打开任何会话</p>
                <p className="mb-6 text-xs">新建一个对话，或从左侧选择一条历史会话</p>
                <button
                  onClick={onNew}
                  className="flex items-center gap-2 rounded-lg bg-klein px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-klein-light"
                >
                  <Plus size={16} />
                  新建对话
                </button>
              </div>
            )}
          </section>
          <Inspector filePath={inspectFile} />
        </main>
      </div>
    </div>
  );
}
