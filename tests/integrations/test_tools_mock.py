"""Integration tests — mock connectors (Agent 2)."""

from __future__ import annotations

import os

import pytest

# Force mock before importing tools
os.environ["LIFE_OS_USE_MOCK_CONNECTORS"] = "1"
os.environ["LIFE_OS_HITL_AUTO"] = "approve"

from life_os import idempotency
from life_os.agents.auditor import auditor_node
from life_os.agents.executor import executor_node
from life_os.agents.scheduler import scheduler_node
from life_os.hitl import request_approval, wait_cli_approval
from life_os.tools.calendar import create_calendar_event
from life_os.tools.gmail import draft_gmail_reply, send_gmail
from life_os.tools.notion import create_notion_page
from life_os.tools.sheets import append_sheets_audit
from life_os.tools.slack import post_slack_receipt, request_slack_approval


@pytest.fixture(autouse=True)
def _clear_idempotency():
    idempotency.clear()
    yield
    idempotency.clear()


def test_calendar_mock_and_idempotent():
    a = create_calendar_event(
        "run1",
        "Sync",
        "2026-09-14T15:00:00Z",
        "2026-09-14T15:30:00Z",
        "cal:run1:i1",
    )
    b = create_calendar_event(
        "run1",
        "Sync",
        "2026-09-14T15:00:00Z",
        "2026-09-14T15:30:00Z",
        "cal:run1:i1",
    )
    assert a["ok"] is True
    assert a["external_id"] == b["external_id"]
    assert a["app"] == "calendar"


def test_calendar_propose_only():
    r = create_calendar_event(
        "run2",
        "Maybe",
        "2026-09-14T16:00:00Z",
        "2026-09-14T16:30:00Z",
        "cal:run2:i1",
        create=False,
    )
    assert r["ok"] is True
    assert r.get("proposed_only") is True
    assert r["external_id"] is None


def test_notion_slack_sheets_gmail_mock():
    n = create_notion_page("run3", "Brief", "body", "notion:run3:i1")
    s = post_slack_receipt("run3", "done")
    sh = append_sheets_audit("run3", {"status": "pass", "apps": ["notion", "slack"]})
    d = draft_gmail_reply("run3", "thread-1", "Thanks")
    assert n["ok"] and s["ok"] and sh["ok"]
    assert d["draft_id"].startswith("mock-draft-")
    sent = send_gmail("run3", d["draft_id"])
    assert sent["ok"] is True


def test_slack_approval_request_id():
    rid = request_slack_approval("run4", "Send email?")
    assert rid.startswith("mock-approval-")


def test_cli_hitl_auto():
    assert wait_cli_approval("run5", "summary") == "approve"
    os.environ["LIFE_OS_HITL_AUTO"] = "deny"
    assert wait_cli_approval("run5b", "summary") == "deny"
    os.environ["LIFE_OS_HITL_AUTO"] = "approve"


def test_request_approval_cli_path():
    assert request_approval("run6", "summary", prefer="cli") == "approve"


def test_scheduler_executor_auditor_happy_path():
    state = {
        "run_id": "demo-run",
        "admin_id": "admin_01",
        "plan_steps": [
            {
                "requires_calendar": True,
                "intent_id": "m1",
                "title": "Demo meeting",
                "start": "2026-09-14T17:00:00Z",
                "end": "2026-09-14T17:30:00Z",
                "confidence": 0.9,
            },
            {"action": "notion_page", "title": "Demo brief", "body": "Notes"},
            {"action": "slack_receipt", "text": "Demo receipt"},
            {"action": "gmail_draft", "body": "Looking forward"},
        ],
        "tool_results": [],
        "errors": [],
        "calendar_actions": [],
        "drafts": [],
        "status": "pass",
    }
    state.update(scheduler_node(state))
    state.update(executor_node(state))
    state.update(auditor_node(state))

    apps = {tr["app"] for tr in state["tool_results"] if tr.get("ok")}
    assert "calendar" in apps
    assert "notion" in apps
    assert "slack" in apps
    assert "sheets" in apps
    assert state.get("audit_ref")
    assert state["drafts"]
    assert state["errors"] == []


def test_send_blocked_on_error_draft():
    r = send_gmail("run7", "error-draft-run7")
    assert r["ok"] is False
