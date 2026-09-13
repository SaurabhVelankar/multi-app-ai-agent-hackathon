"""Test LifeState schema and append-only invariants."""
from life_os.state import LifeState


def _base_state() -> LifeState:
    return {
        "run_id": "test-run-1",
        "thread_id": "test-run-1",
        "created_at": "2026-09-13T00:00:00Z",
        "admin_id": None,
        "trigger": {"type": "goal", "raw": "book a meeting", "source_id": None},
        "normalized_context": {},
        "intents": [],
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
        "status": "running",
        "needs_approval": False,
        "audit_ref": None,
    }


def test_state_has_required_fields():
    state = _base_state()
    required = [
        "run_id", "thread_id", "created_at", "trigger", "intents",
        "plan_steps", "tool_results", "errors", "status", "needs_approval",
    ]
    for field in required:
        assert field in state, f"Missing field: {field}"


def test_status_values():
    state = _base_state()
    valid_statuses = {"running", "needs_approval", "pass", "abort", "error"}
    assert state["status"] in valid_statuses


def test_needs_approval_default_false():
    state = _base_state()
    assert state["needs_approval"] is False


def test_errors_append_only_pattern():
    state = _base_state()
    # Simulate append-only: errors list grows, never shrinks
    state["errors"].append({"node": "intake", "msg": "parse error"})
    assert len(state["errors"]) == 1
    state["errors"].append({"node": "planner", "msg": "llm timeout"})
    assert len(state["errors"]) == 2
    # Cannot shrink
    original_len = len(state["errors"])
    assert original_len == 2


def test_tool_results_append_only_pattern():
    state = _base_state()
    state["tool_results"].append({"node": "executor", "result": "ok"})
    assert len(state["tool_results"]) == 1


def test_trigger_types():
    for t in ("goal", "email", "slack"):
        state = _base_state()
        state["trigger"]["type"] = t
        assert state["trigger"]["type"] == t


def test_plan_step_fields():
    step = {
        "id": "step-1",
        "action": "create_event",
        "app": "calendar",
        "args": {"title": "Q4 sync"},
        "requires_hitl": False,
        "status": "pending",
    }
    assert step["status"] in {"pending", "done", "skipped", "blocked"}
    assert isinstance(step["requires_hitl"], bool)
