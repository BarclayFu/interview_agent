"use client";

import { useEffect, useState } from "react";

// 走同源代理（/api/* → API_ORIGIN），因此没有 CORS 与混合内容问题
export function ApiPing() {
  const [state, setState] = useState<{ ok: boolean | null; version: string }>({
    ok: null,
    version: "",
  });

  useEffect(() => {
    fetch("/api/version", { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d: { version: string }) => setState({ ok: true, version: d.version }))
      .catch(() => setState({ ok: false, version: "" }));
  }, []);

  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-slate-500">
      <span
        className={`h-1.5 w-1.5 rounded-full ${
          state.ok === null ? "bg-slate-300" : state.ok ? "bg-emerald-500" : "bg-rose-500"
        }`}
      />
      {state.ok === null
        ? "浏览器直连探测中…"
        : state.ok
          ? `浏览器直连正常 · ${state.version}`
          : "浏览器直连失败"}
    </span>
  );
}
