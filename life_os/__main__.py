"""CLI entry — python -m life_os --fixture meeting_email.json [--admin-id user1]"""
import argparse
import datetime
import json
import uuid
from pathlib import Path

from life_os.admins import get_roster
from life_os.graph import graph
from life_os.state import LifeState


def _load_fixture(path: str) -> dict:
    p = Path(path)
    if not p.is_absolute():
        # Also look in life_os/fixtures/
        candidates = [p, Path(__file__).parent / "fixtures" / path]
        for c in candidates:
            if c.exists():
                return json.loads(c.read_text())
        raise FileNotFoundError(f"Fixture not found: {path}")
    return json.loads(p.read_text())


def _fixture_to_trigger(fixture: dict) -> dict:
    ftype = fixture.get("type", "goal")
    if ftype == "email":
        raw = fixture
        source_id = fixture.get("fixture_id") or fixture.get("message_id")
    else:
        raw = fixture.get("goal", json.dumps(fixture))
        source_id = fixture.get("fixture_id")
    return {"type": ftype, "raw": raw, "source_id": source_id}


def main():
    parser = argparse.ArgumentParser(description="Life OS CLI")
    parser.add_argument("--fixture", required=True, help="Path or filename of fixture JSON")
    parser.add_argument("--admin-id", default=None, help="Admin identifier")
    args = parser.parse_args()

    fixture = _load_fixture(args.fixture)
    trigger = _fixture_to_trigger(fixture)
    roster = get_roster()

    admin_id = args.admin_id
    if admin_id is None:
        owner = roster.owner()
        admin_id = owner.admin_id if owner else None
    elif roster.get(admin_id) is None:
        raise SystemExit(f"Unknown admin_id={admin_id}. Known: {list(roster.admins)}")

    run_id = str(uuid.uuid4())
    initial_state: LifeState = {
        "run_id": run_id,
        "thread_id": run_id,
        "created_at": datetime.datetime.utcnow().isoformat() + "Z",
        "family_id": roster.family_id,
        "admin_id": admin_id,
        "shared_with": roster.default_shared_with(),
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

    config = {"configurable": {"thread_id": run_id}}

    print(f"\n=== Life OS Run ===")
    print(f"run_id  : {run_id}")
    print(f"fixture : {args.fixture}")
    print(f"trigger : {trigger['type']}\n")

    # Stream node outputs
    for event in graph.stream(initial_state, config=config, stream_mode="updates"):
        for node, update in event.items():
            print(f"[{node}] ", end="")
            if isinstance(update, dict):
                status = update.get("status", "")
                if status:
                    print(f"status={status}", end=" ")
                intents = update.get("intents", [])
                if intents:
                    print(f"intents={len(intents)}", end=" ")
                steps = update.get("plan_steps", [])
                if steps:
                    print(f"steps={len(steps)}", end=" ")
            print()

    # Get final state
    final = graph.get_state(config)
    state = final.values if hasattr(final, "values") else {}

    print(f"\n=== Final Status ===")
    print(f"status        : {state.get('status')}")
    print(f"needs_approval: {state.get('needs_approval')}")
    print(f"intents       : {len(state.get('intents', []))}")
    print(f"plan_steps    : {len(state.get('plan_steps', []))}")
    print(f"errors        : {len(state.get('errors', []))}")

    if state.get("needs_approval"):
        print("\n[!] Run paused — requires human approval.")
        print(f"    POST /runs/{run_id}/approve {{\"decision\": \"approve\", \"admin_id\": \"...\"}}")


if __name__ == "__main__":
    main()
