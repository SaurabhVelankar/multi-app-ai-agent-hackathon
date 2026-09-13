"""Shared result types for connectors (Agent 2)."""

from __future__ import annotations

from typing import Any, Literal, Optional, TypedDict


AppName = Literal["calendar", "notion", "slack", "sheets", "gmail"]
ApprovalDecision = Literal["approve", "deny"]


class ToolResult(TypedDict, total=False):
    ok: bool
    app: AppName
    action: str
    external_id: Optional[str]
    idempotency_key: Optional[str]
    error: Optional[str]
    raw: Any
    proposed_only: Optional[bool]


class GmailDraft(TypedDict, total=False):
    draft_id: str
    thread_id: Optional[str]
    body: str
    run_id: str


def make_tool_result(
    *,
    ok: bool,
    app: AppName,
    action: str,
    external_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
    error: Optional[str] = None,
    raw: Any = None,
    proposed_only: Optional[bool] = None,
) -> ToolResult:
    result: ToolResult = {
        "ok": ok,
        "app": app,
        "action": action,
        "external_id": external_id,
        "idempotency_key": idempotency_key,
        "error": error,
        "raw": raw,
    }
    if proposed_only is not None:
        result["proposed_only"] = proposed_only
    return result
