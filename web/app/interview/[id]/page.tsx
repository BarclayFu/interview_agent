"use client";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { streamSse } from "../../../lib/sse";

interface Msg {
  role: "interviewer" | "candidate";
  content: string;
}

export default function InterviewPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [messages, setMessages] = useState<Msg[]>([]);
  const [streaming, setStreaming] = useState("");
  const [status, setStatus] = useState("准备中…");
  const [input, setInput] = useState("");
  const [awaiting, setAwaiting] = useState(false);
  const [finished, setFinished] = useState(false);
  const started = useRef(false);

  async function drive(body: unknown) {
    setAwaiting(false);
    let acc = "";
    try {
      for await (const e of streamSse(`/sessions/${id}/turns`, body)) {
        const d = e.data as Record<string, string>;
        if (e.event === "node_start") setStatus(d.message ?? "…");
        if (e.event === "token") {
          acc += d.text;
          setStreaming(acc);
        }
        if (e.event === "question" || e.event === "hint") {
          setMessages((m) => [
            ...m,
            { role: "interviewer", content: acc || d.question || d.text },
          ]);
          acc = "";
          setStreaming("");
        }
        if (e.event === "feedback")
          setStatus(`即时反馈：${d.rationale ?? ""}（${d.score ?? "?"} 分）`);
        if (e.event === "paused") setAwaiting(true);
        if (e.event === "finished") {
          setFinished(true);
          setStatus("面试结束，报告生成中…");
        }
        if (e.event === "error") setStatus(`错误：${d.message}`);
      }
    } catch (err) {
      setStatus(`连接中断：${err}`);
    }
  }

  useEffect(() => {
    if (!started.current) {
      started.current = true;
      void drive({ action: "start" });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function send() {
    if (!input.trim()) return;
    setMessages((m) => [...m, { role: "candidate", content: input }]);
    const text = input;
    setInput("");
    void drive({ action: "answer", text });
  }

  return (
    <main style={{ fontFamily: "system-ui", padding: 40, maxWidth: 760 }}>
      <h1>项目深挖面试</h1>
      <p style={{ color: "#666" }}>{status}</p>
      <section style={{ minHeight: 300 }}>
        {messages.map((m, i) => (
          <p key={i} style={{ textAlign: m.role === "candidate" ? "right" : "left" }}>
            <b>{m.role === "candidate" ? "你" : "面试官"}：</b>
            {m.content}
          </p>
        ))}
        {streaming && (
          <p>
            <b>面试官：</b>
            {streaming}▌
          </p>
        )}
      </section>
      {finished ? (
        <button onClick={() => router.push(`/report/${id}`)}>查看评估报告 →</button>
      ) : (
        <>
          <textarea
            rows={4}
            style={{ width: "100%" }}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={awaiting ? "输入你的回答…" : "等待面试官…"}
            disabled={!awaiting}
          />
          <p>
            <button onClick={send} disabled={!awaiting || !input.trim()}>
              回答
            </button>{" "}
            <button onClick={() => void drive({ action: "hint" })} disabled={!awaiting}>
              要提示
            </button>{" "}
            <button onClick={() => void drive({ action: "pause" })}>暂停</button>{" "}
            <button onClick={() => void drive({ action: "end" })}>结束面试</button>
          </p>
        </>
      )}
      <p>
        <a href="/sessions">历史会话</a>
      </p>
    </main>
  );
}
