import Link from "next/link";

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
    <main style={{ fontFamily: "system-ui", padding: 40 }}>
      <h1>历史会话</h1>
      {sessions.length === 0 && <p>还没有会话记录。</p>}
      <ul>
        {sessions.map((s) => (
          <li key={s.id}>
            {new Date(s.created_at).toLocaleString()} — {s.status} —{" "}
            {s.report_status === "done" ? (
              <Link href={`/report/${s.id}`}>报告</Link>
            ) : (
              <Link href={`/interview/${s.id}`}>继续/查看</Link>
            )}
          </li>
        ))}
      </ul>
      <p>
        <Link href="/upload">+ 新面试</Link>
      </p>
    </main>
  );
}
