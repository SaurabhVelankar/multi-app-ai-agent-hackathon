"use client";

import type { RunStatus } from "@/lib/types";

const STYLES: Record<RunStatus | "unknown", string> = {
  running: "bg-sky-500/15 text-sky-200 ring-sky-400/30",
  needs_approval: "bg-amber-500/15 text-amber-100 ring-amber-400/35",
  pass: "bg-emerald-500/15 text-emerald-100 ring-emerald-400/30",
  abort: "bg-zinc-500/20 text-zinc-200 ring-zinc-400/25",
  error: "bg-rose-500/15 text-rose-100 ring-rose-400/30",
  unknown: "bg-white/10 text-white/70 ring-white/15",
};

export function StatusPill({ status }: { status?: string }) {
  const key = (status as RunStatus) || "unknown";
  const cls = STYLES[key] || STYLES.unknown;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium tracking-wide ring-1 ${cls}`}
    >
      {status || "unknown"}
    </span>
  );
}
