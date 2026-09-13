"""Intake node — normalise trigger into intents[]."""
import json
import uuid
from langchain_core.messages import HumanMessage, SystemMessage

from life_os.llm import get_chat_model
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


def _content_to_text(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


def _parse_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(cleaned)


def intake_node(state: LifeState) -> dict:
    trigger = state.get("trigger", {})
    raw = trigger.get("raw", "")
    if isinstance(raw, dict):
        raw = json.dumps(raw, indent=2)

    llm = get_chat_model(temperature=0.2)
    response = llm.invoke([
        SystemMessage(content=_SYSTEM),
        HumanMessage(content=str(raw)),
    ])

    try:
        parsed = _parse_json(_content_to_text(response.content))
        intents = parsed.get("intents", [])
        normalized = parsed.get("normalized_context", {})
        for intent in intents:
            if "id" not in intent or not intent["id"]:
                intent["id"] = str(uuid.uuid4())
    except (json.JSONDecodeError, AttributeError, TypeError):
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
