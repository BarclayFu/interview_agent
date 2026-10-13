import Link from "next/link";

import { ApiPing } from "./api-ping";

export const dynamic = "force-dynamic";

const API_ORIGIN = process.env.API_ORIGIN ?? "http://localhost:8000";

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_ORIGIN}${path}`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export default async function Home() {
  const version = await getJson<{ version: string; built_at: string }>("/version");
  const ready = await getJson<{ db: string; redis: string }>("/readyz");

  return (
    <main className="mx-auto max-w-4xl px-4 py-14">
      <section className="text-center">
        <p className="text-sm font-medium text-indigo-600">AI 模拟面试官</p>
        <h1 className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
          对着自己的简历，练一场真实的技术二面
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-slate-500">
          上传简历 → 面试官主导的项目深挖与追问链 → 带原文证据的结构化评估报告。
        </p>
      </section>

      <section className="mt-10 grid gap-4 sm:grid-cols-2">
        <Link
          href="/upload"
          className="group rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-300 hover:shadow-md"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-lg">
            🎯
          </div>
          <h2 className="mt-4 font-semibold group-hover:text-indigo-600">开始新面试</h2>
          <p className="mt-1.5 text-sm leading-relaxed text-slate-500">
            上传 PDF 简历或粘贴文本，自动抽取项目清单，开始一场项目深挖特训。
          </p>
        </Link>
        <Link
          href="/sessions"
          className="group rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:border-indigo-300 hover:shadow-md"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50 text-lg">
            📋
          </div>
          <h2 className="mt-4 font-semibold group-hover:text-indigo-600">历史会话</h2>
          <p className="mt-1.5 text-sm leading-relaxed text-slate-500">
            回看过去的面试记录与评估报告，跟踪自己的成长曲线。
          </p>
        </Link>
      </section>

      <section className="mt-10 flex flex-wrap items-center justify-center gap-2 text-xs text-slate-500">
        <span className="rounded-full bg-white px-3 py-1 ring-1 ring-slate-200">
          后端 {version?.version ?? "不可达"}
        </span>
        <span className="rounded-full bg-white px-3 py-1 ring-1 ring-slate-200">
          DB
          <span className={ready?.db === "ok" ? "text-emerald-600" : "text-rose-600"}>
            {" "}
            {ready?.db ?? "?"}
          </span>
        </span>
        <span className="rounded-full bg-white px-3 py-1 ring-1 ring-slate-200">
          Redis
          <span className={ready?.redis === "ok" ? "text-emerald-600" : "text-rose-600"}>
            {" "}
            {ready?.redis ?? "?"}
          </span>
        </span>
        <span className="rounded-full bg-white px-3 py-1 ring-1 ring-slate-200">
          <ApiPing />
        </span>
      </section>
    </main>
  );
}
