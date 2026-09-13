"""Test FastAPI routes with mocked graph."""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from life_os.api import app


@pytest.fixture
def client():
    return TestClient(app)


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


def test_approve_run_deny(client):
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
            "admin_id": "user1",
        })

    assert resp.status_code == 200
    assert resp.json()["status"] == "abort"


def test_admin_roster_limit(client):
    mock_snap = MagicMock()
    mock_snap.values = _mock_state()

    with patch("life_os.api.graph") as mock_graph, \
         patch("life_os.api._admin_roster", {f"user{i}": "ts" for i in range(10)}):
        mock_graph.invoke.return_value = None
        mock_graph.get_state.return_value = mock_snap

        resp = client.post("/runs", json={
            "trigger_type": "goal",
            "trigger_payload": "test",
            "admin_id": "user_new",
        })

    assert resp.status_code == 400
    assert "full" in resp.json()["detail"].lower()


def test_idempotency(client):
    mock_snap = MagicMock()
    mock_snap.values = _mock_state()

    with patch("life_os.api.graph") as mock_graph, \
         patch("life_os.api._source_to_run", {"src-001": "existing-run-id"}):
        mock_graph.get_state.return_value = mock_snap

        resp = client.post("/runs", json={
            "trigger_type": "email",
            "trigger_payload": {"subject": "test"},
            "source_id": "src-001",
        })

    assert resp.status_code == 200
    # Should return existing run, invoke not called
    mock_graph.invoke.assert_not_called()
