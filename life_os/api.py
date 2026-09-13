"""FastAPI surface — POST /runs, GET /runs/{id}, POST /runs/{id}/approve, GET /health."""
import datetime
import uuid
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from life_os.config import ADMIN_MAX
from life_os.graph import graph
from life_os.state import LifeState

app = FastAPI(title="Life OS Orchestrator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory admin roster (Tier 0) — maps admin_id -> registered_at
_admin_roster: dict[str, str] = {}

# Idempotency map: source_id -> run_id
_source_to_run: dict[str, str] = {}


# ---------- request / response models ----------

class CreateRunRequest(BaseModel):
    trigger_type: Literal["goal", "email", "slack"]
    trigger_payload: Any
    admin_id: str | None = None
    source_id: str | None = None


class CreateRunResponse(BaseModel):
    run_id: str
    status: str


class ApproveRequest(BaseModel):
    decision: Literal["approve", "deny"]
    admin_id: str


# ---------- helpers ----------

def _register_admin(admin_id: str | None) -> str | None:
    if admin_id is None:
        return None
    if admin_id not in _admin_roster:
        if len(_admin_roster) >= ADMIN_MAX:
            raise HTTPException(status_code=400, detail=f"Admin roster full (max {ADMIN_MAX})")
        _admin_roster[admin_id] = datetime.datetime.utcnow().isoformat() + "Z"
    return admin_id


def _get_state(run_id: str) -> dict:
    config = {"configurable": {"thread_id": run_id}}
    snapshot = graph.get_state(config)
    if snapshot is None or not snapshot.values:
        raise HTTPException(status_code=404, detail="Run not found")
    return dict(snapshot.values)


# ---------- routes ----------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/runs", response_model=CreateRunResponse)
def create_run(req: CreateRunRequest):
    # Idempotency
    if req.source_id and req.source_id in _source_to_run:
        existing_run_id = _source_to_run[req.source_id]
        state = _get_state(existing_run_id)
        return CreateRunResponse(run_id=existing_run_id, status=state.get("status", "running"))

    admin_id = _register_admin(req.admin_id)

    run_id = str(uuid.uuid4())
    if req.source_id:
        _source_to_run[req.source_id] = run_id

    initial_state: LifeState = {
        "run_id": run_id,
        "thread_id": run_id,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "admin_id": admin_id,
        "trigger": {
            "type": req.trigger_type,
            "raw": req.trigger_payload,
            "source_id": req.source_id,
        },
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

    config = {"configurable": {"thread_id": run_id}}
    graph.invoke(initial_state, config=config)

    state = _get_state(run_id)
    return CreateRunResponse(run_id=run_id, status=state.get("status", "running"))


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict:
    return _get_state(run_id)


@app.post("/runs/{run_id}/approve")
def approve_run(run_id: str, req: ApproveRequest) -> dict:
    state = _get_state(run_id)

    if state.get("status") != "needs_approval":
        raise HTTPException(status_code=409, detail="Run is not awaiting approval")

    _register_admin(req.admin_id)

    # Inject approval decision into state and resume
    approval_key = f"hitl:{run_id}"
    config = {"configurable": {"thread_id": run_id}}

    graph.update_state(
        config,
        {
            "approvals": {approval_key: req.decision},
            "admin_id": req.admin_id,
            "status": "running" if req.decision == "approve" else "abort",
            "needs_approval": False,
        },
    )

    if req.decision == "approve":
        graph.invoke(None, config=config)

    return _get_state(run_id)
