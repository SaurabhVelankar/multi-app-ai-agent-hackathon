"use client";

import type { Admin, AdminListResponse, AdminRole } from "@/lib/types";
import { canManageRoster } from "@/lib/types";

type Props = {
  roster: AdminListResponse | null;
  activeId: string;
  onSelect: (id: string) => void;
  onConnectGoogle: (adminId: string) => Promise<void>;
  onAdd: () => Promise<void>;
  busy: boolean;
};

export function AdminRoster({
  roster,
  activeId,
  onSelect,
  onConnectGoogle,
  onAdd,
  busy,
}: Props) {
  const admins = roster?.admins ?? [];
  const active = admins.find((a) => a.admin_id === activeId);
  const max = roster?.admin_max ?? 10;
  const canAdd = canManageRoster(active?.role) && admins.length < max;

  return (
    <section className="panel compact">
      <div className="panel-head">
        <h2>Family roster</h2>
        <p>
          {roster
            ? `${roster.family_id} · ${roster.hitl_policy} · ${admins.length}/${max}`
            : "Loading roster…"}
        </p>
      </div>

      <div className="admin-row">
        {admins.map((a) => (
          <button
            key={a.admin_id}
            type="button"
            className={`admin-chip ${activeId === a.admin_id ? "on" : ""}`}
            onClick={() => onSelect(a.admin_id)}
            title={`${a.name} · ${a.role}`}
          >
            <span
              className={`oauth-dot ${a.google_connected ? "ok" : "off"}`}
              aria-hidden
            />
            {a.name || a.admin_id}
            <span className="role-tag">{a.role}</span>
          </button>
        ))}
      </div>

      {active && (
        <div className="admin-detail mono">
          <div>
            acting as <strong>{active.admin_id}</strong>
          </div>
          <div className="muted">
            Google: {active.google_connected ? "connected" : "missing"}
            {active.email ? ` · ${active.email}` : ""}
          </div>
          {!active.google_connected && (
            <button
              type="button"
              className="btn-ghost"
              disabled={busy}
              onClick={() => void onConnectGoogle(active.admin_id)}
            >
              Connect Google
            </button>
          )}
        </div>
      )}

      <button
        type="button"
        className="btn-ghost"
        disabled={busy || !canAdd}
        onClick={() => void onAdd()}
        title={
          !canManageRoster(active?.role)
            ? "Only owner can add admins"
            : undefined
        }
      >
        {admins.length >= max
          ? "Roster full"
          : canManageRoster(active?.role)
            ? "Add admin"
            : "Owner-only add"}
      </button>
    </section>
  );
}

export function roleOf(
  roster: AdminListResponse | null,
  adminId: string,
): AdminRole | undefined {
  return roster?.admins.find((a: Admin) => a.admin_id === adminId)?.role;
}
