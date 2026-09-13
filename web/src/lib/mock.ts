import type {
  ApproveRequest,
  CreateRunRequest,
  CreateRunResponse,
  LifeState,
} from "./types";

const store = new Map<string, LifeState>();

function uid(prefix: string) {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

export function createMockRun(body: CreateRunRequest): CreateRunResponse {
  const runId = uid("run");
  const now = new Date().toISOString();

  const summary =
    typeof body.trigger_payload === "string"
      ? body.trigger_payload.slice(0, 120)
      : String(
          (body.trigger_payload as { subject?: string }).subject ||
            "Incoming signal",
        );

  const state: LifeState = {
    run_id: runId,
    thread_id: runId,
    created_at: now,
    admin_id: body.admin_id ?? null,
    trigger: {
      type: body.trigger_type,
      raw: body.trigger_payload,
      source_id: body.source_id ?? null,
    },
    intents: [
      {
        id: "intent-1",
        type: "meeting",
        summary,
        confidence: 0.86,
        entities: { duration_min: 30 },
      },
    ],
    priority_scores: { "intent-1": { total: 0.86, deadline: 0.4 } },
    selected_intent: {
      id: "intent-1",
      type: "meeting",
      summary,
      confidence: 0.86,
    },
    plan_steps: [
      {
        id: "s1",
        action: "create_event",
        app: "calendar",
        requires_hitl: false,
        status: "done",
        args: {},
      },
      {
        id: "s2",
        action: "create_notion",
        app: "notion",
        requires_hitl: false,
        status: "done",
        args: {},
      },
      {
        id: "s3",
        action: "notify_slack",
        app: "slack",
        requires_hitl: false,
        status: "done",
        args: {},
      },
      {
        id: "s4",
        action: "draft_email",
        app: "gmail",
        requires_hitl: true,
        status: "blocked",
        args: {},
      },
    ],
    calendar_actions: [
      {
        id: "mock-cal-1",
        summary: "Life OS meeting block",
        htmlLink: "https://calendar.google.com/",
      },
    ],
    drafts: [
      {
        id: "mock-draft-1",
        to: "sarah@example.com",
        subject: "Re: meeting",
        body: "Happy to meet — I've held a slot and dropped a brief in Notion.",
      },
    ],
    approvals: { "email_send:mock-draft-1": "pending" },
    tool_results: [
      {
        ok: true,
        app: "calendar",
        action: "create_event",
        external_id: "mock-cal-1",
        dry_run: true,
      },
      {
        ok: true,
        app: "notion",
        action: "create_page",
        external_id: "mock-notion-1",
        url: "https://notion.so/",
        dry_run: true,
      },
      {
        ok: true,
        app: "slack",
        action: "post_message",
        external_id: "mock-slack-1",
        dry_run: true,
      },
      {
        ok: true,
        app: "gmail",
        action: "create_draft",
        external_id: "mock-draft-1",
        dry_run: true,
      },
    ],
    execution_receipts: [
      { app: "calendar", external_id: "mock-cal-1", label: "Event created" },
      { app: "notion", external_id: "mock-notion-1", label: "Brief page" },
      { app: "slack", external_id: "mock-slack-1", label: "Receipt posted" },
      { app: "gmail", external_id: "mock-draft-1", label: "Draft ready" },
    ],
    errors: [],
    retry_count: 0,
    status: "needs_approval",
    needs_approval: true,
    audit_ref: null,
  };

  store.set(runId, state);
  return { run_id: runId, status: "needs_approval" };
}

export function getMockRun(runId: string): LifeState | undefined {
  return store.get(runId);
}

export function decideMockApproval(
  runId: string,
  body: ApproveRequest,
): LifeState {
  const state = store.get(runId);
  if (!state) throw new Error("404: Run not found");
  if (state.status !== "needs_approval") {
    throw new Error("409: Run not in needs_approval state");
  }

  const approved = body.decision === "approve";
  const next: LifeState = {
    ...state,
    admin_id: body.admin_id,
    needs_approval: false,
    status: approved ? "pass" : "abort",
    approvals: {
      ...(state.approvals || {}),
      "email_send:mock-draft-1": approved ? "approved" : "rejected",
    },
    plan_steps: (state.plan_steps || []).map((s) =>
      s.action === "draft_email"
        ? { ...s, status: approved ? "done" : "skipped" }
        : s,
    ),
    audit_ref: `mock-sheet-row-${runId.slice(-6)}`,
    tool_results: [
      ...(state.tool_results || []),
      {
        ok: true,
        app: "sheets",
        action: "append_row",
        external_id: `mock-sheet-${runId.slice(-6)}`,
        dry_run: true,
      },
    ],
    execution_receipts: [
      ...(state.execution_receipts || []),
      {
        app: "sheets",
        external_id: `mock-sheet-${runId.slice(-6)}`,
        label: "Audit logged",
      },
    ],
  };

  store.set(runId, next);
  return next;
}
