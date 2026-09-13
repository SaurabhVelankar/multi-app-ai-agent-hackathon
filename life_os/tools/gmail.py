"""Gmail tools — draft always; send HITL-gated only."""

from __future__ import annotations

import base64
from email.mime.text import MIMEText
from typing import Optional

from life_os import idempotency
from life_os.tools._common import use_mock_connectors
from life_os.sandbox import sandbox_enabled
from life_os.types import GmailDraft, ToolResult, make_tool_result


def draft_gmail_reply(
    run_id: str,
    thread_id: Optional[str],
    body: str,
    *,
    admin_id: Optional[str] = None,
) -> GmailDraft:
    idem_key = f"gmail:{run_id}:draft"
    cached = idempotency.get_cached(admin_id, idem_key)
    if cached is not None and isinstance(cached, dict) and "draft_id" in cached:
        return cached  # type: ignore[return-value]

    if use_mock_connectors():
        if sandbox_enabled():
            from life_os.sandbox import add_draft, resolve_user_id

            user_id = resolve_user_id(admin_id=admin_id)
            draft = add_draft(
                user_id,
                run_id=run_id,
                body=body,
                thread_id=thread_id,
            )
            draft_out: GmailDraft = {
                "draft_id": draft["draft_id"],
                "thread_id": thread_id,
                "body": body,
                "run_id": run_id,
            }
            print(
                f"[sandbox:gmail] draft_reply user={user_id} "
                f"draft_id={draft_out['draft_id']} thread_id={thread_id}"
            )
            idempotency.put_cached(admin_id, idem_key, draft_out)
            return draft_out

        draft = {
            "draft_id": f"mock-draft-{run_id}",
            "thread_id": thread_id,
            "body": body,
            "run_id": run_id,
        }
        print(f"[mock:gmail] draft_reply draft_id={draft['draft_id']} thread_id={thread_id}")
        idempotency.put_cached(admin_id, idem_key, draft)
        return draft

    try:
        from life_os.adapters import google_auth

        service = google_auth.build_service("gmail", "v1", admin_id=admin_id)
        message = MIMEText(body)
        message["Subject"] = f"Life OS follow-up ({run_id})"
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        draft_body: dict = {"message": {"raw": raw}}
        if thread_id:
            draft_body["message"]["threadId"] = thread_id
        created = service.users().drafts().create(userId="me", body=draft_body).execute()
        draft = {
            "draft_id": created.get("id") or f"draft-{run_id}",
            "thread_id": thread_id or (created.get("message") or {}).get("threadId"),
            "body": body,
            "run_id": run_id,
        }
        idempotency.put_cached(admin_id, idem_key, draft)
        return draft
    except Exception as exc:  # noqa: BLE001
        # Surface failure as a draft with error marker for executor to log
        draft = {
            "draft_id": f"error-draft-{run_id}",
            "thread_id": thread_id,
            "body": body,
            "run_id": run_id,
            "error": str(exc),  # type: ignore[typeddict-unknown-key]
        }
        return draft  # type: ignore[return-value]


def send_gmail(
    run_id: str,
    draft_id: str,
    *,
    admin_id: Optional[str] = None,
) -> ToolResult:
    """Send a previously created draft. Caller MUST gate with HITL approve."""
    idem_key = f"gmail:{run_id}:send:{draft_id}"
    cached = idempotency.get_cached(admin_id, idem_key)
    if cached is not None:
        return cached

    if draft_id.startswith("error-draft-"):
        return make_tool_result(
            ok=False,
            app="gmail",
            action="send",
            idempotency_key=idem_key,
            error="Cannot send error draft; create draft failed earlier",
        )

    if use_mock_connectors():
        if sandbox_enabled():
            from life_os.sandbox import resolve_user_id, send_draft

            user_id = resolve_user_id(admin_id=admin_id)
            try:
                sent = send_draft(user_id, draft_id)
            except KeyError as exc:
                return make_tool_result(
                    ok=False,
                    app="gmail",
                    action="send",
                    idempotency_key=idem_key,
                    error=str(exc),
                )
            print(f"[sandbox:gmail] SEND user={user_id} draft_id={draft_id}")
            result = make_tool_result(
                ok=True,
                app="gmail",
                action="send",
                external_id=sent.get("sent_id") or draft_id,
                idempotency_key=idem_key,
                raw={"sandbox": True, "user_id": user_id, "draft_id": draft_id},
            )
            return idempotency.put_cached(admin_id, idem_key, result)

        print(f"[mock:gmail] SEND draft_id={draft_id} run_id={run_id}")
        result = make_tool_result(
            ok=True,
            app="gmail",
            action="send",
            external_id=f"mock-sent-{draft_id}",
            idempotency_key=idem_key,
            raw={"mock": True, "draft_id": draft_id},
        )
        return idempotency.put_cached(admin_id, idem_key, result)

    try:
        from life_os.adapters import google_auth

        service = google_auth.build_service("gmail", "v1", admin_id=admin_id)
        sent = (
            service.users()
            .drafts()
            .send(userId="me", body={"id": draft_id})
            .execute()
        )
        result = make_tool_result(
            ok=True,
            app="gmail",
            action="send",
            external_id=sent.get("id") or draft_id,
            idempotency_key=idem_key,
            raw=sent,
        )
        return idempotency.put_cached(admin_id, idem_key, result)
    except Exception as exc:  # noqa: BLE001
        return make_tool_result(
            ok=False,
            app="gmail",
            action="send",
            idempotency_key=idem_key,
            error=str(exc),
        )
