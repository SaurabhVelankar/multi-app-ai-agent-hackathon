"use client";

import { useEffect, useMemo, useState } from "react";
import { postSandboxAction } from "@/lib/api";
import type {
  Admin,
  AdminListResponse,
  SandboxActionRequest,
  SandboxActionResult,
  SandboxActionType,
} from "@/lib/types";

type Props = {
  roster: AdminListResponse | null;
  /** Locked sender — must match the open sandbox / selected cockpit admin. */
  fromAdminId: string;
  busy?: boolean;
  onDone?: (result: SandboxActionResult) => void;
};

const ACTIONS: { id: SandboxActionType; label: string; hint: string }[] = [
  {
    id: "email",
    label: "Email",
    hint: "Send mail from this sandbox user into another’s inbox.",
  },
  {
    id: "calendar_invite",
    label: "Calendar invite",
    hint: "Invite another user from this desk (both calendars + email).",
  },
  {
    id: "schedule_meeting",
    label: "Schedule meeting",
    hint: "Book the same busy block on both calendars + confirmation email.",
  },
];

function defaultStartEnd(): { start: string; end: string } {
  const start = "2026-09-16T15:00:00-07:00";
  const end = "2026-09-16T15:30:00-07:00";
  return { start, end };
}

function labelAdmin(a: Admin): string {
  return `${a.name || a.admin_id}${a.email ? ` · ${a.email}` : ""}`;
}

export function CrossUserActions({
  roster,
  fromAdminId,
  busy: parentBusy,
  onDone,
}: Props) {
  const admins = roster?.admins ?? [];
  const defaults = useMemo(() => defaultStartEnd(), []);
  const fromId = fromAdminId.trim();
  const sender = admins.find((a) => a.admin_id === fromId);

  const [action, setAction] = useState<SandboxActionType>("email");
  const [toId, setToId] = useState("");
  const [title, setTitle] = useState("Life OS sync");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [start, setStart] = useState(defaults.start);
  const [end, setEnd] = useState(defaults.end);
  const [allowConflict, setAllowConflict] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SandboxActionResult | null>(null);

  useEffect(() => {
    if (!admins.length || !fromId) return;
    setToId((prev) => {
      if (prev && prev !== fromId && admins.some((a) => a.admin_id === prev)) {
        return prev;
      }
      return (
        admins.find((a) => a.admin_id !== fromId)?.admin_id || ""
      );
    });
  }, [admins, fromId]);

  const needsTime = action !== "email";
  const canSubmit =
    !!fromId &&
    !!toId &&
    fromId !== toId &&
    !busy &&
    !parentBusy &&
    (!needsTime || (!!start.trim() && !!end.trim()));

  async function handleSubmit() {
    setError(null);
    setResult(null);
    if (!fromId) {
      setError("No sandbox user selected for this instance.");
      return;
    }
    if (!canSubmit) {
      setError("Pick a different recipient (and a time window for calendar).");
      return;
    }
    const payload: SandboxActionRequest = {
      from_admin_id: fromId,
      to_admin_id: toId,
      action,
      subject: subject.trim() || undefined,
      body: body.trim() || undefined,
      title: title.trim() || undefined,
      start: needsTime ? start.trim() : undefined,
      end: needsTime ? end.trim() : undefined,
      allow_conflict: allowConflict,
    };
    setBusy(true);
    try {
      const res = await postSandboxAction(payload);
      setResult(res);
      onDone?.(res);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusy(false);
    }
  }

  const meta = ACTIONS.find((a) => a.id === action);

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Send as this user</h2>
        <p>
          {meta?.hint || "Actions leave from the open sandbox instance only."}
        </p>
      </div>

      <p className="mono muted attribution">
        Sender locked to{" "}
        <strong>{sender ? labelAdmin(sender) : fromId || "(none)"}</strong>
      </p>

      <div className="seg">
        {ACTIONS.map((a) => (
          <button
            key={a.id}
            type="button"
            className={action === a.id ? "seg-on" : ""}
            onClick={() => setAction(a.id)}
          >
            {a.label}
          </button>
        ))}
      </div>

      <label className="field-label">
        To
        <select
          className="field"
          value={toId}
          onChange={(e) => setToId(e.target.value)}
        >
          {admins
            .filter((a) => a.admin_id !== fromId)
            .map((a) => (
              <option key={a.admin_id} value={a.admin_id}>
                {labelAdmin(a)}
              </option>
            ))}
        </select>
      </label>

      {needsTime && (
        <>
          <label className="field-label">
            Meeting title
            <input
              className="field"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Life OS sync"
            />
          </label>
          <div className="cross-grid">
            <label className="field-label">
              Start (ISO)
              <input
                className="field mono"
                value={start}
                onChange={(e) => setStart(e.target.value)}
              />
            </label>
            <label className="field-label">
              End (ISO)
              <input
                className="field mono"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
              />
            </label>
          </div>
          <label className="check-row">
            <input
              type="checkbox"
              checked={allowConflict}
              onChange={(e) => setAllowConflict(e.target.checked)}
            />
            Force book even if busy (skip propose-only)
          </label>
        </>
      )}

      <label className="field-label">
        Subject {action === "email" ? "" : "(optional email subject)"}
        <input
          className="field"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          placeholder={
            action === "email" ? "Quick note" : "Invite / confirmation subject"
          }
        />
      </label>

      <label className="field-label">
        Body
        <textarea
          className="field"
          rows={4}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Optional message body…"
        />
      </label>

      {error && <p className="err">{error}</p>}

      <button
        type="button"
        className="btn-primary"
        disabled={!canSubmit}
        onClick={() => void handleSubmit()}
      >
        {busy ? "Sending…" : `Send ${meta?.label.toLowerCase() || "action"}`}
      </button>

      {result && (
        <div className="subblock">
          <h3>Result</h3>
          <p className="mono muted">
            {result.action} · {result.from_user_id} → {result.to_user_id}
            {result.proposed_only ? " · proposed only (busy conflict)" : ""}
          </p>
          {result.email && (
            <p className="muted">
              Email to {String(result.email.to || "?")}
              {result.email.delivered_to_user_id
                ? ` · delivered → ${String(result.email.delivered_to_user_id)}`
                : ""}
            </p>
          )}
          {(result.host_event || result.guest_event) && (
            <ul className="list dense">
              {result.host_event && (
                <li>
                  <span className="chip">host</span>
                  <span>
                    {String(result.host_event.summary || "event")}
                    {result.host_event.proposed_only ? " · propose" : ""}
                  </span>
                </li>
              )}
              {result.guest_event && (
                <li>
                  <span className="chip">guest</span>
                  <span>
                    {String(result.guest_event.summary || "event")}
                    {result.guest_event.proposed_only ? " · propose" : ""}
                  </span>
                </li>
              )}
            </ul>
          )}
          <p className="muted">
            Open the recipient&apos;s sandbox desk to verify inbox / calendar.
          </p>
        </div>
      )}
    </section>
  );
}
