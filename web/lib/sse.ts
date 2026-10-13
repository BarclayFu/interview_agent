// POST + SSE：浏览器 EventSource 只支持 GET，故用 fetch + ReadableStream 手写解析。
export interface SseEvent {
  event: string;
  data: unknown;
}

export async function* streamSse(
  path: string,
  body: unknown,
  signal?: AbortSignal,
): AsyncGenerator<SseEvent> {
  const resp = await fetch(`/api${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  // SSE 帧分隔符可能是 \n\n 或 \r\n\r\n（sse-starlette 默认 \r\n）——两者都要认
  const FRAME_DELIM = /\r?\n\r?\n/;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let m: RegExpExecArray | null;
    while ((m = FRAME_DELIM.exec(buf)) !== null) {
      const frame = buf.slice(0, m.index);
      buf = buf.slice(m.index + m[0].length);
      let event = "message";
      let data = "";
      for (const rawLine of frame.split("\n")) {
        const line = rawLine.replace(/\r$/, "");
        if (line.startsWith("event:")) event = line.slice(6).trim();
        if (line.startsWith("data:")) data += line.slice(5).trim();
      }
      if (data) {
        try {
          yield { event, data: JSON.parse(data) };
        } catch {
          yield { event, data };
        }
      }
    }
  }
}
