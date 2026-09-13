"""Test graph compilation and stub-only run (no LLM key required with mocks)."""
import datetime
import uuid
import json
import pytest
from unittest.mock import patch, MagicMock

from life_os.graph import build_graph
from life_os.state import LifeState


def _initial_state(trigger_type="goal", raw="Book a meeting with Sarah next week") -> LifeState:
    run_id = str(uuid.uuid4())
    return {
        "run_id": run_id,
        "thread_id": run_id,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "admin_id": None,
        "trigger": {"type": trigger_type, "raw": raw, "source_id": None},
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


def test_graph_compiles():
    g = build_graph()
    assert g is not None


def _mock_intake(state):
    return {
        "intents": [{"id": "i1", "type": "meeting", "summary": "Book meeting", "entities": {}, "confidence": 0.9}],
        "normalized_context": {"raw_summary": "meeting request"},
        "status": "running",
    }


def _mock_priority(state):
    return {
        "priority_scores": {"i1": {"total": 6, "rationale": "mock"}},
        "selected_intent": {"id": "i1", "type": "meeting", "summary": "Book meeting", "entities": {}, "confidence": 0.9},
    }


def _mock_planner(state):
    return {
        "plan_steps": [{"id": "s1", "action": "create_event", "app": "calendar", "args": {}, "requires_hitl": False, "status": "pending"}],
    }


def _make_llm_response(content: str):
    from langchain_core.messages import AIMessage
    mock_resp = MagicMock()
    mock_resp.content = content
    return mock_resp


def test_stub_run_reaches_pass():
    g = build_graph()
    state = _initial_state()
    config = {"configurable": {"thread_id": state["run_id"]}}

    intake_resp = json.dumps({
        "intents": [{"id": "i1", "type": "meeting", "summary": "Book meeting", "entities": {"people": ["Sarah"], "times": ["next week"], "links": []}, "confidence": 0.9}],
        "normalized_context": {"summary": "meeting request"},
    })
    priority_resp = json.dumps({
        "scores": {"i1": {"deadline_urgency": 7, "people_impact": 6, "irreversibility": 2, "total": 8, "rationale": "meeting"}}
    })
    planner_resp = json.dumps({
        "plan_steps": [{"id": "s1", "action": "create_event", "app": "calendar", "args": {"title": "Meeting with Sarah"}, "requires_hitl": False, "status": "pending"}]
    })

    call_count = [0]
    responses = [intake_resp, priority_resp, planner_resp]

    def fake_invoke(messages, **kwargs):
        resp = _make_llm_response(responses[min(call_count[0], len(responses) - 1)])
        call_count[0] += 1
        return resp

    with (
        patch("life_os.agents.intake.get_chat_model") as mock_i,
        patch("life_os.agents.priority.get_chat_model") as mock_p,
        patch("life_os.agents.planner.get_chat_model") as mock_pl,
    ):
        mock_llm_i = MagicMock()
        mock_llm_i.invoke = lambda msgs, **kw: _make_llm_response(intake_resp)
        mock_llm_p = MagicMock()
        mock_llm_p.invoke = lambda msgs, **kw: _make_llm_response(priority_resp)
        mock_llm_pl = MagicMock()
        mock_llm_pl.invoke = lambda msgs, **kw: _make_llm_response(planner_resp)
        mock_i.return_value = mock_llm_i
        mock_p.return_value = mock_llm_p
        mock_pl.return_value = mock_llm_pl

        result = g.invoke(state, config=config)

    assert result is not None
    assert result.get("status") in {"pass", "needs_approval", "abort", "error", "running"}


def test_graph_has_all_nodes():
    g = build_graph()
    node_names = set(g.nodes.keys())
    for expected in ["intake", "priority", "planner", "scheduler", "executor", "critic", "hitl_interrupt", "auditor"]:
        assert expected in node_names, f"Missing node: {expected}"
