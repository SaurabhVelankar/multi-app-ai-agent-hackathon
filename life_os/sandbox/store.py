"""Sandbox store — per-user Gmail/Calendar worlds for mock + Shared Life OS.

Seed data lives in repo `sandbox/seed/`.
Runtime mutations copy-on-write into `sandbox/.runtime/` (gitignored).
"""

from __future__ import annotations

import datetime
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SEED_ROOT = _REPO_ROOT / "sandbox" / "seed" / "users"
_RUNTIME_ROOT = _REPO_ROOT / "sandbox" / ".runtime" / "users"
_MANIFEST = _REPO_ROOT / "sandbox" / "manifest.json"


def sandbox_enabled() -> bool:
    """Sandbox is on when mocks are on, unless explicitly disabled."""
    flag = os.getenv("LIFE_OS_USE_SANDBOX", "").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return False
    if flag in {"1", "true", "yes", "on"}:
        return True
    # Default: follow mock connectors
    from life_os.tools._common import use_mock_connectors

    return use_mock_connectors()


def load_manifest() -> dict[str, Any]:
    return json.loads(_MANIFEST.read_text(encoding="utf-8"))


def resolve_user_id(admin_id: Optional[str] = None, user_id: Optional[str] = None) -> str:
    if user_id:
        return user_id
    manifest = load_manifest()
    if admin_id:
        for u in manifest.get("users", []):
            ids = {u.get("admin_id"), *(u.get("admin_id_aliases") or [])}
            ids.discard(None)
            if admin_id in ids:
                return u["user_id"]
    # Default demo user
    return manifest.get("users", [{"user_id": "alex"}])[0]["user_id"]


def _user_runtime_dir(user_id: str) -> Path:
    return _RUNTIME_ROOT / user_id


def ensure_user_runtime(user_id: str) -> Path:
    """Copy seed → runtime once so connectors can mutate safely."""
    src = _SEED_ROOT / user_id
    dst = _user_runtime_dir(user_id)
    if not src.exists():
        raise FileNotFoundError(f"Sandbox seed missing for user_id={user_id}: {src}")
    if not dst.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src, dst)
    return dst


def reset_user(user_id: str) -> Path:
    dst = _user_runtime_dir(user_id)
    if dst.exists():
        shutil.rmtree(dst)
    return ensure_user_runtime(user_id)


def reset_all() -> list[str]:
    if _RUNTIME_ROOT.exists():
        shutil.rmtree(_RUNTIME_ROOT)
    ids = []
    for p in sorted(_SEED_ROOT.iterdir()):
        if p.is_dir():
            ensure_user_runtime(p.name)
            ids.append(p.name)
    return ids


def _read_json(user_id: str, name: str) -> dict[str, Any]:
    path = ensure_user_runtime(user_id) / name
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(user_id: str, name: str, data: dict[str, Any]) -> None:
    path = ensure_user_runtime(user_id) / name
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def get_profile(user_id: str) -> dict[str, Any]:
    return _read_json(user_id, "profile.json")


def list_inbox(user_id: str, *, label: str = "inbox") -> list[dict[str, Any]]:
    gmail = _read_json(user_id, "gmail.json")
    return [m for m in gmail.get("messages", []) if m.get("label", "inbox") == label]


def list_drafts(user_id: str) -> list[dict[str, Any]]:
    gmail = _read_json(user_id, "gmail.json")
    return list(gmail.get("drafts", []))


def list_sent(user_id: str) -> list[dict[str, Any]]:
    gmail = _read_json(user_id, "gmail.json")
    return list(gmail.get("sent", []))


def get_user_world(user_id: str) -> dict[str, Any]:
    """Snapshot of a sandbox user's mailbox + calendar (for cockpit demos)."""
    profile = get_profile(user_id)
    gmail = _read_json(user_id, "gmail.json")
    notion = _read_json(user_id, "notion.json")
    slack = _read_json(user_id, "slack.json")
    return {
        "user_id": user_id,
        "admin_id": profile.get("admin_id"),
        "display_name": profile.get("display_name"),
        "email": profile.get("email") or gmail.get("mailbox"),
        "mailbox": gmail.get("mailbox"),
        "inbox": list_inbox(user_id),
        "drafts": list(gmail.get("drafts", [])),
        "sent": list(gmail.get("sent", [])),
        "calendar_events": list_events(user_id),
        "notion_pages": list(notion.get("pages", [])),
        "slack_messages": list(slack.get("messages", [])),
    }


def get_message(user_id: str, message_id: str) -> Optional[dict[str, Any]]:
    gmail = _read_json(user_id, "gmail.json")
    for m in gmail.get("messages", []):
        if m.get("id") == message_id:
            return m
    return None


def thread_reply_target(
    user_id: str, thread_id: Optional[str]
) -> tuple[Optional[str], Optional[str]]:
    """Return (to_email, subject) for a reply draft on this thread."""
    if not thread_id:
        return None, None
    gmail = _read_json(user_id, "gmail.json")
    for m in gmail.get("messages", []):
        if m.get("thread_id") != thread_id:
            continue
        to_addr = m.get("from")
        subject = m.get("subject")
        if subject and not str(subject).lower().startswith("re:"):
            subject = f"Re: {subject}"
        return (str(to_addr) if to_addr else None, str(subject) if subject else None)
    return None, None


def get_scenario_message(scenario_id: str) -> tuple[str, dict[str, Any]]:
    manifest = load_manifest()
    for s in manifest.get("scenarios", []):
        if s.get("id") == scenario_id:
            user_id = s["user_id"]
            msg = get_message(user_id, s["gmail_message_id"])
            if msg is None:
                raise KeyError(f"Scenario message missing: {scenario_id}")
            return user_id, msg
    raise KeyError(f"Unknown scenario: {scenario_id}")


def add_draft(
    user_id: str,
    *,
    run_id: str,
    body: str,
    thread_id: Optional[str] = None,
    to: Optional[str] = None,
    subject: Optional[str] = None,
) -> dict[str, Any]:
    gmail = _read_json(user_id, "gmail.json")
    draft = {
        "draft_id": f"sbx-draft-{uuid.uuid4().hex[:10]}",
        "thread_id": thread_id,
        "run_id": run_id,
        "to": to,
        "subject": subject or f"Life OS follow-up ({run_id})",
        "body": body,
    }
    gmail.setdefault("drafts", []).append(draft)
    _write_json(user_id, "gmail.json", gmail)
    return draft


def _user_id_for_email(email: Optional[str]) -> Optional[str]:
    addr = (email or "").strip().lower()
    if not addr:
        return None
    for u in load_manifest().get("users", []):
        if str(u.get("email") or "").strip().lower() == addr:
            return str(u["user_id"])
    return None


def _deliver_to_recipient(
    *,
    from_user_id: str,
    sent: dict[str, Any],
) -> Optional[str]:
    """If `to` matches another sandbox user, land a copy in their inbox."""
    to_addr = sent.get("to")
    if not to_addr and sent.get("thread_id"):
        # Reply drafts often omit `to` — use the original message's From.
        sender_gmail = _read_json(from_user_id, "gmail.json")
        for m in sender_gmail.get("messages", []):
            if m.get("thread_id") == sent.get("thread_id") and m.get("from"):
                to_addr = m.get("from")
                break
    recipient_id = _user_id_for_email(str(to_addr) if to_addr else None)
    if not recipient_id or recipient_id == from_user_id:
        return None

    sender = get_profile(from_user_id)
    from_email = sender.get("email") or f"{from_user_id}@lifeos.sandbox"
    recipient_gmail = _read_json(recipient_id, "gmail.json")
    inbound = {
        "id": f"sbx-msg-{uuid.uuid4().hex[:10]}",
        "thread_id": sent.get("thread_id") or f"thread-{uuid.uuid4().hex[:8]}",
        "label": "inbox",
        "subject": sent.get("subject") or "(no subject)",
        "from": from_email,
        "to": [to_addr],
        "cc": [],
        "date": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "snippet": (sent.get("body") or "")[:120],
        "body": sent.get("body") or "",
        "run_id": sent.get("run_id"),
        "via_sandbox_send": True,
        "source_sent_id": sent.get("sent_id"),
    }
    recipient_gmail.setdefault("messages", []).append(inbound)
    _write_json(recipient_id, "gmail.json", recipient_gmail)
    return recipient_id


def send_draft(user_id: str, draft_id: str) -> dict[str, Any]:
    gmail = _read_json(user_id, "gmail.json")
    drafts = gmail.get("drafts", [])
    match = next((d for d in drafts if d.get("draft_id") == draft_id), None)
    if match is None:
        raise KeyError(f"Draft not found: {draft_id}")
    gmail["drafts"] = [d for d in drafts if d.get("draft_id") != draft_id]
    sent = {
        **match,
        "sent_id": f"sbx-sent-{uuid.uuid4().hex[:10]}",
        "label": "sent",
    }
    # Resolve reply recipient onto the sent record for cockpit visibility
    if not sent.get("to") and sent.get("thread_id"):
        for m in gmail.get("messages", []):
            if m.get("thread_id") == sent.get("thread_id") and m.get("from"):
                sent["to"] = m.get("from")
                break
    gmail.setdefault("sent", []).append(sent)
    _write_json(user_id, "gmail.json", gmail)
    delivered_to = _deliver_to_recipient(from_user_id=user_id, sent=sent)
    if delivered_to:
        sent = {**sent, "delivered_to_user_id": delivered_to}
    return sent


def list_events(user_id: str) -> list[dict[str, Any]]:
    cal = _read_json(user_id, "calendar.json")
    return list(cal.get("events", []))


def _parse_dt(value: str) -> datetime.datetime:
    """Parse ISO-8601 datetimes used in seed + tool args (Z or ±offset)."""
    text = (value or "").strip()
    if not text:
        raise ValueError("empty datetime")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.datetime.fromisoformat(text)
    if dt.tzinfo is None:
        # Treat naive as UTC so comparisons stay consistent
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def list_busy(user_id: str, time_min: str, time_max: str) -> list[dict[str, Any]]:
    """Return busy events overlapping [time_min, time_max) (timezone-aware)."""
    try:
        window_start = _parse_dt(time_min)
        window_end = _parse_dt(time_max)
    except ValueError:
        return []
    if window_end <= window_start:
        return []

    busy = []
    for ev in list_events(user_id):
        if not ev.get("busy", True):
            continue
        try:
            start = _parse_dt(str(ev.get("start", "")))
            end = _parse_dt(str(ev.get("end", "")))
        except ValueError:
            continue
        if start < window_end and end > window_start:
            busy.append(ev)
    return busy


def create_event(
    user_id: str,
    *,
    run_id: str,
    title: str,
    start: str,
    end: str,
    idempotency_key: str,
    allow_conflict: bool = False,
    attendees: Optional[list[str]] = None,
    organizer: Optional[str] = None,
    invite_kind: Optional[str] = None,
) -> dict[str, Any]:
    cal = _read_json(user_id, "calendar.json")
    # Idempotent: same key → return existing
    for ev in cal.get("events", []):
        if ev.get("idempotency_key") == idempotency_key:
            return ev

    conflicts = list_busy(user_id, start, end)
    if conflicts and not allow_conflict:
        return {
            "id": None,
            "summary": title,
            "start": start,
            "end": end,
            "busy": True,
            "source": "life_os",
            "run_id": run_id,
            "idempotency_key": idempotency_key,
            "proposed_only": True,
            "attendees": list(attendees or []),
            "organizer": organizer,
            "invite_kind": invite_kind,
            "conflicts": [
                {
                    "id": c.get("id"),
                    "summary": c.get("summary"),
                    "start": c.get("start"),
                    "end": c.get("end"),
                }
                for c in conflicts
            ],
        }

    event = {
        "id": f"sbx-cal-{uuid.uuid4().hex[:10]}",
        "summary": title,
        "start": start,
        "end": end,
        "busy": True,
        "source": "life_os",
        "run_id": run_id,
        "idempotency_key": idempotency_key,
        "proposed_only": False,
        "conflicts": [],
        "attendees": list(attendees or []),
        "organizer": organizer,
        "invite_kind": invite_kind,
    }
    cal.setdefault("events", []).append(event)
    _write_json(user_id, "calendar.json", cal)
    return event


def send_email(
    user_id: str,
    *,
    run_id: str,
    to: str,
    subject: str,
    body: str,
) -> dict[str, Any]:
    """Write a sent message for `user_id` and deliver into recipient inbox if known."""
    gmail = _read_json(user_id, "gmail.json")
    sent = {
        "sent_id": f"sbx-sent-{uuid.uuid4().hex[:10]}",
        "label": "sent",
        "run_id": run_id,
        "to": to,
        "subject": subject,
        "body": body,
    }
    gmail.setdefault("sent", []).append(sent)
    _write_json(user_id, "gmail.json", gmail)
    delivered_to = _deliver_to_recipient(from_user_id=user_id, sent=sent)
    if delivered_to:
        sent = {**sent, "delivered_to_user_id": delivered_to}
    return sent


def resolve_peer(
    *,
    from_admin_id: str,
    to_admin_id: str,
) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    """Return (from_user_id, to_user_id, from_profile, to_profile)."""
    from_user_id = resolve_user_id(admin_id=from_admin_id)
    to_user_id = resolve_user_id(admin_id=to_admin_id)
    if from_user_id == to_user_id:
        raise ValueError("from and to must be different users")
    return (
        from_user_id,
        to_user_id,
        get_profile(from_user_id),
        get_profile(to_user_id),
    )


def cross_user_action(
    *,
    action: str,
    from_admin_id: str,
    to_admin_id: str,
    subject: Optional[str] = None,
    body: Optional[str] = None,
    title: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    allow_conflict: bool = False,
) -> dict[str, Any]:
    """Demo helper: email / calendar invite / schedule meeting between two admins."""
    action_key = (action or "").strip().lower()
    from_uid, to_uid, from_p, to_p = resolve_peer(
        from_admin_id=from_admin_id,
        to_admin_id=to_admin_id,
    )
    from_email = str(from_p.get("email") or f"{from_uid}@lifeos.sandbox")
    to_email = str(to_p.get("email") or f"{to_uid}@lifeos.sandbox")
    from_name = str(from_p.get("display_name") or from_uid)
    to_name = str(to_p.get("display_name") or to_uid)
    run_id = f"manual-{uuid.uuid4().hex[:10]}"

    if action_key in {"email", "send_email"}:
        subj = (subject or "").strip() or f"Note from {from_name}"
        text = (body or "").strip() or f"Hi {to_name},\n\n(from {from_name} via Life OS sandbox)\n"
        sent = send_email(
            from_uid,
            run_id=run_id,
            to=to_email,
            subject=subj,
            body=text,
        )
        return {
            "ok": True,
            "action": "email",
            "run_id": run_id,
            "from_admin_id": from_admin_id,
            "to_admin_id": to_admin_id,
            "from_user_id": from_uid,
            "to_user_id": to_uid,
            "email": sent,
        }

    if action_key in {"calendar_invite", "invite"}:
        if not start or not end:
            raise ValueError("calendar_invite requires start and end")
        mtg_title = (title or subject or "").strip() or f"Meeting: {from_name} × {to_name}"
        host_key = f"invite-host-{run_id}"
        guest_key = f"invite-guest-{run_id}"
        host_event = create_event(
            from_uid,
            run_id=run_id,
            title=mtg_title,
            start=start,
            end=end,
            idempotency_key=host_key,
            allow_conflict=allow_conflict,
            attendees=[to_email],
            organizer=from_email,
            invite_kind="organizer",
        )
        guest_event = create_event(
            to_uid,
            run_id=run_id,
            title=f"{mtg_title} (invite from {from_name})",
            start=start,
            end=end,
            idempotency_key=guest_key,
            allow_conflict=allow_conflict,
            attendees=[from_email],
            organizer=from_email,
            invite_kind="invitee",
        )
        invite_body = (
            body
            or (
                f"You're invited to '{mtg_title}'.\n"
                f"When: {start} → {end}\n"
                f"Organizer: {from_name} <{from_email}>\n"
                f"Guest: {to_name} <{to_email}>\n"
            )
        )
        email = send_email(
            from_uid,
            run_id=run_id,
            to=to_email,
            subject=subject or f"Invite: {mtg_title}",
            body=invite_body,
        )
        return {
            "ok": True,
            "action": "calendar_invite",
            "run_id": run_id,
            "from_admin_id": from_admin_id,
            "to_admin_id": to_admin_id,
            "from_user_id": from_uid,
            "to_user_id": to_uid,
            "host_event": host_event,
            "guest_event": guest_event,
            "email": email,
            "proposed_only": bool(
                host_event.get("proposed_only") or guest_event.get("proposed_only")
            ),
        }

    if action_key in {"schedule_meeting", "meeting", "schedule"}:
        if not start or not end:
            raise ValueError("schedule_meeting requires start and end")
        mtg_title = (title or subject or "").strip() or f"Sync: {from_name} × {to_name}"
        host_key = f"mtg-host-{run_id}"
        guest_key = f"mtg-guest-{run_id}"
        host_event = create_event(
            from_uid,
            run_id=run_id,
            title=mtg_title,
            start=start,
            end=end,
            idempotency_key=host_key,
            allow_conflict=allow_conflict,
            attendees=[to_email],
            organizer=from_email,
            invite_kind="organizer",
        )
        guest_event = create_event(
            to_uid,
            run_id=run_id,
            title=mtg_title,
            start=start,
            end=end,
            idempotency_key=guest_key,
            allow_conflict=allow_conflict,
            attendees=[from_email],
            organizer=from_email,
            invite_kind="attendee",
        )
        confirm = send_email(
            from_uid,
            run_id=run_id,
            to=to_email,
            subject=subject or f"Scheduled: {mtg_title}",
            body=body
            or (
                f"Booked '{mtg_title}' on both calendars.\n"
                f"When: {start} → {end}\n"
                f"With: {from_name} <> {to_name}\n"
            ),
        )
        return {
            "ok": True,
            "action": "schedule_meeting",
            "run_id": run_id,
            "from_admin_id": from_admin_id,
            "to_admin_id": to_admin_id,
            "from_user_id": from_uid,
            "to_user_id": to_uid,
            "host_event": host_event,
            "guest_event": guest_event,
            "email": confirm,
            "proposed_only": bool(
                host_event.get("proposed_only") or guest_event.get("proposed_only")
            ),
        }

    raise ValueError(
        "Unknown action; use email | calendar_invite | schedule_meeting"
    )


def append_notion_page(user_id: str, *, run_id: str, title: str, body: str) -> dict[str, Any]:
    notion = _read_json(user_id, "notion.json")
    page = {
        "id": f"sbx-notion-{uuid.uuid4().hex[:10]}",
        "title": title,
        "body": body,
        "run_id": run_id,
        "source": "life_os",
        "url": f"sandbox://notion/{user_id}/{run_id}",
    }
    notion.setdefault("pages", []).append(page)
    _write_json(user_id, "notion.json", notion)
    return page


def post_slack(user_id: str, *, run_id: str, text: str) -> dict[str, Any]:
    slack = _read_json(user_id, "slack.json")
    msg = {
        "ts": f"sbx-slack-{uuid.uuid4().hex[:10]}",
        "run_id": run_id,
        "text": text,
        "source": "life_os",
    }
    slack.setdefault("messages", []).append(msg)
    _write_json(user_id, "slack.json", slack)
    return msg


def append_audit_row(user_id: str, row: list[Any]) -> dict[str, Any]:
    sheets = _read_json(user_id, "sheets.json")
    sheets.setdefault("rows", []).append(row)
    _write_json(user_id, "sheets.json", sheets)
    return {"row_index": len(sheets["rows"]) - 1, "row": row}
