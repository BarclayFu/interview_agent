import type { NextConfig } from "next";

// 浏览器端 /api/* 由 Route Handler 代理（app/api/[...path]/route.ts，含 X-Proxy-Secret 注入），
// 不使用 rewrites：rewrites 无法注入 header。服务端渲染仍可直连 API_ORIGIN。
const nextConfig: NextConfig = {};

export default nextConfig;
