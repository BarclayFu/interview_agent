export const btn = {
  primary:
    "inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-40",
  secondary:
    "inline-flex items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40",
  ghost:
    "inline-flex items-center justify-center rounded-xl px-3 py-2 text-sm text-slate-500 transition hover:bg-slate-100 hover:text-slate-700",
};

export const input =
  "w-full rounded-xl border border-slate-300 px-3 py-2 text-sm outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100";

export const card = "rounded-2xl border border-slate-200 bg-white p-6 shadow-sm";

type Tone = "slate" | "green" | "amber" | "red" | "indigo";

const tones: Record<Tone, string> = {
  slate: "bg-slate-100 text-slate-600",
  green: "bg-emerald-50 text-emerald-700",
  amber: "bg-amber-50 text-amber-700",
  red: "bg-rose-50 text-rose-700",
  indigo: "bg-indigo-50 text-indigo-700",
};

export function Badge({ tone = "slate", children }: { tone?: Tone; children: React.ReactNode }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function statusTone(status: string): Tone {
  if (status === "done" || status === "finished") return "green";
  if (status === "failed") return "red";
  if (status === "pending" || status === "parsing" || status === "generating") return "amber";
  if (status === "active" || status === "paused") return "indigo";
  return "slate";
}
