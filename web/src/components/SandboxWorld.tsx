"use client";

import { useCallback, useEffect, useState } from "react";
import { getSandboxWorld } from "@/lib/api";
import type { SandboxWorldSnapshot } from "@/lib/types";

type Props = {
  adminId: string;
  /** Bump after runs/approvals so the mailbox refreshes. */
  refreshKey?: string | number | null;
  /** Auto-poll interval (standalone desks). */
  pollMs?: number;
  /** Compact panel vs dedicated window layout. */
  variant?: "panel" | "page";
};

function preview(text: unknown, n = 140): string {
  const s = String(text ?? "").replace(/\s+/g, " ").trim();
  if (!s) return "(empty)";
  return s.length > n ? `${s.slice(0, n)}…` : s;
}

export function SandboxWorld({
  adminId,
  refreshKey,
  pollMs,
  variant = "panel",
}: Props) {
  const [world, setWorld] = useState<SandboxWorldSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!adminId.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const next = await getSandboxWorld(adminId);
      setWorld(next);
      setUpdatedAt(new Date().toLocaleTimeString());
    } catch (e) {
      setWorld(null);
      setError(e instanceof Error ? e.message : "Failed to load sandbox");
    } finally {
      setLoading(false);
    }
  }, [adminId]);

  useEffect(() => {
    void load();
  }, [load, refreshKey]);

  useEffect(() => {
    if (!pollMs || pollMs < 500) return;
    const id = window.setInterval(() => {
      void load();
    }, pollMs);
    return () => window.clearInterval(id);
  }, [pollMs, load]);

  const drafts = world?.drafts ?? [];
  const sent = world?.sent ?? [];
  const inbox = world?.inbox ?? [];
  const events = world?.calendar_events ?? [];
  const agentInbox = inbox.filter((m) => m.via_sandbox_send || m.run_id);
  const isPage = variant === "page";

  const body = (
    <>
      {error && <p className="err">{error}</p>}

      {world && (
        <p className="mono muted attribution">
          {world.display_name || world.user_id} · {world.email || world.mailbox}{" "}
          · user <strong>{world.user_id}</strong>
          {updatedAt ? ` · ${updatedAt}` : ""}
        </p>
      )}

      {!world && !error && (
        <p className="muted">Select an admin to inspect their sandbox.</p>
      )}

      {world && (
        <>
          <div className="subblock">
            <h3>Drafts ({drafts.length})</h3>
            {drafts.length === 0 ? (
              <p className="muted">No drafts yet.</p>
            ) : (
              <ul className="list dense world-list">
                {drafts.map((d, i) => (
                  <li key={String(d.draft_id || i)}>
                    <span className="chip">draft</span>
                    <div className="world-item">
                      <div className="mono">
                        to: {String(d.to || "(reply thread)")}
                        {d.subject ? ` · ${String(d.subject)}` : ""}
                      </div>
                      <div className="muted">{preview(d.body)}</div>
                      {d.draft_id != null && (
                        <div className="mono muted">{String(d.draft_id)}</div>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="subblock">
            <h3>Sent ({sent.length})</h3>
            {sent.length === 0 ? (
              <p className="muted">Nothing sent yet — approve a draft send.</p>
            ) : (
              <ul className="list dense world-list">
                {sent.map((s, i) => (
                  <li key={String(s.sent_id || i)}>
                    <span className="chip ok-chip">sent</span>
                    <div className="world-item">
                      <div className="mono">
                        to: {String(s.to || "?")}
                        {s.delivered_to_user_id
                          ? ` → inbox ${String(s.delivered_to_user_id)}`
                          : ""}
                      </div>
                      <div className="muted">{preview(s.body)}</div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="subblock">
            <h3>Delivered here ({agentInbox.length})</h3>
            {agentInbox.length === 0 ? (
              <p className="muted">
                No cross-user deliveries yet. Open the recipient&apos;s sandbox
                window after a send.
              </p>
            ) : (
              <ul className="list dense world-list">
                {agentInbox.map((m, i) => (
                  <li key={String(m.id || i)}>
                    <span className="chip">inbox</span>
                    <div className="world-item">
                      <div className="mono">
                        from: {String(m.from || "?")} · {String(m.subject || "")}
                      </div>
                      <div className="muted">{preview(m.body || m.snippet)}</div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="subblock">
            <h3>Calendar ({events.length})</h3>
            {events.length === 0 ? (
              <p className="muted">No events.</p>
            ) : (
              <ul className="list dense world-list">
                {events
                  .slice(-8)
                  .reverse()
                  .map((ev, i) => (
                    <li key={String(ev.id || i)}>
                      <span className="chip">cal</span>
                      <div className="world-item">
                        <div>
                          {String(ev.summary || "event")}
                          {ev.proposed_only ? " · proposed only" : ""}
                        </div>
                        <div className="mono muted">
                          {String(ev.start || "?")} → {String(ev.end || "?")}
                        </div>
                      </div>
                    </li>
                  ))}
              </ul>
            )}
          </div>
        </>
      )}
    </>
  );

  if (isPage) {
    return (
      <div className="sandbox-desk">
        <header className="sandbox-desk-head">
          <div>
            <p className="eyebrow">Sandbox desk</p>
            <h1>{world?.display_name || adminId}</h1>
            <p className="lede mono">{adminId}</p>
          </div>
          <button
            type="button"
            className="btn-ghost"
            disabled={loading || !adminId}
            onClick={() => void load()}
          >
            {loading ? "…" : "Refresh"}
          </button>
        </header>
        <div className="panel sandbox-desk-body">{body}</div>
      </div>
    );
  }

  return (
    <section className="panel">
      <div className="panel-head row-between">
        <div>
          <h2>Sandbox mailbox</h2>
          <p>
            Live world for the selected admin — drafts, sent, and inbound
            deliveries.
          </p>
        </div>
        <div className="sandbox-actions">
          <a
            className="btn-ghost"
            href={`/sandbox/${encodeURIComponent(adminId)}`}
            target={`sandbox-${adminId}`}
            rel="noopener noreferrer"
          >
            Open window
          </a>
          <button
            type="button"
            className="btn-ghost"
            disabled={loading || !adminId}
            onClick={() => void load()}
          >
            {loading ? "…" : "Refresh"}
          </button>
        </div>
      </div>
      {body}
    </section>
  );
}

/** Open one browser window/tab per admin sandbox desk. */
export function openSandboxWindows(adminIds: string[]): number {
  if (typeof window === "undefined") return 0;
  let opened = 0;
  for (const id of adminIds) {
    const url = `${window.location.origin}/sandbox/${encodeURIComponent(id)}`;
    // Named targets reuse an existing desk for that admin instead of spawning duplicates.
    // Avoid "noopener" here so we can detect blocked popups (null return).
    const w = window.open(url, `lifeos-sandbox-${id}`, "width=540,height=860");
    if (w) {
      try {
        w.opener = null;
      } catch {
        /* ignore cross-origin */
      }
      opened += 1;
    }
  }
  return opened;
}
