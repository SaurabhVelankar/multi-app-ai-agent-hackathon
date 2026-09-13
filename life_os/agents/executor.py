"""Executor node — Notion, Slack receipt, Gmail draft (Agent 2). Tools only."""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping


def executor_node(state: Mapping[str, Any]) -> dict[str, Any]:
    """Perform safe writes; stage Gmail draft (no send).

    plan_steps actions: notion_page / create_page, slack_receipt, gmail_draft
    """
    from life_os.tools.gmail import draft_gmail_reply
    from life_os.tools.notion import create_notion_page
    from life_os.tools.slack import post_slack_receipt

    run_id = str(state.get("run_id") or "unknown")
    admin_id = state.get("admin_id")
    plan_steps = list(state.get("plan_steps") or [])
    drafts = list(state.get("drafts") or [])
    tool_results = list(state.get("tool_results") or [])
    errors = list(state.get("errors") or [])
    execution_receipts = list(state.get("execution_receipts") or [])

    steps = [s for s in plan_steps if isinstance(s, dict)]

    def _do_notion(step: Mapping[str, Any] | None = None) -> None:
        nonlocal tool_results, errors, execution_receipts
        step = step or {}
        intent_id = str(step.get("intent_id") or "meeting")
        idem = str(step.get("idempotency_key") or f"notion:{run_id}:{intent_id}")
        title = str(step.get("title") or f"Life OS brief — {run_id}")
        body = str(step.get("body") or step.get("content") or state.get("normalized_context") or "Meeting brief")
        result = create_notion_page(run_id, title, body, idem, admin_id=admin_id)
        tool_results.append(result)
        execution_receipts.append({"app": "notion", "external_id": result.get("external_id"), "ok": result.get("ok")})
        if not result.get("ok"):
            errors.append({"node": "executor", "app": "notion", "error": result.get("error")})

    def _do_slack(step: Mapping[str, Any] | None = None) -> None:
        nonlocal tool_results, errors, execution_receipts
        step = step or {}
        text = str(
            step.get("text")
            or f"Life OS run `{run_id}` executed. status={state.get('status', 'running')}"
        )
        result = post_slack_receipt(run_id, text, admin_id=admin_id)
        tool_results.append(result)
        execution_receipts.append({"app": "slack", "external_id": result.get("external_id"), "ok": result.get("ok")})
        if not result.get("ok"):
            errors.append({"node": "executor", "app": "slack", "error": result.get("error")})

    def _do_gmail_draft(step: Mapping[str, Any] | None = None) -> None:
        nonlocal drafts, errors
        step = step or {}
        thread_id = step.get("thread_id") or (state.get("trigger") or {}).get("thread_id")
        body = str(step.get("body") or step.get("draft_body") or "Thanks — confirming via Life OS.")
        draft = draft_gmail_reply(run_id, thread_id, body, admin_id=admin_id)
        drafts.append(draft)
        if draft.get("draft_id", "").startswith("error-draft-") or draft.get("error"):  # type: ignore[arg-type]
            errors.append(
                {
                    "node": "executor",
                    "app": "gmail",
                    "error": draft.get("error") or "draft failed",
                }
            )

    notion_steps = [s for s in steps if s.get("action") in {"notion_page", "create_page", "notion"}]
    slack_steps = [s for s in steps if s.get("action") in {"slack_receipt", "slack"}]
    gmail_steps = [s for s in steps if s.get("action") in {"gmail_draft", "draft_email", "gmail"}]

    # Demo default: if no explicit executor actions, do Notion + Slack + Gmail draft
    if not notion_steps and not slack_steps and not gmail_steps:
        _do_notion()
        _do_slack()
        _do_gmail_draft()
    else:
        for s in notion_steps:
            _do_notion(s)
        for s in slack_steps:
            _do_slack(s)
        for s in gmail_steps:
            _do_gmail_draft(s)

    return {
        "drafts": drafts,
        "tool_results": tool_results,
        "errors": errors,
        "execution_receipts": execution_receipts,
    }


def executor(state: MutableMapping[str, Any]) -> dict[str, Any]:
    return executor_node(state)
