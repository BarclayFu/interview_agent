"use client";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

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
      <main style={{ padding: 40 }}>
        <h1>报告不存在</h1>
      </main>
    );
  if (pending)
    return (
      <main style={{ padding: 40 }}>
        <h1>报告生成中…</h1>
        <p>通常 1-2 分钟，页面会自动刷新。</p>
      </main>
    );
  if (!report) return null;

  return (
    <main style={{ fontFamily: "system-ui", padding: 40, maxWidth: 760 }}>
      <h1>{report.headline}</h1>
      <p>
        总分：<b>{report.total_score} / 5</b>
      </p>
      <h2>维度评分</h2>
      <ul>
        {report.dimensions.map((d, i) => (
          <li key={i}>
            {d.name}：{d.score}/5 — {d.comment}
          </li>
        ))}
      </ul>
      <h2>Top 亮点</h2>
      <ul>
        {report.highlights.map((h, i) => (
          <li key={i}>
            {h.text}
            <blockquote>「{h.evidence}」</blockquote>
          </li>
        ))}
      </ul>
      <h2>Top 致命伤</h2>
      <ul>
        {report.issues.map((h, i) => (
          <li key={i}>
            {h.text}
            <blockquote>「{h.evidence}」</blockquote>
          </li>
        ))}
      </ul>
      <h2>逐题回顾</h2>
      {report.per_question.map((q, i) => (
        <section key={i}>
          <h3>{q.question}</h3>
          <p>你的回答：{q.answer_summary}</p>
          <p>点评：{q.comment}</p>
        </section>
      ))}
      <h2>改进清单</h2>
      <ol>
        {report.improvements.map((x, i) => (
          <li key={i}>{x}</li>
        ))}
      </ol>
      <h2>下次练习重点</h2>
      <p>{report.next_focus}</p>
      <p>
        <a href="/sessions">历史会话</a> · <a href="/upload">再来一场</a>
      </p>
    </main>
  );
}
