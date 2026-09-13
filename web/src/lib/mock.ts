import type {
  AddAdminRequest,
  Admin,
  AdminListResponse,
  ApproveRequest,
  CreateRunRequest,
  CreateRunResponse,
  LifeState,
  OAuthStartResponse,
} from "./types";
import { canApprove, canManageRoster } from "./types";

const store = new Map<string, LifeState>();

const mockRoster: AdminListResponse = {
  family_id: "hauns",
  hitl_policy: "any_of",
  admin_max: 10,
  admins: [
    {
      admin_id: "admin_01",
      name: "Parent A",
      role: "owner",
      email: "parent-a@example.com",
      google_connected: true,
      google_token_path: ".oauth/admin_01_google.json",
    },
    {
      admin_id: "admin_02",
      name: "Parent B",
      role: "operator",
      email: "parent-b@example.com",
      google_connected: false,
      google_token_path: ".oauth/admin_02_google.json",
    },
  ],
};

function uid(prefix: string) {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

function findAdmin(adminId: string): Admin | undefined {
  return mockRoster.admins.find((a) => a.admin_id === adminId);
}

export function listMockAdmins(): AdminListResponse {
  return {
    ...mockRoster,
    admins: mockRoster.admins.map((a) => ({ ...a })),
  };
}

export function mockAddAdmin(body: AddAdminRequest): Admin {
  const actor = findAdmin(body.acting_admin_id);
  if (!canManageRoster(actor?.role)) {
    throw new Error("403: Only owner can add admins");
  }
  if (mockRoster.admins.length >= mockRoster.admin_max) {
    throw new Error(`400: Admin roster full (max ${mockRoster.admin_max})`);
  }
  if (findAdmin(body.admin_id)) {
    throw new Error("400: admin_id already exists");
  }
  const admin: Admin = {
    admin_id: body.admin_id,
    name: body.name,
    role: body.role,
    email: body.email ?? null,
    slack_user_id: body.slack_user_id ?? null,
    google_token_path: `.oauth/${body.admin_id}_google.json`,
    google_connected: false,
  };
  mockRoster.admins.push(admin);
  return { ...admin };
}

export function mockRemoveAdmin(
  adminId: string,
  actingAdminId: string,
): { ok: boolean; removed: string } {
  const actor = findAdmin(actingAdminId);
  if (!canManageRoster(actor?.role)) {
    throw new Error("403: Only owner can remove admins");
  }
  const target = findAdmin(adminId);
  if (!target) throw new Error("404: Admin not found");
  if (target.role === "owner") {
    const owners = mockRoster.admins.filter((a) => a.role === "owner");
    if (owners.length <= 1) {
      throw new Error("400: Cannot remove last owner");
    }
  }
  mockRoster.admins = mockRoster.admins.filter((a) => a.admin_id !== adminId);
  return { ok: true, removed: adminId };
}

export function mockOAuthStart(adminId: string): OAuthStartResponse {
  if (!findAdmin(adminId)) throw new Error("404: Unknown admin_id");
  const a = findAdmin(adminId)!;
  a.google_connected = true;
  return {
    admin_id: adminId,
    auth_url: `https://accounts.google.com/o/oauth2/auth#mock-${adminId}`,
  };
}

export function createMockRun(body: CreateRunRequest): CreateRunResponse {
  const runId = uid("run");
  const now = new Date().toISOString();
  const requester = body.admin_id ?? "admin_01";

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
    family_id: mockRoster.family_id,
    admin_id: requester,
    shared_with: mockRoster.admins.map((a) => a.admin_id),
    approval_assignee: null,
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

  const actor = findAdmin(body.admin_id);
  if (!actor || !canApprove(actor.role)) {
    throw new Error("403: Admin cannot approve (unknown or viewer role)");
  }

  const approved = body.decision === "approve";
  // Preserve requester admin_id (token owner); record who approved separately
  const next: LifeState = {
    ...state,
    approval_assignee: body.admin_id,
    needs_approval: false,
    status: approved ? "pass" : "abort",
    approvals: {
      ...(state.approvals || {}),
      [`hitl:${runId}`]: approved ? "approved" : "rejected",
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
