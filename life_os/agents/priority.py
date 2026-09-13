"""Priority node — rank intents and select one for Tier-0 demo path."""
import json
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from life_os.config import LLM_MODEL, ANTHROPIC_API_KEY
from life_os.state import LifeState


_WEIGHTS = {
    "meeting": {"deadline": 3, "people": 2, "irreversibility": 1},
    "task": {"deadline": 2, "people": 1, "irreversibility": 1},
    "follow_up": {"deadline": 1, "people": 2, "irreversibility": 2},
    "info": {"deadline": 0, "people": 0, "irreversibility": 0},
}

_SYSTEM = """You are a priority-scoring assistant.
Given a list of intents, score each one (0-10) on three axes: deadline_urgency, people_impact, irreversibility.
Return ONLY valid JSON (no markdown):
{
  "scores": {
    "<intent_id>": {
      "deadline_urgency": <0-10>,
      "people_impact": <0-10>,
      "irreversibility": <0-10>,
      "total": <weighted sum>,
      "rationale": "<one sentence>"
    }
  }
}
"""


def _deterministic_score(intent: dict) -> float:
    w = _WEIGHTS.get(intent.get("type", "info"), _WEIGHTS["info"])
    conf = intent.get("confidence", 0.5)
    return (w["deadline"] + w["people"] + w["irreversibility"]) * conf


def priority_node(state: LifeState) -> dict:
    intents = state.get("intents", [])
    if not intents:
        return {"priority_scores": {}, "selected_intent": None}

    # Deterministic pre-scores
    pre_scores = {i["id"]: _deterministic_score(i) for i in intents}

    # LLM tie-break when >1 intent
    priority_scores: dict = {}
    if len(intents) > 1:
        try:
            llm = ChatAnthropic(model=LLM_MODEL, api_key=ANTHROPIC_API_KEY, temperature=0)
            response = llm.invoke([
                SystemMessage(content=_SYSTEM),
                HumanMessage(content=json.dumps({"intents": intents})),
            ])
            parsed = json.loads(response.content)
            priority_scores = parsed.get("scores", {})
        except Exception:
            pass

    # Fall back to deterministic if LLM failed
    for intent in intents:
        iid = intent["id"]
        if iid not in priority_scores:
            priority_scores[iid] = {
                "deadline_urgency": pre_scores[iid],
                "people_impact": 0,
                "irreversibility": 0,
                "total": pre_scores[iid],
                "rationale": "deterministic fallback",
            }

    best_id = max(priority_scores, key=lambda k: priority_scores[k].get("total", 0))
    selected = next((i for i in intents if i["id"] == best_id), intents[0])

    return {
        "priority_scores": priority_scores,
        "selected_intent": selected,
    }
