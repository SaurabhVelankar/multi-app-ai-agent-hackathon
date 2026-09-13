"""Auditor node — always append Sheets audit row (Agent 2)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, MutableMapping


def _apps_touched(state: Mapping[str, Any]) -> list[str]:
    apps: list[str] = []
    for tr in state.get("tool_results") or []:
        if isinstance(tr, dict) and tr.get("app") and tr.get("ok"):
            app = str(tr["app"])
            if app not in apps:
                apps.append(app)
    return apps


def _oauth_account(admin_id: Any) -> str | None:
    if not admin_id:
        return None
    try:
        from life_os.adapters import google_auth

        return google_auth.oauth_status(str(admin_id)).get("email")
    except Exception:  # noqa: BLE001
        return None


def auditor_node(state: Mapping[str, Any]) -> dict[str, Any]:
    from life_os.tools.sheets import append_sheets_audit

    run_id = str(state.get("run_id") or "unknown")
    admin_id = state.get("admin_id")
    tool_results = list(state.get("tool_results") or [])
    errors = list(state.get("errors") or [])

    status = state.get("status") or "pass"
    if errors and status == "pass":
        status = "partial"

    # Today the API sets approval_assignee to the acting approver's admin_id
    # once a decision lands, so "approver" mirrors it; kept as separate audit
    # columns so a future split (assigned target vs. who actually approved)
    # doesn't require a schema change.
    approval_assignee = state.get("approval_assignee")

    row = {
        "run_id": run_id,
        "family_id": state.get("family_id"),
        "admin_id": admin_id,
        "approver": approval_assignee,
        "approval_assignee": approval_assignee,
        "oauth_account": _oauth_account(admin_id),
        "status": status,
        "apps_touched": _apps_touched(state),
        "errors": errors,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "calendar_actions": state.get("calendar_actions") or [],
        "drafts_count": len(state.get("drafts") or []),
        "needs_approval": state.get("needs_approval"),
    }

    result = append_sheets_audit(run_id, row, admin_id=admin_id)
    tool_results.append(result)
    if not result.get("ok"):
        errors.append(
            {
                "node": "auditor",
                "app": "sheets",
                "error": result.get("error"),
            }
        )

    return {
        "tool_results": tool_results,
        "errors": errors,
        "audit_ref": result.get("external_id"),
        "status": status,
    }


def auditor(state: MutableMapping[str, Any]) -> dict[str, Any]:
    return auditor_node(state)
