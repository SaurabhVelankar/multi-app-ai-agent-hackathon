"""HITL channels — CLI first; Slack with CLI fallback (Agent 2)."""

from __future__ import annotations

import time
from typing import Optional

from life_os.tools._common import env, use_mock_connectors
from life_os.types import ApprovalDecision


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
    timeout_sec: float = 120.0,
    poll_interval: float = 3.0,
) -> ApprovalDecision:
    """Request Slack approval; poll reactions. Fall back to CLI if Slack fails or times out."""
    fallback = env("HITL_FALLBACK_CLI", "1")
    fallback_on = (fallback or "1").strip().lower() in {"1", "true", "yes", "on"}

    try:
        from life_os.tools.slack import request_slack_approval

        request_id = request_slack_approval(run_id, summary, admin_id=admin_id)
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
) -> ApprovalDecision:
    """Primary entry: prefer Slack when configured, else CLI. Policy: Primary Admin."""
    channel = prefer or ("slack" if env("SLACK_BOT_TOKEN") and not use_mock_connectors() else "cli")
    policy = env("HITL_POLICY", "primary") or "primary"
    print(f"[hitl] policy={policy} channel={channel} admin_id={admin_id}")
    if channel == "slack":
        return wait_slack_approval(run_id, summary, admin_id=admin_id)
    return wait_cli_approval(run_id, summary)
