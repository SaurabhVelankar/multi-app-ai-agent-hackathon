"""Test Critic node routing logic (no LLM calls needed)."""
import pytest
from unittest.mock import patch
from life_os.agents.critic import critic_node


def _state(**overrides):
    base = {
        "run_id": "test-run",
        "intents": [{"id": "i1", "type": "meeting", "summary": "Q4 sync", "entities": {}, "confidence": 0.9}],
        "plan_steps": [{"id": "s1", "action": "create_event", "app": "calendar", "args": {}, "requires_hitl": False, "status": "pending"}],
        "selected_intent": {"id": "i1", "confidence": 0.9},
        "errors": [],
        "status": "running",
        "needs_approval": False,
    }
    base.update(overrides)
    return base


def test_pass_on_high_confidence_no_hitl():
    result = critic_node(_state())
    assert result["status"] == "pass"
    assert result["needs_approval"] is False


def test_needs_approval_when_hitl_step():
    state = _state(plan_steps=[
        {"id": "s1", "action": "send_email", "app": "gmail", "args": {}, "requires_hitl": True, "status": "pending"}
    ])
    result = critic_node(state)
    assert result["status"] == "needs_approval"
    assert result["needs_approval"] is True


def test_needs_approval_on_low_confidence():
    state = _state(
        selected_intent={"id": "i1", "confidence": 0.3},
        intents=[{"id": "i1", "type": "info", "summary": "unclear", "entities": {}, "confidence": 0.3}],
    )
    result = critic_node(state)
    assert result["status"] == "needs_approval"
    assert result["needs_approval"] is True


def test_needs_approval_on_errors():
    state = _state(errors=[{"node": "executor", "msg": "timeout"}])
    result = critic_node(state)
    assert result["status"] == "needs_approval"
    assert result["needs_approval"] is True


def test_abort_on_no_intents():
    state = _state(intents=[])
    result = critic_node(state)
    assert result["status"] == "abort"
    assert result["needs_approval"] is False


def test_abort_on_all_blocked_steps():
    state = _state(plan_steps=[
        {"id": "s1", "action": "create_event", "app": "calendar", "args": {}, "requires_hitl": False, "status": "blocked"}
    ])
    result = critic_node(state)
    assert result["status"] == "abort"
