"""Planner node — convert selected_intent into ordered plan_steps[]."""
import json
import uuid
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from life_os.config import LLM_MODEL, ANTHROPIC_API_KEY
from life_os.state import LifeState


_SYSTEM = """You are a planning agent for a personal life-OS.
Given a selected intent and its context, produce ordered plan_steps.

Return ONLY valid JSON (no markdown):
{
  "plan_steps": [
    {
      "id": "<uuid>",
      "action": "<create_event|create_notion|draft_email|send_email|notify_slack|info_only>",
      "app": "<calendar|notion|gmail|slack|none>",
      "args": {},
      "requires_hitl": <true|false>,
      "status": "pending"
    }
  ]
}

Rules:
- send_email always requires_hitl = true (irreversible).
- draft_email requires_hitl = false (reversible draft).
- notify_slack requires_hitl = false.
- create_event and create_notion require_hitl = false unless explicitly ambiguous.
- Keep steps minimal — only what the intent requires.
"""


def planner_node(state: LifeState) -> dict:
    selected = state.get("selected_intent")
    if not selected:
        return {"plan_steps": []}

    context = {
        "intent": selected,
        "normalized_context": state.get("normalized_context", {}),
    }

    try:
        llm = ChatAnthropic(model=LLM_MODEL, api_key=ANTHROPIC_API_KEY, temperature=0.1)
        response = llm.invoke([
            SystemMessage(content=_SYSTEM),
            HumanMessage(content=json.dumps(context)),
        ])
        parsed = json.loads(response.content)
        steps = parsed.get("plan_steps", [])
        for step in steps:
            if "id" not in step or not step["id"]:
                step["id"] = str(uuid.uuid4())
            step.setdefault("status", "pending")
    except Exception as exc:
        steps = [{
            "id": str(uuid.uuid4()),
            "action": "info_only",
            "app": "none",
            "args": {"error": str(exc)},
            "requires_hitl": False,
            "status": "blocked",
        }]

    return {"plan_steps": steps}
