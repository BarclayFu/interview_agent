// 同源代理（BFF）：浏览器只与 Vercel/Next 通信；服务端转发到 API 并注入 X-Proxy-Secret。
// 用 Route Handler 而非 rewrites：rewrites 无法注入 header，且 SSE 需要流式透传。
import { NextRequest } from "next/server";

const API_ORIGIN = process.env.API_ORIGIN ?? "http://localhost:8000";
const PROXY_SECRET = process.env.PROXY_SECRET ?? "";

async function proxy(req: NextRequest, { params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const url = `${API_ORIGIN}/${path.join("/")}${req.nextUrl.search}`;
  const headers = new Headers(req.headers);
  headers.delete("host");
  if (PROXY_SECRET) headers.set("X-Proxy-Secret", PROXY_SECRET);

  const upstream = await fetch(url, {
    method: req.method,
    headers,
    body: req.method === "GET" || req.method === "HEAD" ? undefined : await req.arrayBuffer(),
    cache: "no-store",
  });

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "content-type": upstream.headers.get("content-type") ?? "application/json",
      "cache-control": "no-store",
      "x-accel-buffering": "no", // 防中间层缓冲 SSE
    },
  });
}

export { proxy as GET, proxy as POST };
export const dynamic = "force-dynamic";
