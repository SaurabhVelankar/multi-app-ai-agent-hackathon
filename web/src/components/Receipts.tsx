"use client";

import type { LifeState } from "@/lib/types";

function labelOf(item: Record<string, unknown>): string {
  return (
    String(item.label || item.action || item.app || item.external_id || "receipt")
  );
}

export function Receipts({ state }: { state: LifeState | null }) {
  const receipts = state?.execution_receipts || [];
  const tools = state?.tool_results || [];
  const errors = state?.errors || [];

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Side effects</h2>
        <p>
          What landed across apps
          {state?.admin_id
            ? ` · writes as ${state.admin_id}`
            : ""}
          .
        </p>
      </div>

      {(state?.family_id || state?.shared_with?.length) && (
        <p className="mono muted attribution">
          {state.family_id ? `family ${state.family_id}` : ""}
          {state.family_id && state.shared_with?.length ? " · " : ""}
          {state.shared_with?.length
            ? `shared_with [${state.shared_with.join(", ")}]`
            : ""}
          {state.approval_assignee
            ? ` · approved_by ${state.approval_assignee}`
            : ""}
        </p>
      )}

      {receipts.length === 0 && tools.length === 0 && (
        <p className="muted">No receipts yet — start a run.</p>
      )}

      {receipts.length > 0 && (
        <ul className="list">
          {receipts.map((r, i) => (
            <li key={`${labelOf(r)}-${i}`}>
              <span className="chip">{String(r.app || "app")}</span>
              <span>{labelOf(r)}</span>
              {r.external_id != null && (
                <span className="mono muted">{String(r.external_id)}</span>
              )}
            </li>
          ))}
        </ul>
      )}

      {tools.length > 0 && (
        <div className="subblock">
          <h3>Tool results</h3>
          <ul className="list dense">
            {tools.map((t, i) => (
              <li key={i}>
                <span className="chip">{String(t.app || "?")}</span>
                <span className="mono">{String(t.action || "")}</span>
                <span className={t.ok ? "ok" : "err"}>
                  {t.ok ? "ok" : "fail"}
                  {t.dry_run ? " · dry" : ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {state?.audit_ref && (
        <p className="audit">
          Audit ref: <span className="mono">{state.audit_ref}</span>
        </p>
      )}

      {errors.length > 0 && (
        <div className="subblock">
          <h3>Errors</h3>
          <pre className="mono draft-body">{JSON.stringify(errors, null, 2)}</pre>
        </div>
      )}
    </section>
  );
}
