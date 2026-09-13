export type RunStatus =
  | "running"
  | "needs_approval"
  | "pass"
  | "abort"
  | "error";

export type TriggerType = "goal" | "email" | "slack";

export type IntentType = "meeting" | "task" | "follow_up" | "info";

export type StepStatus = "pending" | "done" | "skipped" | "blocked";

export type AdminRole = "owner" | "operator" | "viewer";

export interface TriggerDict {
  type?: TriggerType;
  raw?: string | Record<string, unknown>;
  source_id?: string | null;
}

export interface IntentDict {
  id?: string;
  type?: IntentType;
  summary?: string;
  entities?: Record<string, unknown>;
  confidence?: number;
}

export interface PlanStepDict {
  id?: string;
  action?: string;
  app?: string;
  args?: Record<string, unknown>;
  requires_hitl?: boolean;
  status?: StepStatus;
}

/** Matches shared-LifeOS LifeState (contracts/openapi.yaml). */
export interface LifeState {
  run_id?: string;
  thread_id?: string;
  created_at?: string;
  family_id?: string | null;
  /** Requester — connector writes use this admin's OAuth tokens. */
  admin_id?: string | null;
  shared_with?: string[];
  approval_assignee?: string | null;
  trigger?: TriggerDict;
  normalized_context?: Record<string, unknown>;
  intents?: IntentDict[];
  priority_scores?: Record<string, unknown>;
  selected_intent?: IntentDict | null;
  plan_steps?: PlanStepDict[];
  calendar_actions?: Record<string, unknown>[];
  drafts?: Record<string, unknown>[];
  approvals?: Record<string, "approved" | "rejected" | "pending">;
  tool_results?: Record<string, unknown>[];
  execution_receipts?: Record<string, unknown>[];
  errors?: Record<string, unknown>[];
  retry_count?: number;
  status?: RunStatus;
  needs_approval?: boolean;
  audit_ref?: string | null;
}

export interface CreateRunRequest {
  trigger_type: TriggerType;
  trigger_payload: string | Record<string, unknown>;
  admin_id?: string | null;
  source_id?: string | null;
}

export interface CreateRunResponse {
  run_id: string;
  status: RunStatus | string;
}

export interface ApproveRequest {
  decision: "approve" | "deny";
  admin_id: string;
}

export interface Admin {
  admin_id: string;
  name: string;
  role: AdminRole;
  email?: string | null;
  slack_user_id?: string | null;
  google_token_path?: string;
  google_connected?: boolean;
}

export interface AdminListResponse {
  family_id: string;
  hitl_policy: string;
  admin_max: number;
  admins: Admin[];
}

export interface AddAdminRequest {
  acting_admin_id: string;
  admin_id: string;
  name: string;
  role: AdminRole;
  email?: string | null;
  slack_user_id?: string | null;
}

export interface OAuthStartResponse {
  admin_id: string;
  auth_url: string;
}

export interface OAuthStatus {
  admin_id: string;
  google?: "connected" | "missing";
  connected?: boolean;
  token_path?: string;
  email?: string | null;
  mock_mode?: boolean;
  notion?: "connected" | "missing" | null;
}

export const PIPELINE_NODES = [
  "intake",
  "priority",
  "planner",
  "scheduler",
  "executor",
  "critic",
  "hitl",
  "auditor",
] as const;

export type PipelineNode = (typeof PIPELINE_NODES)[number];

export function canApprove(role: AdminRole | undefined): boolean {
  return role === "owner" || role === "operator";
}

export function canManageRoster(role: AdminRole | undefined): boolean {
  return role === "owner";
}
