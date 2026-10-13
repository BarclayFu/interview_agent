"use client";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Badge, btn, input } from "@/components/ui";
import { streamSse } from "@/lib/sse";

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
  const [input_, setInput] = useState("");
  const [awaiting, setAwaiting] = useState(false);
  const [finished, setFinished] = useState(false);
  const [questionCount, setQuestionCount] = useState(0);
  const started = useRef(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

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
          setQuestionCount((n) => n + 1);
        }
        if (e.event === "feedback") setStatus(`即时反馈：${d.rationale ?? ""}（${d.score ?? "?"} 分）`);
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
    if (!input_.trim()) return;
    setMessages((m) => [...m, { role: "candidate", content: input_ }]);
    const text = input_;
    setInput("");
    void drive({ action: "answer", text });
  }

  return (
    <main className="mx-auto flex min-h-[calc(100vh-3.5rem)] max-w-3xl flex-col px-4 py-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h1 className="text-xl font-bold tracking-tight">项目深挖面试</h1>
        <div className="flex items-center gap-2">
          {questionCount > 0 && <Badge tone="slate">第 {questionCount} 题</Badge>}
          <Badge tone={finished ? "green" : awaiting ? "indigo" : "amber"}>
            {finished ? "已结束" : awaiting ? "等待作答" : "面试官思考中"}
          </Badge>
        </div>
      </div>

      <p className="mt-2 min-h-5 text-xs text-slate-400">{status}</p>

      <section className="mt-4 flex-1 space-y-4">
        {messages.map((m, i) =>
          m.role === "candidate" ? (
            <div key={i} className="flex justify-end">
              <div className="max-w-[85%] rounded-2xl rounded-br-md bg-indigo-600 px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap text-white shadow-sm">
                {m.content}
              </div>
            </div>
          ) : (
            <div key={i} className="flex items-start gap-3">
              <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-sm font-medium text-indigo-600 ring-1 ring-indigo-100">
                面
              </span>
              <div className="max-w-[85%] rounded-2xl rounded-tl-md border border-slate-200 bg-white px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap shadow-sm">
                {m.content}
              </div>
            </div>
          ),
        )}

        {streaming && (
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-sm font-medium text-indigo-600 ring-1 ring-indigo-100">
              面
            </span>
            <div className="max-w-[85%] rounded-2xl rounded-tl-md border border-indigo-200 bg-white px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap shadow-sm">
              {streaming}
              <span className="ml-0.5 inline-block animate-blink text-indigo-500">▍</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </section>

      <section className="sticky bottom-0 mt-6 bg-slate-50 pt-3 pb-1">
        {finished ? (
          <button className={`${btn.primary} w-full`} onClick={() => router.push(`/report/${id}`)}>
            查看评估报告 →
          </button>
        ) : (
          <div className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm">
            <textarea
              rows={3}
              className={`${input} resize-none border-0 focus:ring-0`}
              value={input_}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) send();
              }}
              placeholder={awaiting ? "输入你的回答…（⌘/Ctrl + Enter 发送）" : "等待面试官…"}
              disabled={!awaiting}
            />
            <div className="mt-2 flex items-center justify-between">
              <div className="flex items-center gap-1">
                <button
                  className={btn.ghost}
                  onClick={() => void drive({ action: "hint" })}
                  disabled={!awaiting}
                >
                  要个提示
                </button>
                <button className={btn.ghost} onClick={() => void drive({ action: "pause" })}>
                  暂停
                </button>
                <button
                  className={btn.ghost}
                  onClick={() => void drive({ action: "end" })}
                  disabled={finished}
                >
                  结束面试
                </button>
              </div>
              <button className={btn.primary} onClick={send} disabled={!awaiting || !input_.trim()}>
                发送回答
              </button>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
