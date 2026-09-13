"""FastAPI surface — runs, approve, admins, per-admin Google OAuth."""
import datetime
import uuid
from typing import Any, Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from life_os.adapters import google_auth
from life_os.admins import get_roster, notion_token_for
from life_os.graph import graph
from life_os.state import LifeState

app = FastAPI(title="Life OS Orchestrator", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Idempotency map: (admin_id, source_id) -> run_id
_source_to_run: dict[tuple[str, str], str] = {}


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


class AddAdminRequest(BaseModel):
    acting_admin_id: str
    admin_id: str
    name: str
    role: Literal["owner", "operator", "viewer"]
    email: str | None = None
    slack_user_id: str | None = None


class SandboxActionRequest(BaseModel):
    """Cross-user sandbox action: email, calendar invite, or scheduled meeting."""

    from_admin_id: str
    to_admin_id: str
    action: Literal["email", "calendar_invite", "schedule_meeting"]
    subject: str | None = None
    body: str | None = None
    title: str | None = None
    start: str | None = None
    end: str | None = None
    allow_conflict: bool = False


# ---------- helpers ----------

def _resolve_admin_id(admin_id: str | None) -> str:
    roster = get_roster()
    if admin_id is None:
        owner = roster.owner()
        if owner is None:
            raise HTTPException(status_code=400, detail="No admins configured")
        return owner.admin_id
    if roster.get(admin_id) is None:
        raise HTTPException(status_code=403, detail=f"Unknown admin_id: {admin_id}")
    return admin_id


def _get_state(run_id: str) -> dict:
    config = {"configurable": {"thread_id": run_id}}
    snapshot = graph.get_state(config)
    if snapshot is None or not snapshot.values:
        raise HTTPException(status_code=404, detail="Run not found")
    return dict(snapshot.values)


def _admin_public(admin_id: str) -> dict:
    roster = get_roster()
    admin = roster.require(admin_id)
    status = google_auth.oauth_status(admin_id)
    return {
        "admin_id": admin.admin_id,
        "name": admin.name,
        "role": admin.role,
        "email": admin.email,
        "slack_user_id": admin.slack_user_id,
        "google_token_path": admin.google_token_path,
        "google_connected": status["connected"],
    }


# ---------- routes ----------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/admins")
def list_admins():
    roster = get_roster()
    return {
        "family_id": roster.family_id,
        "hitl_policy": roster.hitl_policy,
        "admin_max": roster.admin_max,
        "admins": [_admin_public(a.admin_id) for a in roster.list_admins()],
    }


@app.post("/admins")
def add_admin(req: AddAdminRequest):
    """Runtime add — in-memory only until process restart (env remains source of truth)."""
    roster = get_roster()
    if not roster.can_manage_roster(req.acting_admin_id):
        raise HTTPException(status_code=403, detail="Only owner can add admins")
    if len(roster.admins) >= roster.admin_max:
        raise HTTPException(
            status_code=400, detail=f"Admin roster full (max {roster.admin_max})"
        )
    if req.admin_id in roster.admins:
        raise HTTPException(status_code=400, detail="admin_id already exists")
    from life_os.admins import Admin

    roster.admins[req.admin_id] = Admin(
        admin_id=req.admin_id,
        name=req.name,
        role=req.role,
        email=req.email,
        slack_user_id=req.slack_user_id,
        google_token_path=f".oauth/{req.admin_id}_google.json",
    )
    return _admin_public(req.admin_id)


@app.delete("/admins/{admin_id}")
def remove_admin(admin_id: str, acting_admin_id: str = Query(...)):
    roster = get_roster()
    if not roster.can_manage_roster(acting_admin_id):
        raise HTTPException(status_code=403, detail="Only owner can remove admins")
    target = roster.get(admin_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Admin not found")
    if target.role == "owner":
        owners = [a for a in roster.list_admins() if a.role == "owner"]
        if len(owners) <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove last owner")
    del roster.admins[admin_id]
    return {"ok": True, "removed": admin_id}


@app.get("/admins/{admin_id}/oauth/google/start")
def start_google_oauth(admin_id: str, redirect: bool = False):
    roster = get_roster()
    if roster.get(admin_id) is None:
        raise HTTPException(status_code=404, detail="Unknown admin_id")
    try:
        auth_url = google_auth.build_auth_url(admin_id)
    except google_auth.GoogleAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if redirect:
        return RedirectResponse(auth_url)
    return {"admin_id": admin_id, "auth_url": auth_url}


@app.get("/admins/{admin_id}/oauth/status")
def oauth_status(admin_id: str):
    roster = get_roster()
    if roster.get(admin_id) is None:
        raise HTTPException(status_code=404, detail="Unknown admin_id")
    status = google_auth.oauth_status(admin_id)
    status["notion"] = "connected" if notion_token_for(admin_id) else "missing"
    return status


@app.get("/oauth/google/callback")
def google_oauth_callback(code: str, state: str):
    """state = admin_id from consent start."""
    admin_id = state
    roster = get_roster()
    if roster.get(admin_id) is None:
        raise HTTPException(status_code=400, detail=f"Invalid state admin_id={admin_id}")
    try:
        path = google_auth.exchange_code(admin_id, code)
    except google_auth.GoogleAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    status = google_auth.oauth_status(admin_id)
    status["saved_to"] = str(path)
    return status


@app.post("/runs", response_model=CreateRunResponse)
def create_run(req: CreateRunRequest):
    admin_id = _resolve_admin_id(req.admin_id)
    roster = get_roster()

    # Idempotency scoped by admin
    if req.source_id:
        key = (admin_id, req.source_id)
        if key in _source_to_run:
            existing_run_id = _source_to_run[key]
            state = _get_state(existing_run_id)
            return CreateRunResponse(
                run_id=existing_run_id, status=state.get("status", "running")
            )

    run_id = str(uuid.uuid4())
    if req.source_id:
        _source_to_run[(admin_id, req.source_id)] = run_id

    initial_state: LifeState = {
        "run_id": run_id,
        "thread_id": run_id,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "family_id": roster.family_id,
        "admin_id": admin_id,
        "shared_with": roster.default_shared_with(),
        "approval_assignee": None,
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


@app.get("/sandbox/admins/{admin_id}")
def get_sandbox_world(admin_id: str) -> dict:
    """Per-admin sandbox mailbox/calendar snapshot for cockpit demos."""
    from life_os.sandbox import get_user_world, resolve_user_id, sandbox_enabled

    _resolve_admin_id(admin_id)
    if not sandbox_enabled():
        raise HTTPException(
            status_code=404,
            detail="Sandbox disabled (set LIFE_OS_USE_SANDBOX=1 or use mock connectors)",
        )
    try:
        user_id = resolve_user_id(admin_id=admin_id)
        world = get_user_world(user_id)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    world["admin_id"] = admin_id
    return world


@app.post("/sandbox/actions")
def post_sandbox_action(req: SandboxActionRequest) -> dict:
    """Send email / calendar invite / schedule meeting between any two admins."""
    from life_os.sandbox import cross_user_action, sandbox_enabled

    _resolve_admin_id(req.from_admin_id)
    _resolve_admin_id(req.to_admin_id)
    if not sandbox_enabled():
        raise HTTPException(
            status_code=404,
            detail="Sandbox disabled (set LIFE_OS_USE_SANDBOX=1 or use mock connectors)",
        )
    try:
        return cross_user_action(
            action=req.action,
            from_admin_id=req.from_admin_id,
            to_admin_id=req.to_admin_id,
            subject=req.subject,
            body=req.body,
            title=req.title,
            start=req.start,
            end=req.end,
            allow_conflict=req.allow_conflict,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/runs/{run_id}")
def get_run(run_id: str, admin_id: str | None = None) -> dict:
    state = _get_state(run_id)
    if admin_id:
        roster = get_roster()
        if roster.get(admin_id) is None:
            raise HTTPException(status_code=403, detail="Unknown admin_id")
        allowed = {
            state.get("admin_id"),
            *(state.get("shared_with") or []),
        }
        owner = roster.owner()
        if owner:
            allowed.add(owner.admin_id)
        if admin_id not in allowed:
            raise HTTPException(status_code=403, detail="Not allowed to view this run")
    return state


@app.post("/runs/{run_id}/approve")
def approve_run(run_id: str, req: ApproveRequest) -> dict:
    state = _get_state(run_id)

    if state.get("status") != "needs_approval":
        raise HTTPException(status_code=409, detail="Run is not awaiting approval")

    roster = get_roster()
    if not roster.can_approve(req.admin_id):
        raise HTTPException(
            status_code=403,
            detail="Admin cannot approve (unknown or viewer role)",
        )

    # Inject approval — do NOT overwrite requester admin_id (token owner)
    approval_key = f"hitl:{run_id}"
    config = {"configurable": {"thread_id": run_id}}

    graph.update_state(
        config,
        {
            "approvals": {approval_key: req.decision},
            "approval_assignee": req.admin_id,
            "status": "running" if req.decision == "approve" else "abort",
            "needs_approval": False,
        },
    )

    if req.decision == "approve":
        graph.invoke(None, config=config)

    return _get_state(run_id)
