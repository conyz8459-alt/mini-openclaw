"use client";

import { useState } from "react";
import { ChevronRight, Terminal, Code, Globe, FileText, Database, Wrench } from "lucide-react";
import clsx from "clsx";
import type { ToolStep } from "./types";

const TOOL_ICON: Record<string, typeof Terminal> = {
  terminal: Terminal,
  python_repl: Code,
  fetch_url: Globe,
  read_file: FileText,
  search_knowledge_base: Database,
};

const TOOL_LABEL: Record<string, string> = {
  terminal: "命令行",
  python_repl: "Python",
  fetch_url: "网络获取",
  read_file: "读取文件",
  search_knowledge_base: "知识检索",
};

export default function ThoughtChain({ steps }: { steps: ToolStep[] }) {
  const [open, setOpen] = useState(false);
  if (steps.length === 0) return null;

  return (
    <div className="mb-2 overflow-hidden rounded-xl border border-black/5 bg-white/50">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs text-neutral-500 transition-colors hover:bg-black/[0.03]"
      >
        <ChevronRight
          size={14}
          className={clsx("transition-transform", open && "rotate-90")}
        />
        <Wrench size={13} className="text-klein" />
        <span className="font-medium">
          思考链 · 调用了 {steps.length} 个工具
        </span>
        <span className="ml-1 flex gap-1">
          {steps.map((s, i) => {
            const Icon = TOOL_ICON[s.name] ?? Wrench;
            return <Icon key={i} size={12} className="text-neutral-400" />;
          })}
        </span>
      </button>

      {open && (
        <div className="space-y-2 border-t border-black/5 px-3 py-2">
          {steps.map((step, i) => {
            const Icon = TOOL_ICON[step.name] ?? Wrench;
            return (
              <div key={i} className="text-xs">
                <div className="flex items-center gap-1.5 font-medium text-neutral-700">
                  <Icon size={13} className="text-klein" />
                  {TOOL_LABEL[step.name] ?? step.name}
                  <span className="font-mono text-[11px] text-neutral-400">
                    {step.name}
                  </span>
                </div>
                <pre className="mt-1 overflow-x-auto rounded-md bg-black/[0.03] px-2 py-1.5 text-[11px] text-neutral-600">
                  入参: {JSON.stringify(step.input, null, 0)}
                </pre>
                {step.output !== undefined && (
                  <pre className="mt-1 max-h-32 overflow-y-auto rounded-md bg-black/[0.03] px-2 py-1.5 text-[11px] text-neutral-600">
                    结果: {step.output.slice(0, 800)}
                    {step.output.length > 800 ? " …" : ""}
                  </pre>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
