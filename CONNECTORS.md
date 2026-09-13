# Life OS — Connectors Playbook

> **Backend integration bible** for humans and coding agents.  
> If you touch Gmail, Calendar, Notion, Slack, Sheets, OAuth, scopes, or adapter code — start here.  
> Product: [`PRD.md`](./PRD.md) · Architecture: [`SYSTEM_DESIGN.md`](./SYSTEM_DESIGN.md) · Env: [`.env.example`](./.env.example)

**Audience:** Teammates + agentic workflows implementing connectors behind LangGraph tools.

---

## 0. TL;DR for coding agents

1. **Never** call vendor SDKs from graph nodes. Nodes → **LangChain tools** → **adapters** → APIs.  
2. Every adapter implements: `healthcheck()`, `execute(action, args, idempotency_key) → ToolResult`.  
3. Secrets live in **`.env.local` only**. Update **`.env.example`** with new *key names* (empty values).  
4. Prefer **least privilege** OAuth scopes. Document every scope you add in this file.  
5. **Gmail send** always requires HITL. Drafts OK without approval.  
6. Demo needs **≥3 real app writes**. Priority order if time-constrained: **Calendar → Notion → Slack → Sheets → Gmail draft**.  
7. Support **`dry_run=True`** so graph work continues without live credentials.  
8. On failure: return `ToolResult(ok=False, …)` — do **not** throw past the tool boundary unless truly unrecoverable.  
9. Use **idempotency keys** on creates. Re-running a demo must not spam duplicate events.  
10. When you change a connector, update: this doc § per-app, `.env.example`, and `SYSTEM_DESIGN.md` if the interface changes.

---

## 1. What a “connector” is

A **connector** is the backend capability that lets Life OS **read/write an external app** on behalf of a user (or a bot).

```
LangGraph node (Scheduler / Executor / Auditor)
        │
        ▼
 LangChain tool (thin, typed args)
        │
        ▼
 Adapter / connector module   ← YOU ARE HERE
        │
        ▼
 Vendor API (OAuth or API token)
```

| Term | Meaning |
|------|---------|
| **Connector / adapter** | Code + auth that talks to one external system |
| **Tool** | LLM/graph-callable wrapper with validated args |
| **Permission / scope** | What the third-party login allows us to do |
| **Consent** | User (or workspace admin) granting those permissions |
| **Dry-run** | Adapter simulates success without calling the network |

---

## 2. Global assumptions

| ID | Assumption |
|----|------------|
| A1 | Hackathon demo uses **our own** Google / Notion / Slack accounts (not multi-tenant SaaS). |
| A2 | **One Google user** covers Gmail + Calendar + Sheets via the same OAuth client + token. |
| A3 | Notion uses an **internal integration** token (not OAuth) for speed. |
| A4 | Slack uses a **bot token** in a free workspace we control. |
| A5 | LLM is **Gemini** (`GEMINI_API_KEY`, `GEMINI_MODEL_NAME`) — unrelated to Google Workspace OAuth. |
| A6 | Free / freemium tiers are enough for one demo day; no paid Google Workspace required. |
| A7 | English-only content for v1 fixtures and demos. |
| A8 | Single-operator demo machine is OK; no production redirect URI farm. |
| A9 | Deletes are **out of scope** — connectors must not expose delete APIs in v1. |
| A10 | Partial success is OK: one adapter failing must not crash the whole run if others succeeded. |

---

## 3. Global constraints

| ID | Constraint |
|----|------------|
| C1 | **No secrets in git** — tokens, client secrets, refresh tokens stay in `.env.local` / `.oauth/`. |
| C2 | OAuth **redirect URI** for local: `http://localhost:8080/` or installed-app / loopback flow. |
| C3 | Minimum **3 live writes** on happy path for judging. |
| C4 | Irreversible actions (email send) → **HITL** before adapter `send`. |
| C5 | Rate limits exist — backoff once; then soft-fail into `ToolResult`. |
| C6 | Do not request sensitive Google scopes we do not need (e.g. full mailbox modify if read+draft+send covers it — still keep send gated). |
| C7 | Connectors must be **idempotent on `idempotency_key`** for create operations where the API allows. |
| C8 | Time zone: store/create Calendar events in **explicit IANA TZ** (default `America/Los_Angeles` for this hackathon unless env overrides). |
| C9 | Agents must not invent connector env vars silently — add them to `.env.example` + this doc. |
| C10 | **Verification / Google OAuth app in Testing mode** is fine: add demo Google accounts as test users. |

---

## 4. Global considerations (design & ops)

1. **Auth setup is the critical path** — start Google Cloud OAuth *before* fancy agent prompts.  
2. **Fixture-first Gmail intake** — don’t block the graph on live inbox if OAuth lags; use `fixtures/sample_meeting_email.json`.  
3. **Same ToolResult shape everywhere** so Critic/Auditor can reason uniformly.  
4. **Log `external_id` + URL** whenever an object is created (event id, page url, message ts, sheet row).  
5. **Prefer create over update** in v1 (simpler demos).  
6. **Human-readable receipts** in Slack beat raw JSON dumps.  
7. **Test users / shared Notion page / Slack channel** — document IDs in `.env.local`, not in chat logs committed to git.  
8. **Consent screens scare judges if broken** — pre-auth tokens before the 2-min demo.  
9. **Scopes are product decisions** — widening scopes needs a note in § changelog below.  
10. **Fake mode** (`LIFE_OS_DRY_RUN=true` or per-adapter flag) keeps CI / teammate laptops working without keys.

---

## 5. Standard adapter contract

All connectors **must** conform.

```python
# Conceptual — implement in life_os/adapters/<app>.py

class ToolResult(TypedDict):
    ok: bool
    action: str
    data: dict          # normalized payload for LifeState
    external_id: str | None
    url: str | None
    raw_error: str | None
    dry_run: bool
    idempotency_key: str | None

class Connector(Protocol):
    name: str  # "gmail" | "calendar" | "notion" | "slack" | "sheets"

    def healthcheck(self) -> bool:
        """True if credentials present and a cheap ping succeeds (or dry_run)."""

    def execute(
        self,
        action: str,
        args: dict,
        *,
        idempotency_key: str | None = None,
        dry_run: bool = False,
    ) -> ToolResult:
        ...
```

### 5.1 Required behaviors

| Behavior | Rule |
|----------|------|
| Unknown `action` | `ok=False`, `raw_error="unknown_action"` |
| Missing credentials | `ok=False`, `raw_error="auth_missing"` (unless `dry_run`) |
| `dry_run=True` | `ok=True`, `dry_run=True`, synthetic `external_id` like `dry_{action}_{key}` |
| Exceptions | Catch vendor errors → `ok=False` with truncated message (no tokens in logs) |
| Timeouts | Cap ~15–30s per call |

### 5.2 Who calls what

| Graph node | Connectors typically used |
|------------|---------------------------|
| Intake | Gmail **fixture/read** (optional live) |
| Scheduler | **Calendar** |
| Executor | **Notion**, **Gmail draft/send**, **Slack** |
| Critic | none (policy only) |
| Auditor | **Sheets** (fallback Notion DB) |

---

## 6. Permission model (product)

| Action class | Examples | Connector may auto-run? |
|--------------|----------|-------------------------|
| Safe write | Notion page, Sheets append, Slack receipt | Yes |
| Reversible write | Calendar event create | Yes if confidence ≥ threshold |
| Irreversible | Gmail **send** | **No — HITL** |
| Forbidden | Delete, trash, ACL changes, mass email | Never expose |

Approval keys (stable): `email_send:{draft_id}`, `calendar_create:{intent_id}` (only if critic forces).

---

## 7. Connector catalog

### 7.1 Gmail

| | |
|--|--|
| **Purpose** | Intake signal (email) + draft/send replies |
| **Auth** | Google OAuth 2.0 (same client as Calendar/Sheets) |
| **Env** | `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GOOGLE_OAUTH_TOKEN_PATH` |
| **API** | Gmail API v1 |

#### Actions (v1)

| Action | Args (core) | HITL | Notes |
|--------|-------------|------|-------|
| `fetch_fixture` | `path` | No | Local JSON — **default intake for demo** |
| `get_message` | `message_id` | No | Optional live read |
| `create_draft` | `to`, `subject`, `body`, `thread_id?` | No | Preferred before send |
| `send` | `draft_id` **or** full message | **Yes** | Critic gate mandatory |
| `send_raw` | — | — | **Do not implement in v1** |

#### Scopes (request only what we use)

| Scope | Why |
|-------|-----|
| `https://www.googleapis.com/auth/gmail.readonly` | Optional live intake |
| `https://www.googleapis.com/auth/gmail.compose` | Drafts + send |

If compose is too broad for comfort mid-hackathon: implement **draft only** and show draft link in demo; send can be simulated after CLI approval without calling API (document as limitation).

#### Assumptions
- Demo inbox may be a dedicated Google account.  
- Intake can be 100% fixture-driven.

#### Constraints
- Never auto-send.  
- Don’t store full message bodies in Sheets audit (truncate / hash).

#### Considerations
- OAuth consent “Gmail” looks scary — pre-consent before judging.  
- Threading: prefer reply-in-thread when `thread_id` exists.

#### Agent implementation checklist
- [ ] Adapter + tool  
- [ ] Fixture loader  
- [ ] Draft create returns `draft_id` + permalink if available  
- [ ] Send blocked unless `approvals[key]==approved`  
- [ ] Dry-run path  

---

### 7.2 Google Calendar

| | |
|--|--|
| **Purpose** | Create meeting blocks; optional free/busy |
| **Auth** | Google OAuth (shared) |
| **Env** | same Google OAuth + `GOOGLE_CALENDAR_ID=primary` |
| **API** | Calendar API v3 |

#### Actions (v1)

| Action | Args | HITL | Notes |
|--------|------|------|-------|
| `list_busy` | `time_min`, `time_max` | No | Tier 2 conflict detection |
| `create_event` | `summary`, `start`, `end`, `timezone`, `description?`, `attendees?` | Usually No | Core demo write |
| `propose_event` | same | No | State-only / description “PROPOSED” — no attendees mail |

#### Scopes

| Scope | Why |
|-------|-----|
| `https://www.googleapis.com/auth/calendar.events` | Create/list events on calendars we access |

Avoid full `calendar` scope unless events scope proves insufficient.

#### Assumptions
- Create on `primary` calendar unless overridden.  
- Default TZ: `America/Los_Angeles` (`LIFE_OS_DEFAULT_TZ` later).

#### Constraints
- Putting attendees on events may **email invite them** — for demo, **omit attendees** or use only our own addresses.  
- Idempotency: put `run_id` / key in `extendedProperties.private` or description line `life_os_key=...`.

#### Considerations
- All-day vs timed: v1 timed only.  
- Conflict detection is Tier 2; don’t block Tier 0.

#### Agent checklist
- [ ] `create_event` live  
- [ ] Store `htmlLink` + `id` in ToolResult  
- [ ] Idempotent re-create guard  
- [ ] No surprise attendee emails  

---

### 7.3 Google Sheets (Auditor)

| | |
|--|--|
| **Purpose** | Durable run audit for reliability story |
| **Auth** | Google OAuth (shared) **or** service account if we add one later |
| **Env** | Google OAuth + `SHEETS_SPREADSHEET_ID` |
| **API** | Sheets API v4 |

#### Actions (v1)

| Action | Args | HITL |
|--------|------|------|
| `append_row` | `values: list` (or keyed dict → fixed column order) | No |
| `ensure_header` | `headers: list` | No |

#### Scopes

| Scope | Why |
|-------|-----|
| `https://www.googleapis.com/auth/spreadsheets` | Append audit rows |

#### Recommended columns

`run_id | timestamp | status | intents | apps_touched | calendar_url | notion_url | slack_ts | errors | dry_run`

#### Assumptions
- One spreadsheet shared with the demo Google account.  
- Tab name `audit` (or first sheet).

#### Constraints
- Don’t write secrets or full email bodies.  
- Tier 0: append-only (duplicates OK); Tier 2: upsert by `run_id`.

#### Considerations
- If Sheets blocked, **fallback Auditor → Notion database row** — keep same logical fields.

---

### 7.4 Notion

| | |
|--|--|
| **Purpose** | Meeting brief / life note as a page |
| **Auth** | Internal integration bearer token |
| **Env** | `NOTION_TOKEN`, `NOTION_PARENT_PAGE_ID` and/or `NOTION_DATABASE_ID` |
| **API** | Notion API |

#### Actions (v1)

| Action | Args | HITL |
|--------|------|------|
| `create_page` | `title`, `body_md` or `blocks`, `parent?` | No |

#### Permissions (Notion-side, not OAuth scopes)
1. Create integration at [notion.so/my-integrations](https://www.notion.so/my-integrations).  
2. **Share** the parent page/database with the integration (critical — easy to forget).  
3. Capabilities: Read content + Insert content (+ Update if needed).

#### Assumptions
- Parent page is a dedicated “Life OS” page.  
- Markdown → simple Notion paragraphs is enough for demo.

#### Constraints
- Token has access **only** to pages explicitly shared.  
- Rate limits ~3 req/s average — irrelevant at demo scale.

#### Considerations
- Database rows look cooler for CRM-like demos; pages are faster to ship.  
- Return `url` in ToolResult for Slack receipt.

---

### 7.5 Slack

| | |
|--|--|
| **Purpose** | Run receipt + HITL approval channel |
| **Auth** | Bot User OAuth Token `xoxb-...` |
| **Env** | `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`, optional `SLACK_SIGNING_SECRET` |
| **API** | Slack Web API |

#### Actions (v1)

| Action | Args | HITL |
|--------|------|------|
| `post_message` | `text`, `blocks?`, `thread_ts?` | No |
| `request_approval` | `text`, `approval_key` | N/A (this *is* the ask) |

#### Bot token scopes (OAuth & Permissions → Bot)

| Scope | Why |
|-------|-----|
| `chat:write` | Post receipts |
| `channels:read` / `groups:read` | Optional resolve channel |
| `app_mentions:read` | Glow-up intake |
| `reactions:read` | Optional emoji-approve HITL |

Invite the bot to `#life-os` (or whatever `SLACK_CHANNEL_ID` points at).

#### Assumptions
- Free Slack workspace.  
- HITL can fall back to **CLI y/n** if Slack isn’t ready.

#### Constraints
- Don’t post tokens or `.env` contents.  
- Keep messages short for the 2-min demo.

#### Considerations
- Interactive buttons need Request URLs (painful on localhost) — prefer **CLI HITL** or emoji reactions for hackathon.  
- `request_approval` may just post “Approve run X key Y in CLI” unless Socket Mode is set up.

---

## 8. Google OAuth setup (shared cookbook)

This unblocks **Gmail + Calendar + Sheets** together.

### 8.1 One-time Cloud setup

1. Google Cloud project (personal is fine).  
2. Enable APIs: **Gmail API**, **Google Calendar API**, **Google Sheets API**.  
3. OAuth consent screen: **External** + **Testing**.  
4. Add **test users** (demo Gmail accounts).  
5. Create OAuth client:  
   - Prefer **Desktop app** for hackathon CLI (simplest loopback).  
   - Or Web app with `http://localhost:8080/`.  
6. Download client JSON → store **outside git** or map into env vars.  
7. Run a one-shot script to obtain `token.json` → `GOOGLE_OAUTH_TOKEN_PATH=.oauth/google_token.json`.

### 8.2 Combined scope string (v1 target)

```text
https://www.googleapis.com/auth/gmail.compose
https://www.googleapis.com/auth/gmail.readonly
https://www.googleapis.com/auth/calendar.events
https://www.googleapis.com/auth/spreadsheets
```

Request incrementally if consent friction appears: **Calendar + Sheets first**, add Gmail when needed.

### 8.3 Token storage rules

| Path | Git? |
|------|------|
| `.oauth/google_token.json` | **Ignored** |
| `client_secret*.json` | **Ignored** |
| `.env.local` | **Ignored** |
| `.env.example` | Committed (names only) |

---

## 9. Env var registry

Keep [`.env.example`](./.env.example) synchronized with this table.

| Variable | Connector | Required for live? |
|----------|-----------|--------------------|
| `GEMINI_API_KEY` | LLM (not a life app) | Yes for real reasoning |
| `GEMINI_MODEL_NAME` | LLM | Yes (default `gemini-2.5-flash`) |
| `GOOGLE_OAUTH_CLIENT_ID` | Gmail/Calendar/Sheets | Yes for Google live |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Gmail/Calendar/Sheets | Yes |
| `GOOGLE_OAUTH_TOKEN_PATH` | Gmail/Calendar/Sheets | Yes |
| `GOOGLE_CALENDAR_ID` | Calendar | Default `primary` |
| `SHEETS_SPREADSHEET_ID` | Sheets | Yes for audit live |
| `NOTION_TOKEN` | Notion | Yes for Notion live |
| `NOTION_PARENT_PAGE_ID` | Notion | Yes (or DB id) |
| `NOTION_DATABASE_ID` | Notion | Optional |
| `SLACK_BOT_TOKEN` | Slack | Yes for Slack live |
| `SLACK_CHANNEL_ID` | Slack | Yes |
| `SLACK_SIGNING_SECRET` | Slack | Only if HTTP interactivity |
| `LIFE_OS_DRY_RUN` | All | Optional `true/false` |
| `LIFE_OS_DEFAULT_TZ` | Calendar | Optional |

---

## 10. Dry-run & offline teammate mode

| Mode | When | Behavior |
|------|------|----------|
| `LIFE_OS_DRY_RUN=true` | No keys / CI | All adapters synthesize success |
| Per-call `dry_run=True` | Tests | Same, scoped |
| Hybrid | Partial keys | Live where `healthcheck()`, dry-run elsewhere; Auditor notes which |

Coding agents: always implement dry-run **before** live calls.

---

## 11. Error taxonomy (shared)

| `raw_error` code | Meaning | Graph hint |
|------------------|---------|------------|
| `auth_missing` | Env/token absent | dry-run or skip app |
| `auth_invalid` | 401/refresh failed | abort app path |
| `forbidden` | 403 scopes / Notion not shared | fix permissions |
| `not_found` | Bad id / channel | config error |
| `rate_limited` | 429 | retry once |
| `validation` | Bad args | planner/critic issue |
| `unknown_action` | Typo / unimplemented | stub |
| `vendor_error` | Everything else | soft-fail |

---

## 12. Idempotency cheat sheet

| Connector | Strategy |
|-----------|----------|
| Calendar | Private extended property or description `life_os_key=...`; search before create |
| Notion | Title prefix `[LifeOS:{run_id}]` OR store mapping in Sheets |
| Slack | Best-effort: include `run_id` in text; skip if recent duplicate (optional) |
| Sheets | Tier 0 append; Tier 2 find `run_id` row and update |
| Gmail draft | Include `run_id` in body footer; don’t recreate if draft_id in state |

---

## 13. Security & privacy

- Strip secrets from logs and Slack.  
- Audit sheet is semi-sensitive — use a dedicated spreadsheet.  
- Don’t commit harvested emails from live Gmail.  
- Rotate tokens if pasted into chat by mistake.  
- Test-mode Google OAuth limits who can auth — feature, not bug.

---

## 14. Build priority for connectors (time box)

| Priority | Connector | Why |
|----------|-----------|-----|
| P0 | Calendar `create_event` | Visible demo write |
| P0 | Notion `create_page` | Visible demo write |
| P0 | Slack `post_message` | Visible demo write |
| P0 | Sheets `append_row` | Reliability story |
| P1 | Gmail `fetch_fixture` + `create_draft` | Full vertical |
| P1 | Shared Google OAuth bootstrap script | Unblocks 3 Google apps |
| P2 | Gmail `send` + HITL | Complete Computer-like loop |
| P2 | Calendar `list_busy` | Conflict intelligence |
| P3 | Slack emoji/button approve | Glow HITL |
| P3 | Live Gmail inbox watch | Glow intake |

---

## 15. Definition of done (per connector)

A connector is “done” when:

1. Adapter implements contract + dry-run.  
2. At least one LangChain tool wired.  
3. Live path works with `.env.local` on a teammate machine.  
4. Failure returns `ToolResult` (no uncaught SDK exceptions in graph).  
5. Section in **this file** matches reality (scopes, env, actions).  
6. `.env.example` has the keys.  
7. One sentence in reliability brief: how we verify the write landed.

---

## 16. Instructions for teammate agentic workflows

When an agent is asked to “add/fix a connector,” it should:

1. Read **this file** + `.env.example` + `SYSTEM_DESIGN.md` §8.  
2. Implement under `life_os/adapters/` and `life_os/tools/`.  
3. Add/adjust unit tests with `dry_run=True`.  
4. Update this playbook if actions/scopes/env change.  
5. Never open a PR/commit that includes `.env.local` or `.oauth/*`.  
6. Prefer smallest scope diff; don’t refactor unrelated agents.  
7. Prove with a one-liner CLI or pytest showing `ToolResult.ok is True`.  
8. If blocked on OAuth UI, ship dry-run + fixture and leave a `## Blockers` note below.

---

## 17. Blockers / working notes

_Teammates: log auth blockers and resolutions here._

| Date | Blocker | Owner | Resolution |
|------|---------|-------|------------|
| | | | |

---

## 18. Changelog

| Date | Change |
|------|--------|
| 2026-09-13 | Initial connectors playbook (Gmail, Calendar, Sheets, Notion, Slack) |

---

## 19. Quick links

- [Gmail API](https://developers.google.com/gmail/api)  
- [Calendar API](https://developers.google.com/calendar/api)  
- [Sheets API](https://developers.google.com/sheets/api)  
- [Notion integrations](https://developers.notion.com/)  
- [Slack Bolt / Web API](https://api.slack.com/apis)  
- [Google OAuth scopes](https://developers.google.com/identity/protocols/oauth2/scopes)
