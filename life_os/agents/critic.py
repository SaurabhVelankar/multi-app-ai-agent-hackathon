"""Critic node — gate approval; sets needs_approval / status. No SDK calls."""
from life_os.config import CONFIDENCE_THRESHOLD
from life_os.state import LifeState


def critic_node(state: LifeState) -> dict:
    intents = state.get("intents", [])
    plan_steps = state.get("plan_steps", [])
    errors = state.get("errors", [])

    # Hard abort: no intents or all steps blocked
    if not intents:
        return {"status": "abort", "needs_approval": False}

    if plan_steps and all(s.get("status") == "blocked" for s in plan_steps):
        return {"status": "abort", "needs_approval": False}

    # Check for irreversible steps
    has_hitl_step = any(s.get("requires_hitl") for s in plan_steps)

    # Check overall confidence
    selected = state.get("selected_intent")
    confidence = selected.get("confidence", 1.0) if selected else 1.0
    low_confidence = confidence < CONFIDENCE_THRESHOLD

    # Check for execution errors
    has_errors = bool(errors)

    needs_approval = has_hitl_step or low_confidence or has_errors

    if needs_approval:
        return {"status": "needs_approval", "needs_approval": True}

    return {"status": "pass", "needs_approval": False}
