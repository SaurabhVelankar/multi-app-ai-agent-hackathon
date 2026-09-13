"""Notion tool — create meeting brief / task page."""

from __future__ import annotations

from typing import Optional

from life_os import idempotency
from life_os.tools._common import use_mock_connectors
from life_os.sandbox import sandbox_enabled
from life_os.types import ToolResult, make_tool_result


def create_notion_page(
    run_id: str,
    title: str,
    body: str,
    idempotency_key: str,
    *,
    admin_id: Optional[str] = None,
) -> ToolResult:
    cached = idempotency.get_cached(admin_id, idempotency_key)
    if cached is not None:
        return cached

    if use_mock_connectors():
        if sandbox_enabled():
            from life_os.sandbox import append_notion_page, resolve_user_id

            user_id = resolve_user_id(admin_id=admin_id)
            page = append_notion_page(user_id, run_id=run_id, title=title, body=body)
            print(f"[sandbox:notion] create_page user={user_id} title={title!r} id={page['id']}")
            result = make_tool_result(
                ok=True,
                app="notion",
                action="create_page",
                external_id=page["id"],
                idempotency_key=idempotency_key,
                raw={"sandbox": True, "user_id": user_id, **page},
            )
            return idempotency.put_cached(admin_id, idempotency_key, result)

        fake_id = f"mock-notion-{run_id}-{idempotency_key[-8:]}"
        print(f"[mock:notion] create_page title={title!r} id={fake_id}")
        result = make_tool_result(
            ok=True,
            app="notion",
            action="create_page",
            external_id=fake_id,
            idempotency_key=idempotency_key,
            raw={"mock": True, "title": title, "body": body},
        )
        return idempotency.put_cached(admin_id, idempotency_key, result)

    try:
        from life_os.adapters import notion_client

        page = notion_client.create_page(
            title=title, body=body, run_id=run_id, admin_id=admin_id
        )
        result = make_tool_result(
            ok=True,
            app="notion",
            action="create_page",
            external_id=page.get("id"),
            idempotency_key=idempotency_key,
            raw=page,
        )
        return idempotency.put_cached(admin_id, idempotency_key, result)
    except Exception as exc:  # noqa: BLE001
        return make_tool_result(
            ok=False,
            app="notion",
            action="create_page",
            idempotency_key=idempotency_key,
            error=str(exc),
        )
