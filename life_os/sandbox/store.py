"""Sandbox store — per-user Gmail/Calendar worlds for mock + Shared Life OS.

Seed data lives in repo `sandbox/seed/`.
Runtime mutations copy-on-write into `sandbox/.runtime/` (gitignored).
"""

from __future__ import annotations

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


def get_message(user_id: str, message_id: str) -> Optional[dict[str, Any]]:
    gmail = _read_json(user_id, "gmail.json")
    for m in gmail.get("messages", []):
        if m.get("id") == message_id:
            return m
    return None


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
    gmail.setdefault("sent", []).append(sent)
    _write_json(user_id, "gmail.json", gmail)
    return sent


def list_events(user_id: str) -> list[dict[str, Any]]:
    cal = _read_json(user_id, "calendar.json")
    return list(cal.get("events", []))


def list_busy(user_id: str, time_min: str, time_max: str) -> list[dict[str, Any]]:
    """Naive string-range overlap on ISO datetimes (good enough for sandbox demos)."""
    busy = []
    for ev in list_events(user_id):
        if not ev.get("busy", True):
            continue
        start, end = ev.get("start", ""), ev.get("end", "")
        if start < time_max and end > time_min:
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
) -> dict[str, Any]:
    cal = _read_json(user_id, "calendar.json")
    # Idempotent: same key → return existing
    for ev in cal.get("events", []):
        if ev.get("idempotency_key") == idempotency_key:
            return ev
    event = {
        "id": f"sbx-cal-{uuid.uuid4().hex[:10]}",
        "summary": title,
        "start": start,
        "end": end,
        "busy": True,
        "source": "life_os",
        "run_id": run_id,
        "idempotency_key": idempotency_key,
    }
    cal.setdefault("events", []).append(event)
    _write_json(user_id, "calendar.json", cal)
    return event


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
