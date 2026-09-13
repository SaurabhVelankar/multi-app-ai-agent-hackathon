"""Intake node — normalise trigger into intents[]."""
import json
import uuid
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from life_os.config import LLM_MODEL, ANTHROPIC_API_KEY
from life_os.state import LifeState


_SYSTEM = """You are an intake agent for a personal life-OS.
Parse the user's trigger (a goal string or an email JSON) and extract a list of intents.

Return ONLY valid JSON matching this schema (no markdown fences):
{
  "intents": [
    {
      "id": "<uuid>",
      "type": "<meeting|task|follow_up|info>",
      "summary": "<one sentence>",
      "entities": {
        "people": [],
        "times": [],
        "links": []
      },
      "confidence": <0.0-1.0>
    }
  ],
  "normalized_context": {}
}

Rules:
- Do NOT invent meetings or tasks that are not implied by the input.
- If you cannot parse the input, return a single intent of type "info" with confidence < 0.4.
- One intent per distinct action required.
"""


def _build_llm():
    return ChatAnthropic(model=LLM_MODEL, api_key=ANTHROPIC_API_KEY, temperature=0.2)


def intake_node(state: LifeState) -> dict:
    trigger = state.get("trigger", {})
    raw = trigger.get("raw", "")
    if isinstance(raw, dict):
        raw = json.dumps(raw, indent=2)

    llm = _build_llm()
    response = llm.invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=str(raw)),
    ])

    try:
        parsed = json.loads(response.content)
        intents = parsed.get("intents", [])
        normalized = parsed.get("normalized_context", {})
        for intent in intents:
            if "id" not in intent or not intent["id"]:
                intent["id"] = str(uuid.uuid4())
    except (json.JSONDecodeError, AttributeError):
        intents = [{
            "id": str(uuid.uuid4()),
            "type": "info",
            "summary": "Could not parse trigger",
            "entities": {"people": [], "times": [], "links": []},
            "confidence": 0.2,
        }]
        normalized = {}

    return {
        "intents": intents,
        "normalized_context": normalized,
        "status": "running",
    }
