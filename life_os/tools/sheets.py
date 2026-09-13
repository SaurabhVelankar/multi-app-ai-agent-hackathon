"""Sheets tool — audit append."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from life_os import idempotency
from life_os.tools._common import env, use_mock_connectors
from life_os.types import ToolResult, make_tool_result


def _flatten_row(run_id: str, life_state_row: Mapping[str, Any], admin_id: Optional[str]) -> list[str]:
    ts = life_state_row.get("timestamp") or datetime.now(timezone.utc).isoformat()
    status = str(life_state_row.get("status", ""))
    apps = life_state_row.get("apps_touched") or life_state_row.get("apps") or []
    if isinstance(apps, list):
        apps_s = ",".join(str(a) for a in apps)
    else:
        apps_s = str(apps)
    errors = life_state_row.get("errors") or []
    errors_s = json.dumps(errors) if not isinstance(errors, str) else errors
    return [
        run_id,
        str(admin_id or life_state_row.get("admin_id") or ""),
        status,
        apps_s,
        errors_s,
        str(ts),
        json.dumps({k: v for k, v in life_state_row.items() if k not in {"errors"}}, default=str)[:2000],
    ]


def append_sheets_audit(
    run_id: str,
    life_state_row: dict,
    *,
    admin_id: Optional[str] = None,
) -> ToolResult:
    idem_key = f"sheets:{run_id}:audit"
    # Tier 0: still allow re-append on purpose for demos; cache only exact same payload hash
    # Plan says best-effort — we cache successful append so identical re-calls no-op.
    cached = idempotency.get_cached(admin_id, idem_key)
    if cached is not None:
        return cached

    row = _flatten_row(run_id, life_state_row, admin_id)

    if use_mock_connectors():
        fake_id = f"mock-sheets-row-{run_id}"
        print(f"[mock:sheets] append_audit row={row}")
        result = make_tool_result(
            ok=True,
            app="sheets",
            action="append_row",
            external_id=fake_id,
            idempotency_key=idem_key,
            raw={"mock": True, "row": row},
        )
        return idempotency.put_cached(admin_id, idem_key, result)

    try:
        from life_os.adapters import google_auth

        spreadsheet_id = env("SHEETS_SPREADSHEET_ID")
        if not spreadsheet_id:
            raise RuntimeError("SHEETS_SPREADSHEET_ID missing")
        range_name = env("SHEETS_AUDIT_RANGE", "Audit!A:Z") or "Audit!A:Z"
        service = google_auth.build_service("sheets", "v4")
        body = {"values": [row]}
        resp = (
            service.spreadsheets()
            .values()
            .append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body,
            )
            .execute()
        )
        updates = resp.get("updates") or {}
        result = make_tool_result(
            ok=True,
            app="sheets",
            action="append_row",
            external_id=updates.get("updatedRange") or run_id,
            idempotency_key=idem_key,
            raw=resp,
        )
        return idempotency.put_cached(admin_id, idem_key, result)
    except Exception as exc:  # noqa: BLE001
        return make_tool_result(
            ok=False,
            app="sheets",
            action="append_row",
            idempotency_key=idem_key,
            error=str(exc),
        )
