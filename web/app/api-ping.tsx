"use client";

import { useEffect, useState } from "react";

// 走同源代理（/api/* → API_ORIGIN），因此没有 CORS 与混合内容问题
const API_BASE = "/api";

export function ApiPing() {
  const [state, setState] = useState("探测中…");

  useEffect(() => {
    fetch(`${API_BASE}/version`, { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d) => setState(`浏览器直连成功（version=${d.version}）`))
      .catch((e) => setState(`浏览器直连失败：${e.message}`));
  }, []);

  return <p style={{ color: "#666" }}>{state}</p>;
}
