import type { Metadata } from "next";

import { Nav } from "@/components/nav";

import "./globals.css";

export const metadata: Metadata = {
  title: "Interview Agent · AI 模拟面试官",
  description: "面向中文技术面试的 AI 模拟面试官：项目深挖、证据化评估报告",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  // suppressHydrationWarning：浏览器扩展（如 Trancy）会注入 <html> 属性，属噪音非本项目 bug
  return (
    <html lang="zh-CN" suppressHydrationWarning>
      <body className="min-h-screen">
        <Nav />
        {children}
      </body>
    </html>
  );
}
