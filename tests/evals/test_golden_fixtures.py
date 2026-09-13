"""Golden-fixture evals — ≥3 fixtures with assertable side effects (EVALS.md / PRD F2.3)."""

from __future__ import annotations

import os

import pytest

os.environ["LIFE_OS_USE_MOCK_CONNECTORS"] = "1"
os.environ.setdefault("LIFE_OS_HITL_AUTO", "approve")

from life_os.evals import apps_ok, has_gmail_send, run_eval


def test_meeting_email_writes_calendar_notion_slack_sheets():
    """Happy path: clear meeting → calendar + notion + slack + sheets audit; no gmail send."""
    result = run_eval(
        "meeting_email.json",
        intake_json={
            "intents": [
                {
                    "id": "i1",
                    "type": "meeting",
                    "summary": "Q4 planning sync with Sarah",
                    "entities": {
                        "people": ["Sarah"],
                        "times": ["Monday or Tuesday afternoon"],
                        "links": [],
                    },
                    "confidence": 0.92,
                }
            ],
            "normalized_context": {"summary": "meeting + project brief"},
        },
        priority_json={
            "scores": {
                "i1": {
                    "deadline_urgency": 7,
                    "people_impact": 6,
                    "irreversibility": 2,
                    "total": 8,
                    "rationale": "clear meeting ask",
                }
            }
        },
        planner_json={
            "plan_steps": [
                {
                    "id": "s1",
                    "action": "create_event",
                    "app": "calendar",
                    "args": {
                        "title": "Q4 planning sync",
                        "start": "2026-09-15T15:00:00Z",
                        "end": "2026-09-15T15:30:00Z",
                    },
                    "requires_hitl": False,
                    "status": "pending",
                },
                {
                    "id": "s2",
                    "action": "create_notion",
                    "app": "notion",
                    "args": {"title": "Q4 project brief"},
                    "requires_hitl": False,
                    "status": "pending",
                },
                {
                    "id": "s3",
                    "action": "notify_slack",
                    "app": "slack",
                    "args": {"text": "Booked Q4 sync"},
                    "requires_hitl": False,
                    "status": "pending",
                },
                {
                    "id": "s4",
                    "action": "draft_email",
                    "app": "gmail",
                    "args": {"body": "Sounds good — I'll send an invite."},
                    "requires_hitl": False,
                    "status": "pending",
                },
            ]
        },
    )

    apps = apps_ok(result)
    assert "calendar" in apps
    assert "notion" in apps
    assert "slack" in apps
    assert "sheets" in apps
    assert result.get("audit_ref")
    assert result.get("drafts"), "Gmail draft should be staged"
    assert not has_gmail_send(result), "Must never auto-send email"
    assert result.get("status") in {"pass", "needs_approval"}
    assert result.get("errors") == [] or result.get("status") == "pass"


def test_goal_simple_notion_and_audit():
    """Goal path: follow-up + Notion summary side effects + audit row."""
    result = run_eval(
        "goal_simple.json",
        intake_json={
            "intents": [
                {
                    "id": "i1",
                    "type": "follow_up",
                    "summary": "Schedule follow-up and Notion summary",
                    "entities": {"people": ["team"], "times": ["next week"], "links": []},
                    "confidence": 0.88,
                }
            ],
            "normalized_context": {"summary": "sprint follow-up"},
        },
        priority_json={
            "scores": {
                "i1": {
                    "deadline_urgency": 5,
                    "people_impact": 5,
                    "irreversibility": 1,
                    "total": 6,
                    "rationale": "follow-up",
                }
            }
        },
        planner_json={
            "plan_steps": [
                {
                    "id": "s1",
                    "action": "create_event",
                    "app": "calendar",
                    "args": {
                        "title": "Sprint follow-up",
                        "start": "2026-09-16T16:00:00Z",
                        "end": "2026-09-16T16:30:00Z",
                    },
                    "requires_hitl": False,
                    "status": "pending",
                },
                {
                    "id": "s2",
                    "action": "create_notion",
                    "app": "notion",
                    "args": {"title": "Sprint summary"},
                    "requires_hitl": False,
                    "status": "pending",
                },
                {
                    "id": "s3",
                    "action": "notify_slack",
                    "app": "slack",
                    "args": {},
                    "requires_hitl": False,
                    "status": "pending",
                },
            ]
        },
    )

    apps = apps_ok(result)
    assert "notion" in apps
    assert "sheets" in apps
    assert result.get("audit_ref")
    assert not has_gmail_send(result)
    assert result.get("status") in {"pass", "needs_approval"}


def test_ambiguous_email_requires_hitl_no_send():
    """Low confidence / irreversible plan → needs_approval; never gmail send."""
    result = run_eval(
        "ambiguous_email.json",
        intake_json={
            "intents": [
                {
                    "id": "i1",
                    "type": "follow_up",
                    "summary": "Unclear: meeting vs email the team",
                    "entities": {"people": ["Alex", "team"], "times": [], "links": []},
                    "confidence": 0.35,
                }
            ],
            "normalized_context": {"summary": "ambiguous ask"},
        },
        priority_json={
            "scores": {
                "i1": {
                    "deadline_urgency": 3,
                    "people_impact": 4,
                    "irreversibility": 8,
                    "total": 5,
                    "rationale": "ambiguous irreversible email",
                }
            }
        },
        planner_json={
            "plan_steps": [
                {
                    "id": "s1",
                    "action": "send_email",
                    "app": "gmail",
                    "args": {"body": "Delaying the launch"},
                    "requires_hitl": True,
                    "status": "pending",
                },
                {
                    "id": "s2",
                    "action": "draft_email",
                    "app": "gmail",
                    "args": {},
                    "requires_hitl": False,
                    "status": "pending",
                },
            ]
        },
    )

    assert result.get("needs_approval") is True
    assert result.get("status") == "needs_approval"
    assert not has_gmail_send(result)
    # Interrupted before auditor when HITL — audit_ref may be absent until resume


def test_newsletter_not_meeting_no_calendar_still_audits():
    """FYI newsletter → info_only, no calendar write; clean terminal + audit when pass."""
    result = run_eval(
        "newsletter_not_meeting.json",
        intake_json={
            "intents": [
                {
                    "id": "i1",
                    "type": "info",
                    "summary": "Product newsletter FYI — no action",
                    "entities": {"people": [], "times": [], "links": []},
                    "confidence": 0.9,
                }
            ],
            "normalized_context": {"summary": "newsletter"},
        },
        priority_json={
            "scores": {
                "i1": {
                    "deadline_urgency": 0,
                    "people_impact": 0,
                    "irreversibility": 0,
                    "total": 0,
                    "rationale": "info only",
                }
            }
        },
        planner_json={
            "plan_steps": [
                {
                    "id": "s1",
                    "action": "info_only",
                    "app": "none",
                    "args": {},
                    "requires_hitl": False,
                    "status": "pending",
                }
            ]
        },
    )

    apps = apps_ok(result)
    assert "calendar" not in apps
    assert not has_gmail_send(result)
    assert result.get("status") in {"pass", "abort"}
    # High-confidence info_only should reach auditor
    if result.get("status") == "pass":
        assert result.get("audit_ref")
        assert "sheets" in apps


def test_at_least_three_golden_fixtures_exist():
    from pathlib import Path

    fixtures = Path(__file__).resolve().parents[2] / "life_os" / "fixtures"
    names = {p.name for p in fixtures.glob("*.json")}
    required = {
        "meeting_email.json",
        "goal_simple.json",
        "ambiguous_email.json",
        "newsletter_not_meeting.json",
    }
    assert required <= names
    assert len(names) >= 3
