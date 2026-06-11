"use client";

import { useEffect, useState } from "react";
import Editor from "@monaco-editor/react";
import { Save, FileCode, Check, RefreshCw } from "lucide-react";
import { readFile, saveFile, listSkills, type SkillInfo } from "@/lib/api";

// 工作区固定文件（记忆/设定类）
const WORKSPACE_FILES = [
  { label: "MEMORY.md", path: "memory/MEMORY.md" },
  { label: "USER.md", path: "workspace/USER.md" },
  { label: "AGENTS.md", path: "workspace/AGENTS.md" },
  { label: "SOUL.md", path: "workspace/SOUL.md" },
];

export default function Inspector({ filePath }: { filePath: string | null }) {
  const [path, setPath] = useState<string>("memory/MEMORY.md");
  const [content, setContent] = useState<string>("");
  const [dirty, setDirty] = useState(false);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(false);
  const [skills, setSkills] = useState<SkillInfo[]>([]);

  // 动态拉取技能列表（新增技能后自动出现）
  useEffect(() => {
    listSkills()
      .then(setSkills)
      .catch(() => setSkills([]));
  }, []);

  // 外部（Agent 触碰文件）驱动切换
  useEffect(() => {
    if (filePath) setPath(filePath);
  }, [filePath]);

  // 路径变化时加载内容
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    readFile(path)
      .then((c) => {
        if (!cancelled) {
          setContent(c);
          setDirty(false);
        }
      })
      .catch(() => {
        if (!cancelled) setContent(`# 无法读取：${path}`);
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [path]);

  const onSave = async () => {
    await saveFile(path, content);
    setDirty(false);
    setSaved(true);
    setTimeout(() => setSaved(false), 1500);
  };

  const lang = path.endsWith(".json") ? "json" : "markdown";

  return (
    <aside className="glass flex w-[34%] min-w-[320px] shrink-0 flex-col border-l border-black/5">
      <div className="flex items-center justify-between border-b border-black/5 px-3 py-2">
        <div className="flex items-center gap-1.5 text-sm font-medium text-neutral-700">
          <FileCode size={15} className="text-klein" />
          检查器
        </div>
        <button
          onClick={onSave}
          disabled={!dirty}
          className="flex items-center gap-1 rounded-lg bg-klein px-2.5 py-1 text-xs font-medium text-white transition-colors hover:bg-klein-light disabled:opacity-40"
        >
          {saved ? <Check size={13} /> : <Save size={13} />}
          {saved ? "已保存" : "保存"}
        </button>
      </div>

      <div className="space-y-1.5 border-b border-black/5 px-3 py-2">
        <div className="flex flex-wrap items-center gap-1">
          <span className="mr-1 text-[10px] font-medium uppercase text-neutral-400">工作区</span>
          {WORKSPACE_FILES.map((f) => (
            <button
              key={f.path}
              onClick={() => setPath(f.path)}
              className={`rounded-md px-2 py-0.5 text-xs transition-colors ${
                path === f.path ? "bg-klein-soft text-klein" : "text-neutral-500 hover:bg-black/5"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-1">
          <span className="mr-1 text-[10px] font-medium uppercase text-neutral-400">技能</span>
          {skills.length === 0 ? (
            <span className="text-xs text-neutral-300">（无）</span>
          ) : (
            skills.map((s) => (
              <button
                key={s.location}
                onClick={() => setPath(s.location)}
                title={s.description}
                className={`rounded-md px-2 py-0.5 text-xs transition-colors ${
                  path === s.location ? "bg-klein-soft text-klein" : "text-neutral-500 hover:bg-black/5"
                }`}
              >
                {s.name}
              </button>
            ))
          )}
        </div>
      </div>

      <div className="flex items-center gap-1.5 px-3 py-1.5 font-mono text-[11px] text-neutral-400">
        {loading ? <RefreshCw size={11} className="animate-spin" /> : null}
        {path}
        {dirty && <span className="text-amber-500">●</span>}
      </div>

      <div className="flex-1 overflow-hidden">
        <Editor
          height="100%"
          language={lang}
          theme="light"
          value={content}
          onChange={(v) => {
            setContent(v ?? "");
            setDirty(true);
          }}
          options={{
            fontSize: 13,
            minimap: { enabled: false },
            wordWrap: "on",
            scrollBeyondLastLine: false,
            lineNumbers: "on",
            padding: { top: 12 },
          }}
        />
      </div>
    </aside>
  );
}
