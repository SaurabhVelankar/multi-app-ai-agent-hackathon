"""CLI: python -m life_os.evals meeting_email.json

Runs a golden fixture through the eval harness (mocked LLM, mock connectors)
and prints side-effect summary. Exit 0 if status is terminal.
"""

from __future__ import annotations

import argparse
import json
import sys

from life_os.evals import apps_ok, has_gmail_send, run_eval


# Default canned LLM payloads for ad-hoc CLI (pytest supplies its own)
_DEFAULTS = {
    "meeting_email.json": {
        "intake": {
            "intents": [
                {
                    "id": "i1",
                    "type": "meeting",
                    "summary": "Q4 planning sync with Sarah",
                    "entities": {"people": ["Sarah"], "times": ["Monday or Tuesday afternoon"], "links": []},
                    "confidence": 0.92,
                }
            ],
            "normalized_context": {"summary": "meeting + brief"},
        },
        "priority": {
            "scores": {
                "i1": {
                    "deadline_urgency": 7,
                    "people_impact": 6,
                    "irreversibility": 2,
                    "total": 8,
                    "rationale": "clear meeting",
                }
            }
        },
        "planner": {
            "plan_steps": [
                {
                    "id": "s1",
                    "action": "create_event",
                    "app": "calendar",
                    "args": {
                        "title": "Q4 planning sync",
                        "start": "2026-09-15T15:00:00Z",
                        "end": "2026-09-15T15:30:00Z",
                    },
                    "requires_hitl": False,
                    "status": "pending",
                },
                {
                    "id": "s2",
                    "action": "create_notion",
                    "app": "notion",
                    "args": {"title": "Q4 brief"},
                    "requires_hitl": False,
                    "status": "pending",
                },
                {
                    "id": "s3",
                    "action": "notify_slack",
                    "app": "slack",
                    "args": {},
                    "requires_hitl": False,
                    "status": "pending",
                },
                {
                    "id": "s4",
                    "action": "draft_email",
                    "app": "gmail",
                    "args": {},
                    "requires_hitl": False,
                    "status": "pending",
                },
            ]
        },
    }
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a Life OS golden-fixture eval")
    parser.add_argument("fixture", help="Fixture filename under life_os/fixtures/")
    parser.add_argument("--admin-id", default="admin_01")
    args = parser.parse_args(argv)

    canned = _DEFAULTS.get(args.fixture)
    if not canned:
        print(
            f"No default LLM canned responses for {args.fixture}; "
            "use pytest tests/evals/ for full coverage.",
            file=sys.stderr,
        )
        return 2

    result = run_eval(
        args.fixture,
        intake_json=canned["intake"],
        priority_json=canned["priority"],
        planner_json=canned["planner"],
        admin_id=args.admin_id,
    )
    summary = {
        "run_id": result.get("run_id"),
        "status": result.get("status"),
        "needs_approval": result.get("needs_approval"),
        "apps_ok": sorted(apps_ok(result)),
        "gmail_sent": has_gmail_send(result),
        "audit_ref": result.get("audit_ref"),
        "errors": result.get("errors"),
        "drafts": len(result.get("drafts") or []),
    }
    print(json.dumps(summary, indent=2))
    if result.get("status") in {"pass", "needs_approval", "abort", "error"}:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
