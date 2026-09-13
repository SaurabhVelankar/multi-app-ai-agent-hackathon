import type {
  ApproveRequest,
  CreateRunRequest,
  CreateRunResponse,
  LifeState,
} from "./types";
import { createMockRun, decideMockApproval, getMockRun } from "./mock";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  "http://localhost:8000";

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

  return res.json() as Promise<T>;
}

export async function healthCheck(): Promise<{ status: string }> {
  if (useMocks()) return { status: "ok-mock" };
  return request("/health");
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

export async function getRun(runId: string): Promise<LifeState> {
  if (useMocks()) {
    const state = getMockRun(runId);
    if (!state) throw new Error("404: Run not found");
    return state;
  }
  return request(`/runs/${encodeURIComponent(runId)}`);
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
