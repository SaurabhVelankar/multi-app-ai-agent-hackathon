from typing import Annotated, Any, Literal
from typing_extensions import TypedDict
import operator


class TriggerDict(TypedDict, total=False):
    type: Literal["goal", "email", "slack"]
    raw: Any                   # str or dict
    source_id: str | None


class IntentDict(TypedDict, total=False):
    id: str
    type: Literal["meeting", "task", "follow_up", "info"]
    summary: str
    entities: dict             # people, times, links
    confidence: float


class PlanStepDict(TypedDict, total=False):
    id: str
    action: str                # create_event | create_notion | draft_email | notify_slack
    app: str
    args: dict
    requires_hitl: bool
    status: Literal["pending", "done", "skipped", "blocked"]


class LifeState(TypedDict, total=False):
    run_id: str
    thread_id: str
    created_at: str                        # ISO8601
    family_id: str | None
    admin_id: str | None                   # requester / token owner for writes
    shared_with: list[str]                 # admin_ids who may view this run
    approval_assignee: str | None          # HITL primary target
    trigger: TriggerDict
    normalized_context: dict
    intents: Annotated[list[IntentDict], operator.add]
    priority_scores: dict                  # intent_id -> score breakdown
    selected_intent: dict | None
    plan_steps: Annotated[list[PlanStepDict], operator.add]
    calendar_actions: Annotated[list, operator.add]
    drafts: Annotated[list, operator.add]
    approvals: dict                        # key -> "approved" | "rejected" | "pending"
    tool_results: Annotated[list, operator.add]   # append-only
    execution_receipts: Annotated[list, operator.add]
    errors: Annotated[list, operator.add]          # append-only
    retry_count: int
    status: Literal["running", "needs_approval", "pass", "abort", "error"]
    needs_approval: bool
    audit_ref: str | None
