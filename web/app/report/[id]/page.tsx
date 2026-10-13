"use client";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { card } from "@/components/ui";

interface Report {
  headline: string;
  total_score: number;
  dimensions: { name: string; score: number; comment: string }[];
  per_question: { question: string; answer_summary: string; comment: string }[];
  highlights: { text: string; evidence: string }[];
  issues: { text: string; evidence: string }[];
  improvements: string[];
  next_focus: string;
}

function scoreColor(s: number) {
  if (s >= 4) return "bg-emerald-500";
  if (s >= 3) return "bg-amber-500";
  return "bg-rose-500";
}

export default function ReportPage() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<Report | null>(null);
  const [pending, setPending] = useState(true);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    const timer = setInterval(async () => {
      const r = await fetch(`/api/sessions/${id}/report`);
      if (r.status === 404) {
        setMissing(true);
        setPending(false);
        clearInterval(timer);
        return;
      }
      if (r.status === 200) {
        const body = (await r.json()) as { report: Report };
        setReport(body.report);
        setPending(false);
        clearInterval(timer);
      }
    }, 3000);
    return () => clearInterval(timer);
  }, [id]);

  if (missing)
    return (
      <main className="mx-auto max-w-3xl px-4 py-24 text-center text-slate-500">
        报告不存在
      </main>
    );

  if (pending)
    return (
      <main className="mx-auto flex max-w-3xl flex-col items-center px-4 py-24">
        <span className="h-8 w-8 animate-spin rounded-full border-2 border-slate-200 border-t-indigo-600" />
        <p className="mt-4 font-medium">报告生成中…</p>
        <p className="mt-1 text-sm text-slate-500">深度评估约需 1-2 分钟，页面会自动刷新</p>
      </main>
    );

  if (!report) return null;

  return (
    <main className="mx-auto max-w-3xl space-y-5 px-4 py-10">
      <section className={card}>
        <h1 className="text-lg leading-relaxed font-semibold">{report.headline}</h1>
        <div className="mt-4 flex items-end gap-2">
          <span className="text-4xl font-bold text-indigo-600">{report.total_score}</span>
          <span className="pb-1 text-sm text-slate-400">/ 5 总分</span>
        </div>
      </section>

      <section className={card}>
        <h2 className="text-sm font-semibold text-slate-500">维度评分</h2>
        <ul className="mt-4 space-y-4">
          {report.dimensions.map((d, i) => (
            <li key={i}>
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">{d.name}</span>
                <span className="text-slate-500">{d.score} / 5</span>
              </div>
              <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100">
                <div
                  className={`h-full rounded-full ${scoreColor(d.score)}`}
                  style={{ width: `${(d.score / 5) * 100}%` }}
                />
              </div>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-500">{d.comment}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="grid gap-5 sm:grid-cols-2">
        <div className={`${card} border-emerald-100`}>
          <h2 className="text-sm font-semibold text-emerald-700">Top 亮点</h2>
          <ul className="mt-3 space-y-4">
            {report.highlights.map((h, i) => (
              <li key={i} className="text-sm">
                <p className="leading-relaxed">{h.text}</p>
                <blockquote className="mt-2 border-l-2 border-emerald-300 pl-3 text-slate-500 italic">
                  「{h.evidence}」
                </blockquote>
              </li>
            ))}
          </ul>
        </div>
        <div className={`${card} border-rose-100`}>
          <h2 className="text-sm font-semibold text-rose-700">Top 致命伤</h2>
          <ul className="mt-3 space-y-4">
            {report.issues.map((h, i) => (
              <li key={i} className="text-sm">
                <p className="leading-relaxed">{h.text}</p>
                <blockquote className="mt-2 border-l-2 border-rose-300 pl-3 text-slate-500 italic">
                  「{h.evidence}」
                </blockquote>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className={card}>
        <h2 className="text-sm font-semibold text-slate-500">逐题回顾</h2>
        <div className="mt-4 space-y-6">
          {report.per_question.map((q, i) => (
            <div key={i} className="border-t border-slate-100 pt-4 first:border-0 first:pt-0">
              <h3 className="text-sm font-semibold">{q.question}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-500">
                <span className="font-medium text-slate-600">你的回答：</span>
                {q.answer_summary}
              </p>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-500">
                <span className="font-medium text-slate-600">点评：</span>
                {q.comment}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section className={card}>
        <h2 className="text-sm font-semibold text-slate-500">改进清单（按优先级）</h2>
        <ol className="mt-4 space-y-3">
          {report.improvements.map((x, i) => (
            <li key={i} className="flex gap-3 text-sm leading-relaxed">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-xs font-semibold text-white">
                {i + 1}
              </span>
              <span>{x}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="rounded-2xl border border-indigo-100 bg-indigo-50/60 p-6">
        <h2 className="text-sm font-semibold text-indigo-700">下次练习重点</h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-700">{report.next_focus}</p>
      </section>

      <p className="flex justify-center gap-4 pt-2 text-sm text-slate-500">
        <a href="/sessions" className="hover:text-indigo-600">
          历史会话
        </a>
        <a href="/upload" className="hover:text-indigo-600">
          再来一场
        </a>
      </p>
    </main>
  );
}
