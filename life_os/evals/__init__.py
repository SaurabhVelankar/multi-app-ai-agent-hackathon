"""Golden-fixture eval harness (see EVALS.md).

Runs the LangGraph pipeline in mock-connector mode with canned LLM responses,
then asserts on side effects in LifeState.
"""

from __future__ import annotations

import datetime
import json
import uuid
from pathlib import Path
from typing import Any, Callable, Optional
from unittest.mock import MagicMock, patch

from life_os.state import LifeState

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    path = FIXTURES_DIR / name
    if not path.exists():
        path = Path(name)
    return json.loads(path.read_text())


def fixture_to_trigger(fixture: dict[str, Any]) -> dict[str, Any]:
    ftype = fixture.get("type", "goal")
    if ftype == "email":
        raw = fixture
        source_id = fixture.get("fixture_id") or fixture.get("message_id")
    else:
        raw = fixture.get("goal", json.dumps(fixture))
        source_id = fixture.get("fixture_id")
    return {"type": ftype, "raw": raw, "source_id": source_id}


def initial_state_from_fixture(
    fixture: dict[str, Any],
    *,
    admin_id: str = "admin_01",
    family_id: str = "eval_family",
) -> LifeState:
    run_id = str(uuid.uuid4())
    trigger = fixture_to_trigger(fixture)
    return {
        "run_id": run_id,
        "thread_id": run_id,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "family_id": family_id,
        "admin_id": admin_id,
        "shared_with": [admin_id],
        "approval_assignee": None,
        "trigger": trigger,
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


def _ai(content: str) -> MagicMock:
    mock = MagicMock()
    mock.content = content
    return mock


def apps_ok(state: dict[str, Any]) -> set[str]:
    return {
        str(tr["app"])
        for tr in (state.get("tool_results") or [])
        if isinstance(tr, dict) and tr.get("ok") and tr.get("app")
    }


def has_gmail_send(state: dict[str, Any]) -> bool:
    for tr in state.get("tool_results") or []:
        if isinstance(tr, dict) and tr.get("app") == "gmail" and tr.get("action") == "send":
            return True
    return False


def run_eval(
    fixture_name: str,
    *,
    intake_json: dict[str, Any],
    priority_json: dict[str, Any],
    planner_json: dict[str, Any],
    admin_id: str = "admin_01",
) -> dict[str, Any]:
    """Invoke the real compiled graph with mocked LLMs + mock connectors."""
    import os

    os.environ.setdefault("LIFE_OS_USE_MOCK_CONNECTORS", "1")
    os.environ.setdefault("LIFE_OS_HITL_AUTO", "approve")

    from life_os import idempotency
    from life_os.graph import build_graph

    idempotency.clear()
    fixture = load_fixture(fixture_name)
    state = initial_state_from_fixture(fixture, admin_id=admin_id)
    config = {"configurable": {"thread_id": state["run_id"]}}

    intake_s = json.dumps(intake_json)
    priority_s = json.dumps(priority_json)
    planner_s = json.dumps(planner_json)

    g = build_graph()

    def _mk(content: str):
        def factory(*, temperature: float = 0.2):
            mock = MagicMock()
            mock.invoke = lambda msgs, **kw: _ai(content)
            return mock

        return factory

    with (
        patch("life_os.agents.intake.get_chat_model", side_effect=_mk(intake_s)),
        patch("life_os.agents.priority.get_chat_model", side_effect=_mk(priority_s)),
        patch("life_os.agents.planner.get_chat_model", side_effect=_mk(planner_s)),
    ):
        result = g.invoke(state, config=config)

    # LangGraph may return state dict directly
    if hasattr(result, "values") and isinstance(result.values, dict):
        return dict(result.values)
    return dict(result)
