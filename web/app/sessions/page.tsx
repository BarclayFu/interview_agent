import Link from "next/link";

import { Badge, card, statusTone } from "@/components/ui";

export const dynamic = "force-dynamic";

async function listSessions() {
  const origin = process.env.API_ORIGIN ?? "http://localhost:8000";
  const secret = process.env.PROXY_SECRET ?? "";
  try {
    const r = await fetch(`${origin}/sessions`, {
      headers: secret ? { "X-Proxy-Secret": secret } : {},
      cache: "no-store",
    });
    if (!r.ok) return [];
    return (await r.json()) as {
      id: string;
      status: string;
      created_at: string;
      report_status: string | null;
    }[];
  } catch {
    return [];
  }
}

export default async function SessionsPage() {
  const sessions = await listSessions();
  return (
    <main className="mx-auto max-w-3xl px-4 py-10">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold tracking-tight">历史会话</h1>
        <Link
          href="/upload"
          className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-500"
        >
          + 新面试
        </Link>
      </div>

      {sessions.length === 0 ? (
        <p className={`${card} mt-6 text-center text-sm text-slate-500`}>
          还没有会话记录，去上传一份简历开始第一场吧。
        </p>
      ) : (
        <ul className="mt-6 space-y-3">
          {sessions.map((s) => (
            <li
              key={s.id}
              className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm"
            >
              <div>
                <p className="text-sm font-medium">
                  {new Date(s.created_at).toLocaleString("zh-CN", { hour12: false })}
                </p>
                <p className="mt-0.5 font-mono text-xs text-slate-400">{s.id.slice(0, 8)}</p>
              </div>
              <div className="flex items-center gap-3">
                <Badge tone={statusTone(s.status)}>{s.status}</Badge>
                {s.report_status === "done" ? (
                  <Link
                    href={`/report/${s.id}`}
                    className="text-sm font-medium text-indigo-600 hover:text-indigo-500"
                  >
                    查看报告 →
                  </Link>
                ) : (
                  <Link
                    href={`/interview/${s.id}`}
                    className="text-sm font-medium text-slate-500 hover:text-indigo-600"
                  >
                    继续 →
                  </Link>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
