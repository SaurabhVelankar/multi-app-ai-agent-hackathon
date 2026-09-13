# Family Shared Admin

Life OS supports a family of up to **10 admins** sharing one deployment. Each
admin connects **their own** Google account — there is no "family login" —
and every write action uses the token of the admin who requested it, never
the token of whoever approved it.

See [`contracts/connectors.md`](contracts/connectors.md) for the full
connector contract and [`contracts/openapi.yaml`](contracts/openapi.yaml) for
the API schema. This doc covers the roster, per-user OAuth, HITL routing, and
the audit trail.

---

## 1. Roster

Configured entirely from environment (`.env.local`), loaded by
[`life_os/admins.py`](life_os/admins.py):

```bash
FAMILY_ID=hauns
ADMIN_MAX=10          # hard cap; startup refuses ADMIN_IDS longer than this
HITL_POLICY=any_of    # any_of | primary (round_robin is documented below, not yet implemented)
ADMIN_IDS=admin_01,admin_02

ADMIN_01_NAME=Parent A
ADMIN_01_ROLE=owner        # owner | operator | viewer
ADMIN_01_EMAIL=parent-a@example.com
ADMIN_01_SLACK=U_AAAA
ADMIN_01_GOOGLE_TOKEN_PATH=.oauth/admin_01_google.json   # default shown; usually omit
# ADMIN_01_NOTION_TOKEN=                                  # per-admin Notion override

ADMIN_02_NAME=Parent B
ADMIN_02_ROLE=operator
ADMIN_02_GOOGLE_TOKEN_PATH=.oauth/admin_02_google.json
```

Roles:

| Role | Add/remove admins | Approve HITL | Trigger runs |
|------|:---:|:---:|:---:|
| `owner` | yes | yes | yes |
| `operator` | no | yes | yes |
| `viewer` | no | **no** | yes (read-only elsewhere) |

Rules enforced at startup and on every request (`life_os/admins.py`,
`life_os/api.py`):

- More than `ADMIN_MAX` (default 10) entries in `ADMIN_IDS` → the process
  refuses to start (`RuntimeError`).
- No `owner` configured → the first admin is promoted to `owner` with a
  warning; more than one `owner` is allowed (first one wins for defaults).
- Every request that carries an `admin_id` is checked against the roster —
  unknown ids are rejected with `403`.
- Only an `owner` can add or remove admins (`POST/DELETE /admins`); the last
  remaining `owner` cannot be removed.
- `viewer` is blocked from `POST /runs/{id}/approve` (`403`).

`GET /admins` lists the roster (with each admin's Google connection status);
`POST /admins` / `DELETE /admins/{id}` manage it at runtime — in-memory only,
so the env file remains the source of truth across restarts.

---

## 2. Each member runs their own Google login

Google Calendar, Gmail, and Sheets all read a **per-admin** OAuth token from
`.oauth/{admin_id}_google.json` (or the path in `ADMIN_XX_GOOGLE_TOKEN_PATH`).
There is one shared Google OAuth **client** (`GOOGLE_OAUTH_CLIENT_ID` /
`GOOGLE_OAUTH_CLIENT_SECRET`), but a **separate refresh token file per admin**
— no admin's credentials are ever reused for another admin's writes.

Every family member completes their own consent, either via the API or the
CLI:

**Via API**

```bash
curl http://localhost:8000/admins/admin_01/oauth/google/start
# → { "admin_id": "admin_01", "auth_url": "https://accounts.google.com/..." }
# open auth_url, approve, Google redirects to /oauth/google/callback?state=admin_01
```

```bash
curl http://localhost:8000/admins/admin_01/oauth/status
# → { "admin_id": "admin_01", "google": "connected", "token_path": "...", ... }
```

**Via CLI** (same flow, no server needed)

```bash
python -m life_os.oauth_google --admin-id admin_01
```

Notion uses `ADMIN_XX_NOTION_TOKEN` per admin when set, otherwise falls back
to the shared `NOTION_TOKEN`.

**Mock mode** — set `LIFE_OS_USE_MOCK_CONNECTORS=1` (the default) to run the
full graph, roster, and HITL flow without any admin completing OAuth; every
connector returns deterministic fake ids instead of making network calls.

---

## 3. HITL routing (`HITL_POLICY`)

Set via `HITL_POLICY=any_of|primary` (roster-wide, in `.env.local`); resolved
per-request in [`life_os/hitl.py`](life_os/hitl.py):

- **`any_of` (default)** — every `owner` and `operator` is @mentioned on the
  Slack approval request; any one of them reacting approves or denies the
  run. There is no single `approval_assignee` under this policy (any of them
  may act), so it resolves to `None`.
- **`primary`** — only the roster `owner` is @mentioned and is the
  `approval_assignee`.
- **`round_robin`** — documented for a future release (rotate the primary
  assignee among owners); **not implemented yet** — falls back to `primary`
  today.

If Slack is unreachable, unset, or times out, HITL falls back to a CLI
`y/N` prompt (`HITL_FALLBACK_CLI=1`, the default).

**Approval never changes whose tokens are used for writes.** A run's
`admin_id` (the requester, set when the run was created) stays fixed for the
lifetime of the run. Approving a run only records who approved it
(`POST /runs/{id}/approve` with the approver's `admin_id`); a subsequent
`send_gmail` / calendar write still authenticates as the original requester,
never the approver.

---

## 4. Audit trail

Every run appends one row to the Sheets audit log
([`life_os/agents/auditor.py`](life_os/agents/auditor.py) →
[`life_os/tools/sheets.py`](life_os/tools/sheets.py)) containing:

- `family_id`, `run_id`
- `admin_id` — the requester whose tokens performed the writes
- `approver` / `approval_assignee` — who approved (or was assigned to
  approve) the run, if it needed HITL
- `oauth_account` — the requester's connected Google account email, when
  known
- `status`, `apps_touched`, `errors`, `timestamp`

Writes are idempotent per `(admin_id, key)` — see
[`life_os/idempotency.py`](life_os/idempotency.py) — so retries never repeat
a Calendar event, Gmail send, or Sheets append for the same admin.

---

## 5. Tests

- [`tests/orchestrator/test_admins.py`](tests/orchestrator/test_admins.py) —
  roster cap, unknown `admin_id`, viewer denial, `any_of` mention/assignee
  resolution, per-admin OAuth token paths.
- [`tests/orchestrator/test_api.py`](tests/orchestrator/test_api.py) — API
  enforcement: unknown `admin_id` on create/approve, viewer denied on
  approve, admin roster full, idempotent run creation.
- [`tests/orchestrator/test_auditor.py`](tests/orchestrator/test_auditor.py)
  — audit row carries `family_id`, `approver`, `approval_assignee`,
  `oauth_account`.

```bash
pytest tests/orchestrator/test_admins.py tests/orchestrator/test_api.py tests/orchestrator/test_auditor.py -q
```

---

## Out of scope (this branch)

- Real Life OS JWT login (beyond `admin_id` + OAuth connect)
- Quorum approval (2-of-N)
- Frontend roster / OAuth UI
- Per-user Slack user OAuth (a family bot + @mention is enough)
