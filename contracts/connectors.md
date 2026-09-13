# Life OS — Connector Contract (Agent 1 ↔ Agent 2)

> **Sole file editor: Agent 2.** Agent 1 may propose signatures but must not commit edits.  
> Change protocol: propose in chat → both ACK → Agent 2 updates this file → Agent 2 implements → Agent 1 wires imports.

**Status:** FROZEN for Tier 0–1 — **per-user OAuth** (each `admin_id` has its own Google token)

**Credentials rule:** Every write tool takes `admin_id`. Google Calendar / Gmail / Sheets load `.oauth/{admin_id}_google.json` (or `ADMIN_XX_GOOGLE_TOKEN_PATH`). Notion uses `ADMIN_XX_NOTION_TOKEN` when set, else shared `NOTION_TOKEN`. Never use another admin’s tokens for writes.

---

## Shared types

### `tool_result`

```text
{
  ok: bool,
  app: "calendar" | "notion" | "slack" | "sheets" | "gmail",
  action: str,
  external_id: str | null,
  idempotency_key: str | null,
  error: str | null,
  raw: object | null,
  proposed_only: bool | null   # calendar: true when event was not created
}
```

### `draft` (Gmail)

```text
{
  draft_id: str,
  thread_id: str | null,
  body: str,
  run_id: str
}
```

### Approval decision

```text
"approve" | "deny"
```

---

## Function surface

Import path convention:

```text
from life_os.tools.calendar import create_calendar_event
from life_os.tools.notion import create_notion_page
from life_os.tools.slack import post_slack_receipt, request_slack_approval
from life_os.tools.sheets import append_sheets_audit
from life_os.tools.gmail import draft_gmail_reply, send_gmail
from life_os.hitl import wait_cli_approval

# Write nodes (wired by Agent 1 graph.py)
from life_os.agents.scheduler import scheduler_node
from life_os.agents.executor import executor_node
from life_os.agents.auditor import auditor_node
```

### Calendar

```text
create_calendar_event(
  run_id: str,
  title: str,
  start: str,          # ISO-8601
  end: str,            # ISO-8601
  idempotency_key: str,
  *,
  admin_id: str | None = None,
  create: bool = True  # False → propose only (no write)
) -> tool_result
```

### Notion

```text
create_notion_page(
  run_id: str,
  title: str,
  body: str,
  idempotency_key: str,
  *,
  admin_id: str | None = None
) -> tool_result
```

### Slack

```text
post_slack_receipt(
  run_id: str,
  text: str,
  *,
  admin_id: str | None = None
) -> tool_result

request_slack_approval(
  run_id: str,
  summary: str,
  *,
  admin_id: str | None = None
) -> str   # approval_request_id (message ts or mock id)
```

### HITL (CLI)

```text
wait_cli_approval(
  run_id: str,
  summary: str
) -> "approve" | "deny"
```

### Sheets (audit)

```text
append_sheets_audit(
  run_id: str,
  life_state_row: dict,   # flat row: run_id, family_id, admin_id, approver,
                          # approval_assignee, oauth_account, status, apps,
                          # errors, timestamp, …
  *,
  admin_id: str | None = None
) -> tool_result
```

### Gmail

```text
draft_gmail_reply(
  run_id: str,
  thread_id: str | None,
  body: str,
  *,
  admin_id: str | None = None
) -> draft

send_gmail(
  run_id: str,
  draft_id: str,
  *,
  admin_id: str | None = None
) -> tool_result
# HITL-gated only — Critic / hitl must approve before Agent 1 calls this
```

---

## Mock mode

```bash
LIFE_OS_USE_MOCK_CONNECTORS=1
```

When set (default for local without credentials), every tool returns deterministic fake `external_id` values and logs the intended write. Signatures stay identical so Agent 1 can swap stubs → real imports without changing graph edges.

---

## Idempotency

In-memory (Tier 0) store keyed by `(admin_id or "", idempotency_key)`. Re-calling with the same key returns the prior `tool_result` without a second write.

Suggested keys:

| Resource | Key pattern |
|----------|-------------|
| Calendar | `cal:{run_id}:{intent_id}` |
| Notion | `notion:{run_id}:{intent_id}` |
| Slack receipt | `slack:{run_id}:receipt` |
| Sheets | `sheets:{run_id}:audit` (Tier 0 may still append; store is best-effort) |
| Gmail draft | `gmail:{run_id}:draft` |

---

## Policy (hard)

- No deletes
- `send_gmail` only after HITL approve
- Failed tool → `ok=False` + `error` string; never fake success in live mode
- Partial success is allowed across apps

---

## Env keys (Agent 2 → Agent 1 for `.env.example`)

```text
LIFE_OS_USE_MOCK_CONNECTORS=1
FAMILY_ID=hauns
ADMIN_MAX=10
HITL_POLICY=any_of
ADMIN_IDS=admin_01,admin_02

ADMIN_01_NAME=Parent A
ADMIN_01_ROLE=owner
ADMIN_01_SLACK=U_AAAA
ADMIN_01_EMAIL=a@example.com
ADMIN_01_GOOGLE_TOKEN_PATH=.oauth/admin_01_google.json

ADMIN_02_NAME=Parent B
ADMIN_02_ROLE=operator
ADMIN_02_GOOGLE_TOKEN_PATH=.oauth/admin_02_google.json

GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=http://localhost:8000/oauth/google/callback
GOOGLE_CALENDAR_ID=primary
SHEETS_SPREADSHEET_ID=
SHEETS_AUDIT_RANGE=Audit!A:Z

NOTION_TOKEN=
NOTION_PARENT_PAGE_ID=
NOTION_DATABASE_ID=

SLACK_BOT_TOKEN=
SLACK_CHANNEL_ID=
SLACK_SIGNING_SECRET=
```

OAuth connect: `GET /admins/{admin_id}/oauth/google/start` → consent → `/oauth/google/callback?state={admin_id}`  
CLI: `python -m life_os.oauth_google --admin-id admin_01`

---

## ACK log

| When | Who | Note |
|------|-----|------|
| 2026-09-13 | Agent 2 | Initial freeze published — awaiting Agent 1 ACK |
