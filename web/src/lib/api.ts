import type {
  AddAdminRequest,
  Admin,
  AdminListResponse,
  ApproveRequest,
  CreateRunRequest,
  CreateRunResponse,
  LifeState,
  OAuthStartResponse,
  OAuthStatus,
  SandboxActionRequest,
  SandboxActionResult,
  SandboxWorldSnapshot,
} from "./types";
import {
  createMockRun,
  decideMockApproval,
  getMockRun,
  getMockSandboxWorld,
  listMockAdmins,
  mockAddAdmin,
  mockOAuthStart,
  mockRemoveAdmin,
  mockSandboxAction,
} from "./mock";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  "http://localhost:8001";

export function useMocks(): boolean {
  return process.env.NEXT_PUBLIC_USE_MOCKS === "true";
}

export function getApiBase(): string {
  return API_URL;
}

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status}: ${detail}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export async function healthCheck(): Promise<{ status: string }> {
  if (useMocks()) return { status: "ok-mock" };
  return request("/health");
}

export async function listAdmins(): Promise<AdminListResponse> {
  if (useMocks()) return listMockAdmins();
  return request("/admins");
}

export async function addAdmin(body: AddAdminRequest): Promise<Admin> {
  if (useMocks()) return mockAddAdmin(body);
  return request("/admins", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function removeAdmin(
  adminId: string,
  actingAdminId: string,
): Promise<{ ok: boolean; removed: string }> {
  if (useMocks()) return mockRemoveAdmin(adminId, actingAdminId);
  const q = `?acting_admin_id=${encodeURIComponent(actingAdminId)}`;
  return request(`/admins/${encodeURIComponent(adminId)}${q}`, {
    method: "DELETE",
  });
}

export async function startGoogleOAuth(
  adminId: string,
): Promise<OAuthStartResponse> {
  if (useMocks()) return mockOAuthStart(adminId);
  return request(
    `/admins/${encodeURIComponent(adminId)}/oauth/google/start`,
  );
}

export async function getOAuthStatus(adminId: string): Promise<OAuthStatus> {
  if (useMocks()) {
    const roster = listMockAdmins();
    const a = roster.admins.find((x) => x.admin_id === adminId);
    return {
      admin_id: adminId,
      google: a?.google_connected ? "connected" : "missing",
      connected: Boolean(a?.google_connected),
      mock_mode: true,
      notion: "missing",
    };
  }
  return request(`/admins/${encodeURIComponent(adminId)}/oauth/status`);
}

export async function createRun(
  body: CreateRunRequest,
): Promise<CreateRunResponse> {
  if (useMocks()) return createMockRun(body);
  return request("/runs", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getRun(
  runId: string,
  adminId?: string | null,
): Promise<LifeState> {
  if (useMocks()) {
    const state = getMockRun(runId);
    if (!state) throw new Error("404: Run not found");
    return state;
  }
  const q =
    adminId && adminId.trim()
      ? `?admin_id=${encodeURIComponent(adminId.trim())}`
      : "";
  return request(`/runs/${encodeURIComponent(runId)}${q}`);
}

export async function approveRun(
  runId: string,
  body: ApproveRequest,
): Promise<LifeState> {
  if (useMocks()) return decideMockApproval(runId, body);
  return request(`/runs/${encodeURIComponent(runId)}/approve`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function getSandboxWorld(
  adminId: string,
): Promise<SandboxWorldSnapshot> {
  if (useMocks()) return getMockSandboxWorld(adminId);
  return request(`/sandbox/admins/${encodeURIComponent(adminId)}`);
}

export async function postSandboxAction(
  body: SandboxActionRequest,
): Promise<SandboxActionResult> {
  if (useMocks()) return mockSandboxAction(body);
  return request("/sandbox/actions", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
