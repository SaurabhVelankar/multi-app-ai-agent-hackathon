"""T6 — audit row carries family_id, approver, approval_assignee, oauth account."""
from __future__ import annotations

from unittest.mock import patch

from life_os.agents.auditor import auditor_node


def _state(**overrides) -> dict:
    base = {
        "run_id": "run-1",
        "family_id": "fam-1",
        "admin_id": "admin_01",
        "approval_assignee": "admin_02",
        "status": "pass",
        "tool_results": [],
        "errors": [],
        "calendar_actions": [],
        "drafts": [],
        "needs_approval": False,
    }
    base.update(overrides)
    return base


def test_audit_row_includes_family_and_approval_fields():
    captured = {}

    def _fake_append(run_id, row, *, admin_id=None):
        captured.update(row)
        return {"ok": True, "app": "sheets", "action": "append_row", "external_id": "row-1"}

    with patch("life_os.tools.sheets.append_sheets_audit", side_effect=_fake_append), \
         patch(
             "life_os.adapters.google_auth.oauth_status",
             return_value={"email": "parent-a@example.com"},
         ):
        auditor_node(_state())

    assert captured["family_id"] == "fam-1"
    assert captured["admin_id"] == "admin_01"
    assert captured["approver"] == "admin_02"
    assert captured["approval_assignee"] == "admin_02"
    assert captured["oauth_account"] == "parent-a@example.com"


def test_audit_row_oauth_account_missing_is_none():
    captured = {}

    def _fake_append(run_id, row, *, admin_id=None):
        captured.update(row)
        return {"ok": True, "app": "sheets", "action": "append_row", "external_id": "row-1"}

    with patch("life_os.tools.sheets.append_sheets_audit", side_effect=_fake_append), \
         patch(
             "life_os.adapters.google_auth.oauth_status",
             side_effect=RuntimeError("no token"),
         ):
        auditor_node(_state(admin_id="admin_03", approval_assignee=None))

    assert captured["oauth_account"] is None
    assert captured["approver"] is None
