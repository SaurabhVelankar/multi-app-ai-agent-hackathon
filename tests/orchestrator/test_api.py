"""Test FastAPI routes with mocked graph."""
import os

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from life_os.admins import reload_roster
from life_os.api import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def family_roster(monkeypatch):
    """A known 3-admin roster (owner/operator/viewer) for tests that need one."""
    monkeypatch.setenv("FAMILY_ID", "api_test_family")
    monkeypatch.setenv("ADMIN_MAX", "10")
    monkeypatch.setenv("HITL_POLICY", "any_of")
    monkeypatch.setenv("ADMIN_IDS", "owner_1,op_1,viewer_1")
    monkeypatch.setenv("OWNER_1_ROLE", "owner")
    monkeypatch.setenv("OP_1_ROLE", "operator")
    monkeypatch.setenv("VIEWER_1_ROLE", "viewer")
    reload_roster()
    yield
    for key in list(os.environ):
        if key.startswith(("ADMIN_", "OWNER_1_", "OP_1_", "VIEWER_1_")) or key in {
            "FAMILY_ID",
            "HITL_POLICY",
        }:
            monkeypatch.delenv(key, raising=False)
    reload_roster()


def _mock_state(status="pass", needs_approval=False):
    return {
        "run_id": "test-run-123",
        "thread_id": "test-run-123",
        "created_at": "2026-09-13T00:00:00Z",
        "admin_id": None,
        "trigger": {"type": "goal", "raw": "book a meeting", "source_id": None},
        "normalized_context": {},
        "intents": [{"id": "i1", "type": "meeting", "summary": "book meeting", "entities": {}, "confidence": 0.9}],
        "priority_scores": {},
        "selected_intent": None,
        "plan_steps": [],
        "calendar_actions": [],
        "drafts": [],
        "approvals": {},
        "tool_results": [],
        "execution_receipts": [],
        "errors": [],
        "retry_count": 0,
        "status": status,
        "needs_approval": needs_approval,
        "audit_ref": None,
    }


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_create_run(client):
    mock_snap = MagicMock()
    mock_snap.values = _mock_state()

    with patch("life_os.api.graph") as mock_graph:
        mock_graph.invoke.return_value = None
        mock_graph.get_state.return_value = mock_snap

        resp = client.post("/runs", json={
            "trigger_type": "goal",
            "trigger_payload": "Book a meeting with Sarah next week",
        })

    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data
    assert data["status"] == "pass"


def test_get_run_not_found(client):
    mock_snap = MagicMock()
    mock_snap.values = {}

    with patch("life_os.api.graph") as mock_graph:
        mock_graph.get_state.return_value = mock_snap
        resp = client.get("/runs/nonexistent-run-id")

    assert resp.status_code == 404


def test_get_run_found(client):
    mock_snap = MagicMock()
    mock_snap.values = _mock_state()

    with patch("life_os.api.graph") as mock_graph:
        mock_graph.get_state.return_value = mock_snap
        resp = client.get("/runs/test-run-123")

    assert resp.status_code == 200
    assert resp.json()["run_id"] == "test-run-123"


def test_approve_run_not_in_approval_state(client):
    mock_snap = MagicMock()
    mock_snap.values = _mock_state(status="pass", needs_approval=False)

    with patch("life_os.api.graph") as mock_graph:
        mock_graph.get_state.return_value = mock_snap
        resp = client.post("/runs/test-run-123/approve", json={
            "decision": "approve",
            "admin_id": "user1",
        })

    assert resp.status_code == 409


def test_approve_run_deny(client, family_roster):
    approval_state = _mock_state(status="needs_approval", needs_approval=True)
    final_state = _mock_state(status="abort", needs_approval=False)
    mock_snap_approval = MagicMock()
    mock_snap_approval.values = approval_state
    mock_snap_final = MagicMock()
    mock_snap_final.values = final_state

    with patch("life_os.api.graph") as mock_graph:
        mock_graph.get_state.side_effect = [mock_snap_approval, mock_snap_final]
        mock_graph.update_state.return_value = None
        resp = client.post("/runs/test-run-123/approve", json={
            "decision": "deny",
            "admin_id": "op_1",
        })

    assert resp.status_code == 200
    assert resp.json()["status"] == "abort"


def test_approve_run_unknown_admin_denied(client, family_roster):
    mock_snap = MagicMock()
    mock_snap.values = _mock_state(status="needs_approval", needs_approval=True)

    with patch("life_os.api.graph") as mock_graph:
        mock_graph.get_state.return_value = mock_snap
        resp = client.post("/runs/test-run-123/approve", json={
            "decision": "approve",
            "admin_id": "not_in_roster",
        })

    assert resp.status_code == 403


def test_approve_run_viewer_denied(client, family_roster):
    mock_snap = MagicMock()
    mock_snap.values = _mock_state(status="needs_approval", needs_approval=True)

    with patch("life_os.api.graph") as mock_graph:
        mock_graph.get_state.return_value = mock_snap
        resp = client.post("/runs/test-run-123/approve", json={
            "decision": "approve",
            "admin_id": "viewer_1",
        })

    assert resp.status_code == 403


def test_create_run_unknown_admin_rejected(client, family_roster):
    resp = client.post("/runs", json={
        "trigger_type": "goal",
        "trigger_payload": "test",
        "admin_id": "not_in_roster",
    })

    assert resp.status_code == 403


def test_admin_roster_limit(client, family_roster):
    # Roster already has 3 members; drop the cap to force "full" without
    # actually adding 10 more admins.
    with patch("life_os.api.get_roster") as mock_get_roster:
        from life_os.admins import get_roster as real_get_roster

        roster = real_get_roster()
        roster.admin_max = len(roster.admins)
        mock_get_roster.return_value = roster

        resp = client.post("/admins", json={
            "acting_admin_id": "owner_1",
            "admin_id": "overflow_admin",
            "name": "Overflow",
            "role": "operator",
        })

    assert resp.status_code == 400
    assert "full" in resp.json()["detail"].lower()


def test_idempotency(client, family_roster):
    mock_snap = MagicMock()
    mock_snap.values = _mock_state()

    with patch("life_os.api.graph") as mock_graph, \
         patch("life_os.api._source_to_run", {("owner_1", "src-001"): "existing-run-id"}):
        mock_graph.get_state.return_value = mock_snap

        resp = client.post("/runs", json={
            "trigger_type": "email",
            "trigger_payload": {"subject": "test"},
            "source_id": "src-001",
            "admin_id": "owner_1",
        })

    assert resp.status_code == 200
    # Should return existing run, invoke not called
    mock_graph.invoke.assert_not_called()
