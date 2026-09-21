import type { NextConfig } from "next";

// 同源代理（BFF）：浏览器只与 Vercel 通信（HTTPS、同源），由 Vercel 服务端转发到 API。
// 因此 API 无需域名与 TLS，也没有混合内容与 CORS 问题。
const API_ORIGIN = process.env.API_ORIGIN ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${API_ORIGIN}/:path*` }];
  },
};

export default nextConfig;
