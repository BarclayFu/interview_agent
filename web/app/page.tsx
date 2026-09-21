import { ApiPing } from "./api-ping";

export const dynamic = "force-dynamic";

const API_ORIGIN = process.env.API_ORIGIN ?? "http://localhost:8000";

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API_ORIGIN}${path}`, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export default async function Home() {
  const version = await getJson<{ version: string; built_at: string }>("/version");
  const ready = await getJson<{ db: string; redis: string }>("/readyz");

  return (
    <main style={{ fontFamily: "system-ui", padding: 40, lineHeight: 1.8 }}>
      <h1>Interview Agent · 走路骨架</h1>
      <p>后端版本（服务端渲染）：{version ? version.version : "不可达"}</p>
      <p>
        DB：{ready?.db ?? "?"} · Redis：{ready?.redis ?? "?"}
      </p>
      <ApiPing />
      <p style={{ color: "#999", fontSize: 12 }}>API: {API_ORIGIN}</p>
    </main>
  );
}
