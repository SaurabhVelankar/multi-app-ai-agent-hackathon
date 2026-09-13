"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listAdmins, useMocks } from "@/lib/api";
import { openSandboxWindows } from "@/components/SandboxWorld";
import type { AdminListResponse } from "@/lib/types";

export default function SandboxIndexPage() {
  const [roster, setRoster] = useState<AdminListResponse | null>(null);
  const [banner, setBanner] = useState<string | null>(null);
  const mocks = useMocks();

  useEffect(() => {
    void listAdmins()
      .then(setRoster)
      .catch((e) =>
        setBanner(e instanceof Error ? e.message : "Failed to load roster"),
      );
  }, [mocks]);

  const admins = roster?.admins ?? [];

  function handleOpenAll() {
    const n = openSandboxWindows(admins.map((a) => a.admin_id));
    setBanner(
      n === 0
        ? "Browser blocked popups — allow popups for this site, then try again."
        : `Opened ${n} sandbox window${n === 1 ? "" : "s"}.`,
    );
  }

  return (
    <main className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">Sandbox</p>
          <h1>Per-user desks</h1>
          <p className="lede">
            Each family admin gets their own live mailbox/calendar window.
          </p>
        </div>
        <div className="hero-meta">
          <Link href="/" className="btn-ghost">
            ← Cockpit
          </Link>
          <button
            type="button"
            className="btn-primary"
            disabled={admins.length === 0}
            onClick={handleOpenAll}
          >
            Open all in separate windows
          </button>
        </div>
      </header>

      {banner && <div className="banner">{banner}</div>}

      <div className="banner">
        Sending is locked to whoever’s desk you open — e.g. Alex’s window can
        only send as Alex. Open a user below to compose email / invites.
      </div>

      <section className="panel">
        <div className="panel-head">
          <h2>Users</h2>
          <p>
            {roster
              ? `${admins.length} sandbox worlds`
              : "Loading roster…"}
          </p>
        </div>
        <ul className="list sandbox-index-list">
          {admins.map((a) => (
            <li key={a.admin_id}>
              <div className="world-item">
                <strong>{a.name || a.admin_id}</strong>
                <span className="mono muted">
                  {a.admin_id}
                  {a.email ? ` · ${a.email}` : ""}
                </span>
              </div>
              <div className="sandbox-actions">
                <Link
                  className="btn-ghost"
                  href={`/sandbox/${encodeURIComponent(a.admin_id)}`}
                >
                  Open desk
                </Link>
                <button
                  type="button"
                  className="btn-ghost"
                  onClick={() => openSandboxWindows([a.admin_id])}
                >
                  New window
                </button>
              </div>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
