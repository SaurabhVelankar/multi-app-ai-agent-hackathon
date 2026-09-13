"""Slack tools — receipts + approval requests."""

from __future__ import annotations

from typing import Optional

from life_os import idempotency
from life_os.tools._common import env, use_mock_connectors
from life_os.types import ToolResult, make_tool_result


def post_slack_receipt(
    run_id: str,
    text: str,
    *,
    admin_id: Optional[str] = None,
) -> ToolResult:
    idem_key = f"slack:{run_id}:receipt"
    cached = idempotency.get_cached(admin_id, idem_key)
    if cached is not None:
        return cached

    if use_mock_connectors():
        fake_id = f"mock-slack-receipt-{run_id}"
        print(f"[mock:slack] receipt run_id={run_id} text={text!r}")
        result = make_tool_result(
            ok=True,
            app="slack",
            action="post_receipt",
            external_id=fake_id,
            idempotency_key=idem_key,
            raw={"mock": True, "text": text},
        )
        return idempotency.put_cached(admin_id, idem_key, result)

    try:
        from life_os.adapters import slack_client

        mention = env("ADMIN_PRIMARY_SLACK") if env("HITL_POLICY", "primary") == "primary" else None
        resp = slack_client.post_message(text, mention=mention)
        result = make_tool_result(
            ok=True,
            app="slack",
            action="post_receipt",
            external_id=resp.get("ts"),
            idempotency_key=idem_key,
            raw=resp,
        )
        return idempotency.put_cached(admin_id, idem_key, result)
    except Exception as exc:  # noqa: BLE001
        return make_tool_result(
            ok=False,
            app="slack",
            action="post_receipt",
            idempotency_key=idem_key,
            error=str(exc),
        )


def request_slack_approval(
    run_id: str,
    summary: str,
    *,
    admin_id: Optional[str] = None,
) -> str:
    """Post an approval request; returns approval_request_id (message ts or mock id).

    React with :white_check_mark: / :x: (or reply) — polling is left to Agent 1 /
    hitl.wait_slack_approval. On Slack failure, raises so caller can fall back to CLI.
    """
    idem_key = f"slack:{run_id}:approval"
    cached = idempotency.get_cached(admin_id, idem_key)
    if isinstance(cached, str):
        return cached

    text = (
        f":hand: Life OS HITL approval needed for run `{run_id}`\n"
        f"{summary}\n"
        f"React :white_check_mark: to approve or :x: to deny."
    )

    if use_mock_connectors():
        request_id = f"mock-approval-{run_id}"
        print(f"[mock:slack] approval_request id={request_id} summary={summary!r}")
        idempotency.put_cached(admin_id, idem_key, request_id)
        return request_id

    from life_os.adapters import slack_client

    mention = env("ADMIN_PRIMARY_SLACK")
    resp = slack_client.post_message(text, mention=mention)
    request_id = str(resp.get("ts") or resp.get("message", {}).get("ts"))
    idempotency.put_cached(admin_id, idem_key, request_id)
    return request_id
