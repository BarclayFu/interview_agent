"use client";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { Badge, btn, input } from "@/components/ui";
import { streamSse } from "@/lib/sse";
import type { Decision, DebugResponse, UsageResponse } from "@/lib/types";

interface Msg {
  role: "interviewer" | "candidate";
  content: string;
}

interface LiveState {
  phase: string;
  question_count: number;
  followup_depth: number;
  current_project_idx: number;
  hint_count: number;
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
  const started = useRef(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  // ---- 开发者观测 ----
  const [devOpen, setDevOpen] = useState(false);
  const [live, setLive] = useState<LiveState | null>(null);
  const [decisions, setDecisions] = useState<Decision[]>([]);
  const [usage, setUsage] = useState<UsageResponse | null>(null);
  const [debug, setDebug] = useState<DebugResponse | null>(null);

  async function refreshObs() {
    try {
      const [u, g] = await Promise.all([
        fetch(`/api/sessions/${id}/usage`).then((r) => r.json()),
        fetch(`/api/sessions/${id}/debug`).then((r) => r.json()),
      ]);
      setUsage(u as UsageResponse);
      setDebug(g as DebugResponse);
    } catch {
      /* 观测失败不影响面试 */
    }
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  async function drive(body: unknown) {
    setAwaiting(false);
    let acc = "";
    try {
      for await (const e of streamSse(`/sessions/${id}/turns`, body)) {
        const d = e.data as Record<string, unknown>;
        if (e.event === "node_start") setStatus(String(d.message ?? "…"));
        if (e.event === "token") {
          acc += String(d.text ?? "");
          setStreaming(acc);
        }
        if (e.event === "question" || e.event === "hint") {
          setMessages((m) => [
            ...m,
            { role: "interviewer", content: acc || String(d.question ?? d.text ?? "") },
          ]);
          acc = "";
          setStreaming("");
        }
        if (e.event === "feedback") {
          setStatus(`即时反馈：${d.rationale ?? ""}（${d.score ?? "?"} 分）`);
          setDecisions((prev) => [...prev, d as unknown as Decision]);
        }
        if (e.event === "state") setLive(d as unknown as LiveState);
        if (e.event === "paused") setAwaiting(true);
        if (e.event === "finished") {
          setFinished(true);
          setStatus("面试结束，报告生成中…");
        }
        if (e.event === "error") setStatus(`错误：${String(d.message)}`);
        if (e.event === "done") void refreshObs();
      }
    } catch (err) {
      const msg = String(err);
      if (msg.includes("409")) {
        setStatus("会话已开始，正在恢复状态…");
        void bootstrap(true);
      } else {
        setStatus(`连接中断：${msg}`);
      }
    }
  }

  async function bootstrap(fromConflict = false) {
    // 刷新/恢复场景：会话可能已开始——先水合已有状态，不盲目再 start（会 409）
    try {
      const [sr, gr] = await Promise.all([
        fetch(`/api/sessions/${id}`),
        fetch(`/api/sessions/${id}/debug`),
      ]);
      if (sr.ok) {
        const s = (await sr.json()) as {
          status: string;
          phase: string;
          question_count: number;
          messages: Msg[];
        };
        if (s.messages.length > 0) {
          setMessages(s.messages);
          if (gr.ok) {
            const g = (await gr.json()) as DebugResponse;
            setDebug(g);
            setLive({
              phase: g.state.phase ?? s.phase,
              question_count: g.state.question_count,
              followup_depth: g.state.followup_depth,
              current_project_idx: g.state.current_project_idx,
              hint_count: g.state.hint_count,
            });
          }
          if (s.status === "finished") {
            setFinished(true);
            setStatus("面试已结束");
          } else {
            setAwaiting(true);
            setStatus("已恢复会话，等待你的回答");
          }
          void refreshObs();
          return;
        }
      }
    } catch {
      /* 网络异常：落回 start 流程 */
    }
    if (fromConflict) {
      setStatus("会话已开始但读不到状态，请刷新页面");
      return;
    }
    void drive({ action: "start" });
  }

  useEffect(() => {
    if (!started.current) {
      started.current = true;
      void bootstrap();
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
          {live && <Badge tone="slate">第 {live.question_count} 题</Badge>}
          <Badge tone={finished ? "green" : awaiting ? "indigo" : "amber"}>
            {finished ? "已结束" : awaiting ? "等待作答" : "面试官思考中"}
          </Badge>
          <button
            className={btn.ghost}
            onClick={() => {
              setDevOpen((v) => !v);
              if (!devOpen) void refreshObs();
            }}
          >
            观测 {devOpen ? "▴" : "▾"}
          </button>
        </div>
      </div>

      <p className="mt-2 min-h-5 text-xs text-slate-400">{status}</p>

      {devOpen && (
        <section className="mt-3 space-y-4 rounded-2xl border border-slate-200 bg-white p-4 text-xs shadow-sm">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-slate-500">状态机</span>
            {live ? (
              <>
                <Badge tone="indigo">{live.phase}</Badge>
                <span className="text-slate-500">
                  题 {live.question_count}
                  {debug?.state.max_questions ? `/${debug.state.max_questions}` : ""}
                </span>
                <span className="text-slate-500">追问深度 {live.followup_depth}</span>
                <span className="text-slate-500">
                  项目 {live.current_project_idx + 1}/{debug?.state.project_count ?? "?"}
                </span>
                <span className="text-slate-500">提示 {live.hint_count}</span>
                {debug && debug.next.length > 0 && (
                  <span className="text-slate-400">下一节点: {debug.next.join(", ")}</span>
                )}
              </>
            ) : (
              <span className="text-slate-400">等待首个状态事件…</span>
            )}
          </div>

          {decisions.length > 0 && (
            <div>
              <p className="font-semibold text-slate-500">决策时间线（decide 结构化输出）</p>
              <ul className="mt-1.5 space-y-1.5">
                {decisions.map((d, i) => (
                  <li key={i} className="rounded-lg bg-slate-50 px-3 py-2">
                    <span className="font-medium">#{i + 1}</span>
                    <span className="ml-2">得分 {d.score}</span>
                    <span className="ml-2 text-slate-500">
                      {d.next_action}
                      {d.effective_action !== d.next_action
                        ? ` → ${d.effective_action}`
                        : ""}
                      {d.guard ? `（守卫: ${d.guard}）` : ""}
                    </span>
                    <p className="mt-0.5 text-slate-600">{d.rationale}</p>
                    {d.evidence && (
                      <p className="mt-0.5 text-slate-400">证据：「{d.evidence}」</p>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {usage && usage.totals.calls > 0 && (
            <div>
              <p className="font-semibold text-slate-500">Token / 成本</p>
              <p className="mt-1 text-slate-600">
                调用 {usage.totals.calls} 次 · 输入 {usage.totals.prompt_tokens} · 输出{" "}
                {usage.totals.completion_tokens} · 缓存命中{" "}
                {Math.round(usage.totals.cache_hit_rate * 100)}% ·{" "}
                <span className="font-medium text-indigo-600">
                  ¥{usage.totals.cost_cny.toFixed(4)}
                </span>
              </p>
              <table className="mt-1.5 w-full text-left">
                <thead>
                  <tr className="text-slate-400">
                    <th className="font-normal">节点</th>
                    <th className="font-normal">模型</th>
                    <th className="font-normal">次数</th>
                    <th className="font-normal">输入/输出</th>
                    <th className="font-normal">命中</th>
                    <th className="font-normal">耗时</th>
                    <th className="font-normal">成本</th>
                  </tr>
                </thead>
                <tbody>
                  {usage.by_node.map((b) => (
                    <tr key={b.node + b.model} className="border-t border-slate-100">
                      <td className="py-1">{b.node}</td>
                      <td>{b.model}</td>
                      <td>{b.calls}</td>
                      <td>
                        {b.prompt_tokens}/{b.completion_tokens}
                      </td>
                      <td>{b.cache_hit_tokens}</td>
                      <td>{Math.round(b.latency_ms_avg)}ms</td>
                      <td>¥{b.cost_cny.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

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
