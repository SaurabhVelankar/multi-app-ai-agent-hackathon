"""Scheduler node — Calendar writes (Agent 2). Calls tools only."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping


def scheduler_node(state: Mapping[str, Any]) -> dict[str, Any]:
    """Read plan_steps needing calendar; create or propose events.

    Expected state keys (Agent 1 LifeState subset):
      run_id, plan_steps[], admin_id?, calendar_actions?, tool_results?, errors?
    plan_step may include: requires_calendar, title, start, end, intent_id, create (bool), confidence
    """
    from life_os.tools.calendar import create_calendar_event

    run_id = str(state.get("run_id") or "unknown")
    admin_id = state.get("admin_id")
    plan_steps = list(state.get("plan_steps") or [])
    calendar_actions = list(state.get("calendar_actions") or [])
    tool_results = list(state.get("tool_results") or [])
    errors = list(state.get("errors") or [])

    cal_steps = [
        s
        for s in plan_steps
        if isinstance(s, dict)
        and (s.get("requires_calendar") or s.get("action") in {"create_event", "calendar"})
    ]

    if not cal_steps:
        return {
            "calendar_actions": calendar_actions,
            "tool_results": tool_results,
            "errors": errors,
            "calendar_skipped": True,
        }

    for step in cal_steps:
        intent_id = str(step.get("intent_id") or step.get("id") or "intent")
        idem = str(step.get("idempotency_key") or f"cal:{run_id}:{intent_id}")
        title = str(step.get("title") or step.get("summary") or "Life OS meeting")
        start = str(step.get("start") or step.get("start_iso") or "")
        end = str(step.get("end") or step.get("end_iso") or "")
        confidence = float(step.get("confidence") or state.get("priority_scores", {}).get(intent_id) or 1.0)
        create = bool(step.get("create", confidence >= 0.7))

        result = create_calendar_event(
            run_id,
            title,
            start,
            end,
            idem,
            admin_id=admin_id,
            create=create,
        )
        tool_results.append(result)
        action = {
            "intent_id": intent_id,
            "title": title,
            "start": start,
            "end": end,
            "external_id": result.get("external_id"),
            "proposed_only": result.get("proposed_only"),
            "ok": result.get("ok"),
        }
        calendar_actions.append(action)
        if not result.get("ok"):
            errors.append(
                {
                    "node": "scheduler",
                    "app": "calendar",
                    "error": result.get("error"),
                    "idempotency_key": idem,
                }
            )

    return {
        "calendar_actions": calendar_actions,
        "tool_results": tool_results,
        "errors": errors,
        "calendar_skipped": False,
    }


# LangGraph-friendly alias
def scheduler(state: MutableMapping[str, Any]) -> dict[str, Any]:
    return scheduler_node(state)
