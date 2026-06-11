import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "mini OpenClaw",
  description: "本地运行、拥有真实记忆的 AI Agent 系统",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
