"use client";

import type { LifeState } from "@/lib/types";

type Props = {
  state: LifeState | null;
  adminId: string;
  canApprove: boolean;
  busy: boolean;
  onDecide: (decision: "approve" | "deny") => Promise<void>;
};

export function HitlPanel({
  state,
  adminId,
  canApprove,
  busy,
  onDecide,
}: Props) {
  const open = Boolean(
    state?.needs_approval || state?.status === "needs_approval",
  );
  const draft = state?.drafts?.[0];
  const requester = state?.admin_id;

  return (
    <section className={`panel ${open ? "panel-alert" : ""}`}>
      <div className="panel-head">
        <h2>Human-in-the-loop</h2>
        <p>
          {open
            ? "Irreversible action waiting on an owner/operator."
            : "No approval pending for this run."}
        </p>
      </div>

      {!open && (
        <p className="muted">
          When Critic gates a send (or low-confidence act), Approve / Deny shows
          up here. Approving does not change whose OAuth tokens execute writes
          — that stays the run requester.
        </p>
      )}

      {open && (
        <>
          <div className="hitl-meta mono muted">
            {requester && <div>requester (token owner): {requester}</div>}
            <div>acting admin: {adminId || "—"}</div>
            {state?.shared_with && state.shared_with.length > 0 && (
              <div>shared with: {state.shared_with.join(", ")}</div>
            )}
            {!canApprove && (
              <div className="err">
                Viewers cannot approve — switch to an owner or operator.
              </div>
            )}
          </div>

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
              disabled={busy || !adminId.trim() || !canApprove}
              onClick={() => onDecide("approve")}
            >
              Approve
            </button>
            <button
              type="button"
              className="btn-ghost danger"
              disabled={busy || !adminId.trim() || !canApprove}
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
