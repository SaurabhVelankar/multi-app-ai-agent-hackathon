"""Calendar tool — create / propose events."""

from __future__ import annotations

from typing import Any, Optional

from life_os import idempotency
from life_os.tools._common import env, use_mock_connectors
from life_os.sandbox import sandbox_enabled
from life_os.types import ToolResult, make_tool_result


def create_calendar_event(
    run_id: str,
    title: str,
    start: str,
    end: str,
    idempotency_key: str,
    *,
    admin_id: Optional[str] = None,
    create: bool = True,
) -> ToolResult:
    cached = idempotency.get_cached(admin_id, idempotency_key)
    if cached is not None:
        return cached

    if not create:
        result = make_tool_result(
            ok=True,
            app="calendar",
            action="propose_event",
            external_id=None,
            idempotency_key=idempotency_key,
            raw={"title": title, "start": start, "end": end, "run_id": run_id},
            proposed_only=True,
        )
        return idempotency.put_cached(admin_id, idempotency_key, result)

    if use_mock_connectors():
        if sandbox_enabled():
            from life_os.sandbox import create_event, resolve_user_id

            user_id = resolve_user_id(admin_id=admin_id)
            event = create_event(
                user_id,
                run_id=run_id,
                title=title,
                start=start,
                end=end,
                idempotency_key=idempotency_key,
            )
            print(
                f"[sandbox:calendar] create_event user={user_id} "
                f"title={title!r} id={event['id']}"
            )
            result = make_tool_result(
                ok=True,
                app="calendar",
                action="create_event",
                external_id=event["id"],
                idempotency_key=idempotency_key,
                raw={"sandbox": True, "user_id": user_id, **event},
                proposed_only=False,
            )
            return idempotency.put_cached(admin_id, idempotency_key, result)

        fake_id = f"mock-cal-{run_id}-{idempotency_key[-8:]}"
        print(f"[mock:calendar] create_event title={title!r} start={start} end={end} id={fake_id}")
        result = make_tool_result(
            ok=True,
            app="calendar",
            action="create_event",
            external_id=fake_id,
            idempotency_key=idempotency_key,
            raw={"mock": True, "title": title, "start": start, "end": end},
            proposed_only=False,
        )
        return idempotency.put_cached(admin_id, idempotency_key, result)

    try:
        from life_os.adapters import google_auth

        service = google_auth.build_service("calendar", "v3", admin_id=admin_id)
        calendar_id = env("GOOGLE_CALENDAR_ID", "primary") or "primary"
        body: dict[str, Any] = {
            "summary": title,
            "description": f"Life OS run_id={run_id} key={idempotency_key}",
            "start": {"dateTime": start},
            "end": {"dateTime": end},
            "extendedProperties": {
                "private": {
                    "life_os_run_id": run_id,
                    "life_os_idempotency_key": idempotency_key,
                }
            },
        }
        created = (
            service.events()
            .insert(calendarId=calendar_id, body=body)
            .execute()
        )
        result = make_tool_result(
            ok=True,
            app="calendar",
            action="create_event",
            external_id=created.get("id"),
            idempotency_key=idempotency_key,
            raw=created,
            proposed_only=False,
        )
        return idempotency.put_cached(admin_id, idempotency_key, result)
    except Exception as exc:  # noqa: BLE001 — surface as tool_result
        result = make_tool_result(
            ok=False,
            app="calendar",
            action="create_event",
            idempotency_key=idempotency_key,
            error=str(exc),
        )
        return result
