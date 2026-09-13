"use client";

import { useCallback, useEffect, useState } from "react";
import { AdminRoster } from "@/components/AdminRoster";
import { HitlPanel } from "@/components/HitlPanel";
import { Receipts } from "@/components/Receipts";
import { StatusPill } from "@/components/StatusPill";
import { Timeline } from "@/components/Timeline";
import { TriggerPanel } from "@/components/TriggerPanel";
import {
  approveRun,
  createRun,
  getApiBase,
  getRun,
  healthCheck,
  useMocks,
} from "@/lib/api";
import type { CreateRunRequest, LifeState } from "@/lib/types";

export function Cockpit() {
  const [admins, setAdmins] = useState<string[]>(["admin-1"]);
  const [adminId, setAdminId] = useState("admin-1");
  const [state, setState] = useState<LifeState | null>(null);
  const [busy, setBusy] = useState(false);
  const [banner, setBanner] = useState<string | null>(null);
  const [apiOk, setApiOk] = useState<boolean | null>(null);

  const mocks = useMocks();

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

  const refresh = useCallback(async (runId: string) => {
    const next = await getRun(runId);
    setState(next);
    return next;
  }, []);

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
          ? "Approved — run resumed through Auditor."
          : "Denied — run aborted with audit trail.",
      );
    } catch (e) {
      setBanner(e instanceof Error ? e.message : "Approve failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Life OS</p>
          <h1>Operations cockpit</h1>
          <p className="lede">
            Trigger a life outcome, watch the multi-agent graph act across apps,
            approve only what can&apos;t be undone.
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
          {state?.run_id && (
            <div className="meta-line mono">run: {state.run_id}</div>
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
            admins={admins}
            activeId={adminId}
            onSelect={setAdminId}
            onAdd={(id) =>
              setAdmins((prev) =>
                prev.includes(id) || prev.length >= 10 ? prev : [...prev, id],
              )
            }
          />
          <TriggerPanel
            adminId={adminId}
            busy={busy}
            onSubmit={handleStart}
          />
          <HitlPanel
            state={state}
            adminId={adminId}
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
