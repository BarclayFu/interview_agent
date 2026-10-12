"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";

type Status = { parse_status: string; parsed_projects?: { name: string }[]; parse_error?: string };

export default function UploadPage() {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<Status | null>(null);
  const [resumeId, setResumeId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function poll(id: string) {
    for (;;) {
      await new Promise((r) => setTimeout(r, 2000));
      const r = await fetch(`/api/resumes/${id}`);
      const s = (await r.json()) as Status;
      setStatus(s);
      if (s.parse_status === "done" || s.parse_status === "failed") return;
    }
  }

  async function submit(form: FormData) {
    setBusy(true);
    setError(null);
    try {
      const r = await fetch("/api/resumes", { method: "POST", body: form });
      if (!r.ok) throw new Error(await r.text());
      const { resume_id } = (await r.json()) as { resume_id: string };
      setResumeId(resume_id);
      await poll(resume_id);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function startInterview() {
    if (!resumeId) return;
    const r = await fetch("/api/sessions", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ resume_id: resumeId }),
    });
    if (!r.ok) {
      setError(await r.text());
      return;
    }
    const { session_id } = (await r.json()) as { session_id: string };
    router.push(`/interview/${session_id}`);
  }

  return (
    <main style={{ fontFamily: "system-ui", padding: 40, maxWidth: 720 }}>
      <h1>上传简历</h1>
      <form action={submit}>
        <p>
          <input type="file" name="file" accept="application/pdf" />
        </p>
        <p>或粘贴文本（解析失败兜底）：</p>
        <textarea
          name="text"
          rows={8}
          style={{ width: "100%" }}
          placeholder="粘贴简历纯文本（≥50 字）"
        />
        <p>
          <button disabled={busy}>{busy ? "上传中…" : "上传并解析"}</button>
        </p>
      </form>
      {error && <p style={{ color: "crimson" }}>{error}</p>}
      {status && (
        <section>
          <p>
            状态：{status.parse_status}
            {status.parse_error ? `（${status.parse_error}）` : ""}
          </p>
          {status.parsed_projects && (
            <ul>
              {status.parsed_projects.map((p, i) => (
                <li key={i}>{p.name}</li>
              ))}
            </ul>
          )}
          {status.parse_status === "done" && (
            <button onClick={startInterview}>开始项目深挖面试 →</button>
          )}
        </section>
      )}
      <p>
        <a href="/sessions">历史会话</a>
      </p>
    </main>
  );
}
