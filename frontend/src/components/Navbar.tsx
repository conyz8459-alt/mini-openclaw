"use client";

import { Rabbit } from "lucide-react";

export default function Navbar() {
  return (
    <header className="glass-strong sticky top-0 z-20 flex h-14 items-center justify-between border-b border-black/5 px-5">
      <div className="flex items-center gap-2">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-klein text-white">
          <Rabbit size={17} />
        </div>
        <span className="text-[15px] font-semibold tracking-tight">mini OpenClaw</span>
      </div>
    </header>
  );
}
