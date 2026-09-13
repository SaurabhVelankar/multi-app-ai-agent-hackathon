"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AdminRoster, roleOf } from "@/components/AdminRoster";
import { HitlPanel } from "@/components/HitlPanel";
import { Receipts } from "@/components/Receipts";
import { StatusPill } from "@/components/StatusPill";
import { Timeline } from "@/components/Timeline";
import { TriggerPanel } from "@/components/TriggerPanel";
import {
  addAdmin,
  approveRun,
  createRun,
  getApiBase,
  getRun,
  healthCheck,
  listAdmins,
  startGoogleOAuth,
  useMocks,
} from "@/lib/api";
import type {
  AdminListResponse,
  CreateRunRequest,
  LifeState,
} from "@/lib/types";
import { canApprove } from "@/lib/types";

export function Cockpit() {
  const [roster, setRoster] = useState<AdminListResponse | null>(null);
  const [adminId, setAdminId] = useState("admin_01");
  const [state, setState] = useState<LifeState | null>(null);
  const [busy, setBusy] = useState(false);
  const [banner, setBanner] = useState<string | null>(null);
  const [apiOk, setApiOk] = useState<boolean | null>(null);

  const mocks = useMocks();
  const activeRole = useMemo(
    () => roleOf(roster, adminId),
    [roster, adminId],
  );

  const loadRoster = useCallback(async () => {
    const next = await listAdmins();
    setRoster(next);
    setAdminId((prev) => {
      if (next.admins.some((a) => a.admin_id === prev)) return prev;
      return next.admins[0]?.admin_id ?? prev;
    });
    return next;
  }, []);

  useEffect(() => {
    let cancelled = false;
    healthCheck()
      .then(() => {
        if (!cancelled) setApiOk(true);
      })
      .catch(() => {
        if (!cancelled) setApiOk(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!mocks && apiOk === false) return;
    void loadRoster().catch((e) =>
      setBanner(e instanceof Error ? e.message : "Failed to load roster"),
    );
  }, [mocks, apiOk, loadRoster]);

  const refresh = useCallback(
    async (runId: string) => {
      const next = await getRun(runId, adminId);
      setState(next);
      return next;
    },
    [adminId],
  );

  useEffect(() => {
    if (!state?.run_id) return;
    if (state.status !== "running") return;

    const id = window.setInterval(() => {
      void refresh(state.run_id!).catch((e) =>
        setBanner(e instanceof Error ? e.message : "Poll failed"),
      );
    }, 1200);

    return () => window.clearInterval(id);
  }, [state?.run_id, state?.status, refresh]);

  async function handleStart(input: CreateRunRequest) {
    setBusy(true);
    setBanner(null);
    try {
      const res = await createRun(input);
      const snap = await refresh(res.run_id);
      if (snap.status === "running") {
        setBanner("Run in progress — polling for updates…");
      }
    } catch (e) {
      setBanner(e instanceof Error ? e.message : "Start failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleDecide(decision: "approve" | "deny") {
    if (!state?.run_id) return;
    setBusy(true);
    setBanner(null);
    try {
      const next = await approveRun(state.run_id, {
        decision,
        admin_id: adminId,
      });
      setState(next);
      setBanner(
        decision === "approve"
          ? "Approved — run resumed through Auditor. Writes still use the requester's tokens."
          : "Denied — run aborted with audit trail.",
      );
    } catch (e) {
      setBanner(e instanceof Error ? e.message : "Approve failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleConnectGoogle(id: string) {
    setBusy(true);
    setBanner(null);
    try {
      const { auth_url } = await startGoogleOAuth(id);
      if (mocks) {
        await loadRoster();
        setBanner(`Mock: marked ${id} Google as connected.`);
        return;
      }
      window.open(auth_url, "_blank", "noopener,noreferrer");
      setBanner("Complete Google consent in the new tab, then refresh roster.");
      window.setTimeout(() => {
        void loadRoster().catch(() => undefined);
      }, 2500);
    } catch (e) {
      setBanner(e instanceof Error ? e.message : "OAuth start failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleAddAdmin() {
    setBusy(true);
    setBanner(null);
    try {
      const n = (roster?.admins.length ?? 0) + 1;
      const id = `admin_${String(n).padStart(2, "0")}`;
      await addAdmin({
        acting_admin_id: adminId,
        admin_id: id,
        name: `Admin ${n}`,
        role: "operator",
      });
      await loadRoster();
      setAdminId(id);
      setBanner(`Added ${id} (in-memory until backend restart).`);
    } catch (e) {
      setBanner(e instanceof Error ? e.message : "Add admin failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Life OS</p>
          <h1>Family operations cockpit</h1>
          <p className="lede">
            Each admin uses their own Google tokens. Approve does not switch
            whose calendar or Gmail is written.
          </p>
        </div>
        <div className="hero-meta">
          <StatusPill status={state?.status || "idle"} />
          <div className="meta-line mono">
            mode: {mocks ? "UI mocks" : "live API"}
          </div>
          <div className="meta-line mono">
            api: {getApiBase()}{" "}
            {apiOk === null ? "" : apiOk ? "· up" : "· unreachable"}
          </div>
          {(state?.family_id || roster?.family_id) && (
            <div className="meta-line mono">
              family: {state?.family_id || roster?.family_id}
            </div>
          )}
          {state?.run_id && (
            <div className="meta-line mono">run: {state.run_id}</div>
          )}
          {state?.admin_id && (
            <div className="meta-line mono">
              requester tokens: {state.admin_id}
              {state.approval_assignee
                ? ` · approved by ${state.approval_assignee}`
                : ""}
            </div>
          )}
        </div>
      </header>

      {banner && <div className="banner">{banner}</div>}

      {!mocks && apiOk === false && (
        <div className="banner warn">
          Backend not reachable at {getApiBase()}. Start{" "}
          <span className="mono">uvicorn life_os.api:app --reload --port 8000</span>{" "}
          or set <span className="mono">NEXT_PUBLIC_USE_MOCKS=true</span> in{" "}
          <span className="mono">web/.env.local</span>.
        </div>
      )}

      <div className="grid">
        <div className="col">
          <AdminRoster
            roster={roster}
            activeId={adminId}
            onSelect={setAdminId}
            onConnectGoogle={handleConnectGoogle}
            onAdd={handleAddAdmin}
            busy={busy}
          />
          <TriggerPanel
            adminId={adminId}
            busy={busy}
            onSubmit={handleStart}
          />
          <HitlPanel
            state={state}
            adminId={adminId}
            canApprove={canApprove(activeRole)}
            busy={busy}
            onDecide={handleDecide}
          />
        </div>
        <div className="col">
          <Timeline state={state} />
          <Receipts state={state} />
        </div>
      </div>
    </div>
  );
}
