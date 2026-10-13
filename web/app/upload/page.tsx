"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Badge, btn, card, input, statusTone } from "@/components/ui";

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
    <main className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="text-2xl font-bold tracking-tight">上传简历</h1>
      <p className="mt-1.5 text-sm text-slate-500">
        支持文字型 PDF 或直接粘贴文本；解析抽取约需 10-30 秒。
      </p>

      <form action={submit} className={`${card} mt-6 space-y-5`}>
        <div>
          <label htmlFor="resume-file" className="text-sm font-medium">
            上传 PDF
          </label>
          <input
            id="resume-file"
            type="file"
            name="file"
            accept="application/pdf"
            className="mt-2 block w-full cursor-pointer rounded-xl border border-dashed border-slate-300 px-3 py-2.5 text-sm text-slate-500 transition hover:border-indigo-300 file:mr-3 file:rounded-lg file:border-0 file:bg-indigo-50 file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-indigo-700 hover:file:bg-indigo-100"
          />
        </div>

        <div className="flex items-center gap-3 text-xs text-slate-400">
          <span className="h-px flex-1 bg-slate-200" />
          或
          <span className="h-px flex-1 bg-slate-200" />
        </div>

        <div>
          <label htmlFor="resume-text" className="text-sm font-medium">
            粘贴简历文本
          </label>
          <textarea
            id="resume-text"
            name="text"
            rows={8}
            className={`${input} mt-2`}
            placeholder="粘贴简历纯文本（≥50 字），PDF 解析失败时的兜底入口"
          />
        </div>

        <button className={`${btn.primary} w-full`} disabled={busy}>
          {busy ? "上传解析中…" : "上传并解析"}
        </button>
      </form>

      {error && (
        <p className="mt-4 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700 ring-1 ring-rose-100">
          {error}
        </p>
      )}

      {status && (
        <section className={`${card} mt-5`}>
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">解析状态</span>
            <Badge tone={statusTone(status.parse_status)}>{status.parse_status}</Badge>
          </div>

          {status.parse_error && (
            <p className="mt-3 text-sm text-rose-600">{status.parse_error}</p>
          )}

          {status.parsed_projects && status.parsed_projects.length > 0 && (
            <ul className="mt-4 space-y-2">
              {status.parsed_projects.map((p, i) => (
                <li
                  key={i}
                  className="flex items-center gap-3 rounded-xl bg-slate-50 px-4 py-3 text-sm"
                >
                  <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-white text-xs font-medium text-indigo-600 ring-1 ring-slate-200">
                    {i + 1}
                  </span>
                  <span className="font-medium text-slate-800">{p.name}</span>
                </li>
              ))}
            </ul>
          )}

          {status.parse_status === "done" && (
            <button className={`${btn.primary} mt-5 w-full`} onClick={startInterview}>
              开始项目深挖面试 →
            </button>
          )}
        </section>
      )}
    </main>
  );
}
