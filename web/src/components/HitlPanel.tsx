"use client";

import type { LifeState } from "@/lib/types";

type Props = {
  state: LifeState | null;
  adminId: string;
  busy: boolean;
  onDecide: (decision: "approve" | "deny") => Promise<void>;
};

export function HitlPanel({ state, adminId, busy, onDecide }: Props) {
  const open = Boolean(state?.needs_approval || state?.status === "needs_approval");
  const draft = state?.drafts?.[0];

  return (
    <section className={`panel ${open ? "panel-alert" : ""}`}>
      <div className="panel-head">
        <h2>Human-in-the-loop</h2>
        <p>
          {open
            ? "Irreversible action waiting on you."
            : "No approval pending for this run."}
        </p>
      </div>

      {!open && (
        <p className="muted">
          When Critic gates a Gmail send (or low-confidence act), Approve / Deny
          shows up here.
        </p>
      )}

      {open && (
        <>
          {draft && (
            <div className="draft">
              <div className="muted">Draft preview</div>
              <pre className="mono draft-body">
                {JSON.stringify(draft, null, 2)}
              </pre>
            </div>
          )}

          <div className="btn-row">
            <button
              type="button"
              className="btn-primary"
              disabled={busy || !adminId.trim()}
              onClick={() => onDecide("approve")}
            >
              Approve
            </button>
            <button
              type="button"
              className="btn-ghost danger"
              disabled={busy || !adminId.trim()}
              onClick={() => onDecide("deny")}
            >
              Deny
            </button>
          </div>
        </>
      )}
    </section>
  );
}
