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


def auditor_node(state: Mapping[str, Any]) -> dict[str, Any]:
    from life_os.tools.sheets import append_sheets_audit

    run_id = str(state.get("run_id") or "unknown")
    admin_id = state.get("admin_id")
    tool_results = list(state.get("tool_results") or [])
    errors = list(state.get("errors") or [])

    status = state.get("status") or "pass"
    if errors and status == "pass":
        status = "partial"

    row = {
        "run_id": run_id,
        "admin_id": admin_id,
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
