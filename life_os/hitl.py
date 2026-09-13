"""HITL channels — CLI first; Slack with CLI fallback (Agent 2)."""

from __future__ import annotations

import time
from typing import Optional

from life_os.tools._common import env, use_mock_connectors
from life_os.types import ApprovalDecision


def resolve_assignee(policy: str) -> Optional[str]:
    """Single `approval_assignee` admin_id for a given HITL policy.

    - primary / round_robin (documented for a future release — rotates the
      primary among owners; not implemented, falls back to primary today):
      the roster owner is the assignee.
    - any_of: no single assignee — any owner or operator may approve — so
      this returns None; use `mention_targets` for who gets notified.
    """
    from life_os.admins import get_roster

    if policy == "any_of":
        return None
    owner = get_roster().owner()
    return owner.admin_id if owner else None


def mention_targets(policy: str) -> list[str]:
    """Slack user ids to @mention for an approval request under `policy`."""
    from life_os.admins import get_roster

    admins = get_roster().approval_targets() if policy == "any_of" else None
    if admins is None:
        owner = get_roster().owner()
        admins = [owner] if owner else []
    return [a.slack_user_id for a in admins if a.slack_user_id]


def _mention_prefix(policy: str) -> str:
    ids = mention_targets(policy)
    if not ids:
        fallback = env("ADMIN_PRIMARY_SLACK")
        return f"<@{fallback}> " if fallback else ""
    return " ".join(f"<@{sid}>" for sid in ids) + " "


def wait_cli_approval(run_id: str, summary: str) -> ApprovalDecision:
    """Block for y/n approval on stdin. Auto-approve in non-interactive mock tests via env."""
    auto = env("LIFE_OS_HITL_AUTO")
    if auto is not None:
        decision: ApprovalDecision = "approve" if auto.strip().lower() in {"1", "approve", "yes", "y"} else "deny"
        print(f"[hitl:cli] auto decision={decision} run_id={run_id}")
        return decision

    print("\n=== Life OS HITL ===")
    print(f"run_id: {run_id}")
    print(summary)
    print("Approve send / irreversible action? [y/N]: ", end="", flush=True)
    try:
        answer = input().strip().lower()
    except EOFError:
        answer = "n"
    return "approve" if answer in {"y", "yes"} else "deny"


def wait_slack_approval(
    run_id: str,
    summary: str,
    *,
    admin_id: Optional[str] = None,
    policy: Optional[str] = None,
    timeout_sec: float = 120.0,
    poll_interval: float = 3.0,
) -> ApprovalDecision:
    """Request Slack approval; poll reactions. Fall back to CLI if Slack fails or times out.

    `policy="any_of"` @mentions every owner+operator so any of them can react;
    otherwise only the primary owner is mentioned.
    """
    fallback = env("HITL_FALLBACK_CLI", "1")
    fallback_on = (fallback or "1").strip().lower() in {"1", "true", "yes", "on"}
    resolved_policy = (policy or env("HITL_POLICY", "primary") or "primary").strip().lower()
    summary_with_mentions = _mention_prefix(resolved_policy) + summary

    try:
        from life_os.tools.slack import request_slack_approval

        request_id = request_slack_approval(run_id, summary_with_mentions, admin_id=admin_id)
    except Exception as exc:  # noqa: BLE001
        print(f"[hitl:slack] request failed ({exc}); falling back to CLI" if fallback_on else "")
        if fallback_on:
            return wait_cli_approval(run_id, summary)
        raise

    if use_mock_connectors():
        # In mock, Slack cannot receive reacts — use CLI / auto
        print(f"[hitl:slack] mock request_id={request_id}; using CLI/auto")
        return wait_cli_approval(run_id, summary)

    # Live poll for reactions on the approval message
    channel = env("SLACK_CHANNEL_ID")
    deadline = time.time() + timeout_sec
    try:
        import json
        import urllib.parse
        import urllib.request

        token = env("SLACK_BOT_TOKEN")
        while time.time() < deadline:
            params = urllib.parse.urlencode(
                {"channel": channel, "timestamp": request_id, "full": "true"}
            )
            req = urllib.request.Request(
                f"https://slack.com/api/reactions.get?{params}",
                headers={"Authorization": f"Bearer {token}"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            if body.get("ok"):
                reactions = (body.get("message") or {}).get("reactions") or []
                names = {r.get("name") for r in reactions}
                if "white_check_mark" in names or "heavy_check_mark" in names or "+1" in names:
                    return "approve"
                if "x" in names or "no_entry" in names or "-1" in names:
                    return "deny"
            time.sleep(poll_interval)
    except Exception as exc:  # noqa: BLE001
        print(f"[hitl:slack] poll failed ({exc})")

    if fallback_on:
        print("[hitl:slack] timeout/error — CLI fallback")
        return wait_cli_approval(run_id, summary)
    return "deny"


def request_approval(
    run_id: str,
    summary: str,
    *,
    admin_id: Optional[str] = None,
    prefer: Optional[str] = None,
    policy: Optional[str] = None,
) -> ApprovalDecision:
    """Primary entry: prefer Slack when configured, else CLI.

    Policy comes from the family roster's `HITL_POLICY` (any_of / primary)
    unless overridden by the `policy` kwarg.
    """
    from life_os.admins import get_roster

    resolved_policy = (policy or get_roster().hitl_policy or "primary").strip().lower()
    channel = prefer or ("slack" if env("SLACK_BOT_TOKEN") and not use_mock_connectors() else "cli")
    assignee = resolve_assignee(resolved_policy)
    print(f"[hitl] policy={resolved_policy} channel={channel} admin_id={admin_id} assignee={assignee}")
    if channel == "slack":
        return wait_slack_approval(run_id, summary, admin_id=admin_id, policy=resolved_policy)
    return wait_cli_approval(run_id, summary)
