"use client";

import { PIPELINE_NODES, type LifeState, type PipelineNode } from "@/lib/types";

function nodePhase(state: LifeState | null, node: PipelineNode): "done" | "active" | "waiting" | "blocked" {
  if (!state?.status) return "waiting";

  const status = state.status;
  const order: PipelineNode[] = [...PIPELINE_NODES];
  const idx = order.indexOf(node);

  if (status === "error" && node === "critic") return "blocked";
  if (status === "abort" && node === "auditor") return "done";
  if (status === "pass") return "done";

  if (status === "needs_approval") {
    if (node === "hitl") return "active";
    if (idx < order.indexOf("hitl")) return "done";
    return "waiting";
  }

  if (status === "running") {
    // Approximate progress from available artifacts
    const hasIntent = (state.intents?.length || 0) > 0;
    const hasPlan = (state.plan_steps?.length || 0) > 0;
    const hasCal = (state.calendar_actions?.length || 0) > 0;
    const hasTools = (state.tool_results?.length || 0) > 0;
    const hasDraft = (state.drafts?.length || 0) > 0;

    const furthest =
      hasDraft || hasTools
        ? "executor"
        : hasCal
          ? "scheduler"
          : hasPlan
            ? "planner"
            : hasIntent
              ? "priority"
              : "intake";

    const fIdx = order.indexOf(furthest);
    if (idx < fIdx) return "done";
    if (idx === fIdx) return "active";
    return "waiting";
  }

  if (status === "abort" || status === "error") {
    if (idx <= order.indexOf("critic")) return idx < order.indexOf("critic") ? "done" : "blocked";
    if (node === "auditor" && state.audit_ref) return "done";
    return "waiting";
  }

  return "waiting";
}

export function Timeline({ state }: { state: LifeState | null }) {
  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Pipeline</h2>
        <p>LangGraph specialists for this run.</p>
      </div>

      <ol className="pipeline">
        {PIPELINE_NODES.map((node) => {
          const phase = nodePhase(state, node);
          return (
            <li key={node} className={`pipe-item pipe-${phase}`}>
              <span className="pipe-dot" aria-hidden />
              <div>
                <div className="pipe-name">{node}</div>
                <div className="pipe-meta">{phase}</div>
              </div>
            </li>
          );
        })}
      </ol>

      {state?.plan_steps && state.plan_steps.length > 0 && (
        <div className="subblock">
          <h3>Plan steps</h3>
          <ul className="list">
            {state.plan_steps.map((step) => (
              <li key={step.id || `${step.app}-${step.action}`}>
                <span className="chip">{step.app || "?"}</span>
                <span className="mono">
                  {step.action}
                  {step.requires_hitl ? " · HITL" : ""}
                </span>
                <span className="muted">{step.status}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
