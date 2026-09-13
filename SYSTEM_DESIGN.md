# Life OS — System Design

> **Architecture anchor.** How the app is built, how data moves, how agents coordinate, how we fail safely.  
> Product/requirements: [`PRD.md`](./PRD.md) · Event: [`Hackathon.md`](./Hackathon.md)  
> **Status:** Design locked for hackathon v1 (meeting / life-admin vertical)

---

## 1. Design goals

| Goal | Design consequence |
|------|--------------------|
| Outcome → side effects | Graph runs to **tool writes**, not chat text |
| Multi-agent clarity | Named nodes with single responsibilities |
| Multi-app reality | Thin adapters; orchestration stays in LangGraph |
| Reliability is scored | Auditor + checkpoints + eval hooks are first-class |
| 6-hour ship | One vertical path fully live; other life domains are extension seams |

**Non-goals (v1):** local desktop control, always-on schedulers, hundreds of connectors, auto-send without HITL.

---

## 2. System context

```
┌──────────────┐     trigger      ┌─────────────────────────────────────────────┐
│ Human / Demo │ ───────────────► │                 Life OS                      │
│ CLI / API/UI │ ◄── receipt ──── │  LangGraph orchestrator + tool adapters     │
└──────────────┘   / HITL ask     └───────┬──────────┬──────────┬───────┬───────┘
                                          │          │          │       │
                                          ▼          ▼          ▼       ▼
                                       Gmail     Calendar    Notion   Slack
                                          │                              │
                                          └──────────► Sheets (audit) ◄──┘
```

**Life OS sits between the human and their apps.** The human states an outcome (or supplies a signal). Life OS plans, acts, asks only when irreversible, and leaves an auditable receipt.

---

## 3. Logical architecture (layers)

```
┌────────────────────────────────────────────────────────────┐
│ L5  Interface     CLI · (optional) FastAPI/Streamlit UI    │
├────────────────────────────────────────────────────────────┤
│ L4  Orchestration LangGraph Life Orchestrator + checkpointer│
├────────────────────────────────────────────────────────────┤
│ L3  Agents        Intake Priority Planner Scheduler        │
│                   Executor Critic Auditor                  │
├────────────────────────────────────────────────────────────┤
│ L2  Tools         LangChain tools wrapping app adapters    │
├────────────────────────────────────────────────────────────┤
│ L1  Adapters      Gmail · Calendar · Notion · Slack · Sheets│
├────────────────────────────────────────────────────────────┤
│ L0  Platform      LLM provider · secrets · logging · env   │
└────────────────────────────────────────────────────────────┘
```

**Rule:** Agents never call vendor SDKs directly. They call **tools**; tools call **adapters**. That keeps the graph testable with fakes.

---

## 4. Repository / module layout (target)

```text
life_os/
  __main__.py              # CLI entry: run / resume / demo
  config.py                # env, thresholds, feature flags
  state.py                 # LifeState (TypedDict / Pydantic)
  graph/
    builder.py             # compiles StateGraph
    edges.py               # routing predicates
    nodes/
      intake.py
      priority.py
      planner.py
      scheduler.py
      executor.py
      critic.py
      auditor.py
  tools/
    gmail.py
    calendar.py
    notion.py
    slack.py
    sheets.py
  adapters/                # raw API clients + auth
    google_auth.py
    notion_client.py
    slack_client.py
  policies/
    safety.py              # what requires HITL
    idempotency.py
  evals/
    fixtures/
    runners.py
  fixtures/
    sample_meeting_email.json
tests/
docs/                      # optional; root MDs are canonical for hackathon
```

Hackathon note: folders may start flatter; **names and boundaries** matter more than perfect packaging on day one.

---

## 5. Control plane — LangGraph

### 5.1 Pattern

**Linear specialist pipeline** with **conditional edges** and a **HITL interrupt**, not a free-form ReAct soup.

```
START
  → intake
  → priority
  → planner
  → scheduler          # may no-op if no time-bound steps
  → executor           # prepares / performs safe writes; stages irreversible drafts
  → critic             # pass | need_hitl | abort | retry_planner
       ├─ need_hitl → interrupt → (human) → critic/executor resume
       ├─ retry     → planner (bounded)
       ├─ abort     → auditor → END
       └─ pass      → auditor → END
```

### 5.2 Why this shape

| Alternative | Why not (for us) |
|-------------|------------------|
| Single ReAct agent | Hard to explain, hard to eval, muddy reliability brief |
| Full swarm handoffs | Too much nondeterminism for a 2-min demo |
| Pure supervisor fan-out | Overkill until multi-intent batching (glow-up) |

This pipeline is **legible on a slide** and still “multi-agent system design.”

### 5.3 Node contracts

| Node | Reads (state) | Writes (state) | Side effects |
|------|---------------|----------------|--------------|
| **intake** | `trigger` | `intents[]`, `normalized_context` | none |
| **priority** | `intents[]` | `priority_scores`, `selected_intent` | none |
| **planner** | `selected_intent`, context | `plan_steps[]` | none |
| **scheduler** | `plan_steps` | `calendar_actions[]`, tool_results | Calendar R/W |
| **executor** | `plan_steps`, approvals | `drafts[]`, `execution_receipts[]` | Notion, Slack; Gmail draft |
| **critic** | drafts, scores, policies | `status`, `needs_approval`, `errors` | none (routing only) |
| **auditor** | full state | `audit_ref` | Sheets append |

### 5.4 Routing predicates (edges)

| From → To | Predicate |
|-----------|-----------|
| intake → priority | `len(intents) > 0` else auditor (empty run) |
| priority → planner | always (selected_intent set; may be low-confidence) |
| planner → scheduler | any step `requires_calendar` else skip→executor |
| scheduler → executor | calendar success **or** soft-fail with `calendar_skipped` |
| executor → critic | always |
| critic → interrupt | `needs_approval == True` |
| critic → planner | `status == retry` AND `retry_count < max` |
| critic → auditor | `status in {pass, abort}` OR post-HITL continue |
| auditor → END | always |

**Bounded retries:** `max_planner_retries = 1` in Tier 0–1.

### 5.5 Checkpointing & resume

| Tier | Checkpointer | Resume behavior |
|------|-------------|-----------------|
| 0 | `MemorySaver` | Same process HITL via CLI y/n |
| 1–2 | `MemorySaver` or SQLite | Resume thread_id after Slack/CLI approval |
| Glow | Postgres / cloud | Multi-session life memory |

Every run has `thread_id == run_id` for LangGraph persistence.

---

## 6. Data plane — `LifeState`

Canonical shared state (implement as `TypedDict` or Pydantic model).

```python
# Conceptual schema — source of truth for the graph
LifeState = {
  "run_id": str,
  "thread_id": str,
  "created_at": str,          # ISO8601
  "trigger": {
    "type": "goal" | "email" | "slack",  # slack = glow
    "raw": str | dict,
    "source_id": str | None,  # message-id / fixture id
  },
  "normalized_context": dict,
  "intents": [
    {
      "id": str,
      "type": "meeting" | "task" | "follow_up" | "info",
      "summary": str,
      "entities": dict,       # people, times, links
      "confidence": float,
    }
  ],
  "priority_scores": dict,    # intent_id -> score breakdown
  "selected_intent": dict | None,
  "plan_steps": [
    {
      "id": str,
      "action": str,          # create_event | create_notion | draft_email | notify_slack
      "app": str,
      "args": dict,
      "requires_hitl": bool,
      "status": "pending" | "done" | "skipped" | "blocked",
    }
  ],
  "calendar_actions": list,
  "drafts": list,             # especially outbound email
  "approvals": {              # key -> "approved" | "rejected" | "pending"
  },
  "tool_results": list,       # append-only tool IO traces
  "execution_receipts": list, # ids/urls of created artifacts
  "errors": list,
  "retry_count": int,
  "status": "running" | "needs_approval" | "pass" | "abort" | "error",
  "needs_approval": bool,
  "audit_ref": str | None,    # Sheets row / URL
}
```

### 6.1 State invariants

1. **Append-only traces:** `tool_results` and `errors` only grow.  
2. **Single selected intent** in v1 demo path (multi-intent = glow-up).  
3. **No silent success:** a tool failure must append to `errors` and mark step status.  
4. **HITL keys** are stable: e.g. `email_send:{draft_id}`.

---

## 7. Agent design (behavioral)

### 7.1 Intake
- **Input:** goal string or email fixture/raw MIME-ish JSON.  
- **LLM task:** extract intents + entities; do not invent meetings without evidence.  
- **Output:** `intents[]` with confidences.  
- **Failure:** unparseable → `info` intent + low confidence → critic will HITL or abort softly.

### 7.2 Priority
- **Rubric (deterministic weights + LLM tie-break):**
  - Deadline proximity  
  - External human waiting  
  - Irreversibility of likely actions  
  - Confidence of extraction  
- **Output:** `selected_intent` + score breakdown in logs (reliability brief loves this).

### 7.3 Planner
- Produces **ordered**, **tool-bound** steps only from an allowlist of actions.  
- Must mark `requires_hitl` for send-email.  
- Prefer: Calendar → Notion brief → Slack receipt → (optional) Gmail draft.

### 7.4 Scheduler
- Reads free/busy if available; else creates event from extracted window.  
- On conflict: write `propose_only` alternate into state (Tier 2); Tier 0 may create if clear.

### 7.5 Executor
- Executes **non-HITL** steps immediately.  
- Stages HITL steps as `drafts` without sending.  
- Posts Slack **run receipt** (what happened / what’s waiting).

### 7.6 Critic
- Policy engine + optional LLM double-check.  
- Hard rules in `policies/safety.py` beat the model.  
- Sets `needs_approval` or `abort` with reason codes.

### 7.7 Auditor
- Always runs on terminal paths.  
- Writes one Sheets row (or Notion DB row fallback): run_id, status, apps touched, artifact links, error codes.  
- This is the spine of the **reliability brief**.

---

## 8. Integration design

> **Canonical connector rules, OAuth scopes, permissions, and per-app checklists:** [`CONNECTORS.md`](./CONNECTORS.md).

### 8.1 Adapter interface

Every adapter exposes a small surface:

```text
healthcheck() -> bool
execute(action, args, idempotency_key) -> ToolResult
```

`ToolResult = { ok, data, external_id, raw_error }`

### 8.2 App map (v1)

| App | Actions | Auth | Notes |
|-----|---------|------|-------|
| **Gmail** | `fetch_fixture` / `create_draft` / `send` | Google OAuth | `send` HITL-only |
| **Calendar** | `create_event` / `list_busy` | Google OAuth | primary demo write |
| **Notion** | `create_page` | Internal integration token | meeting brief |
| **Slack** | `post_message` / `request_approval` | Bot token | receipt + HITL channel |
| **Sheets** | `append_row` | Google OAuth / service | audit log |

### 8.3 Idempotency

| Resource | Key |
|----------|-----|
| Calendar event | `cal:{run_id}:{intent_id}` stored in description/extended props if possible |
| Notion page | title includes `run_id` OR store mapping in Sheets |
| Slack receipt | `slack:{run_id}:receipt` — skip if already posted (best-effort) |
| Sheets audit | one row per `run_id` (update if exists — Tier 2; append Tier 0 OK) |

### 8.4 Secrets

Canonical templates: [`.env.example`](./.env.example) (committed) · `.env.local` (gitignored).

```text
# Active (v1 LLM)
GEMINI_API_KEY=
GEMINI_MODEL_NAME=gemini-3.6-flash

# Integrations — uncomment / fill as adapters land
GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GOOGLE_OAUTH_TOKEN_PATH=
NOTION_TOKEN=
NOTION_DATABASE_ID=
NOTION_PARENT_PAGE_ID=
SLACK_BOT_TOKEN=
SLACK_CHANNEL_ID=
SHEETS_SPREADSHEET_ID=
```

---

## 9. Sequence — happy path (demo)

```
User/CLI                Graph                 Calendar   Notion   Slack   Sheets
   |                      |                      |         |        |       |
   |-- run(email fix) --> |                      |         |        |       |
   |                      | intake→priority→plan |         |        |       |
   |                      |-- create_event ----->|         |        |       |
   |                      |<-- event_id ---------|         |        |       |
   |                      |-- create_page ---------------->|        |       |
   |                      |<-- page_url -------------------|        |       |
   |                      |-- draft_email (no send)        |        |       |
   |                      |-- post receipt ------------------------>|       |
   |                      |-- critic: need_hitl (send?)             |       |
   |<-- approve? ---------|                      |         |        |       |
   |-- yes -------------->| send email (opt)     |         |        |       |
   |                      |-- append audit -------------------------------->|
   |<-- final receipt ----|                      |         |        |       |
```

**2-minute demo script maps 1:1 to this sequence.**

---

## 10. Failure modes & reliability

| Failure | Detection | Behavior |
|---------|-----------|----------|
| LLM returns garbage intents | schema validation | soft abort → Auditor |
| Calendar API 403/429 | adapter error | mark step failed; continue Notion/Slack if possible; status=error partial |
| Notion down | adapter error | keep calendar write; Slack explains partial |
| Slack down | adapter error | CLI HITL fallback |
| User rejects HITL | approval=rejected | skip send; still audit |
| Duplicate re-run | idempotency keys | no double event (best-effort) |
| Mid-run crash | checkpointer | resume from last node with same `run_id` |

**Partial success is a first-class outcome:** `status=pass` with `errors[]` non-empty is allowed if core demo artifacts exist; Auditor records `partial`.

### 10.1 Observability

- Structured logs per node: `run_id`, `node`, `latency_ms`, `status`  
- `tool_results` dumpable as JSON for the reliability brief  
- Optional LangSmith tracing if key present (glow / free tier)

### 10.2 Evaluation harness

| Fixture | Assert |
|---------|--------|
| `meeting_clear.json` | calendar_actions≥1, notion page, slack receipt, audit row |
| `meeting_ambiguous.json` | needs_approval or propose_only; no silent send |
| `not_a_meeting.json` | no calendar create; clean abort/info path |

---

## 11. Trust & safety architecture

```
Executor stages action
        │
        ▼
 Critic applies policy matrix
        │
        ├─ safe & high confidence → allow
        ├─ irreversible / low conf → HITL interrupt
        └─ forbidden (delete, bulk spam) → abort
```

| Action class | Examples | Gate |
|--------------|----------|------|
| **Safe write** | Notion page, Sheets row, Slack receipt | Auto |
| **Reversible write** | Calendar create (user can delete) | Auto if confidence ≥ τ |
| **Irreversible** | Gmail send | HITL always |
| **Forbidden** | Delete, forward chains, scrape contacts spam | Hard abort |

Default τ (confidence threshold): **0.7** (config).

---

## 12. Interface design

### 12.1 CLI (Tier 0 — required)

```bash
python -m life_os run --fixture fixtures/sample_meeting_email.json
python -m life_os run --goal "Schedule a 30m sync with Alex next Tue afternoon and note it in Notion"
python -m life_os resume --run-id <id> --approve email_send:<draft_id>
```

### 12.2 Optional HTTP (Tier 2)

`POST /runs` `{ trigger }` → `{ run_id, status, receipts[] }`  
`POST /runs/{id}/approve` `{ key }`  

Enough for a Vercel/Railway “try it” if time remains.

---

## 13. Deployment topology (hackathon)

| Mode | Topology |
|------|----------|
| **Default** | Local Python process; OAuth tokens on disk; demo from laptop |
| **Optional live** | Single web process + env secrets; no separate worker queue in v1 |
| **Not now** | Kubernetes, message buses, multi-tenant auth |

Async long-running Computer-style jobs are a **future** topology; v1 is request/run scoped.

---

## 14. Extension seams (life-wide, not built today)

Design so the PRD’s “entire life” ambition is honest without expanding scope:

| Domain | New intent types | Extra tools |
|--------|------------------|-------------|
| Tasks / chores | `task` | Todoist/Trello |
| Expenses | `expense` | Sheets ledger + Gmail receipts |
| Travel | `travel` | Calendar + Notion itinerary |
| Care admin | `case` | Notion case file + mandatory HITL |

Add domains by **new planner templates + tools**, not by forking the graph.

---

## 15. Tech stack choices

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Language | Python 3.11+ | LangGraph ergonomics |
| Orchestration | `langgraph` + `langchain` | Multi-agent + tools |
| Schema | Pydantic v2 | Validation at node boundaries |
| Google APIs | google-api-python-client / google-auth | Gmail, Calendar, Sheets |
| Notion | official SDK / HTTP | Simple pages |
| Slack | slack-sdk | Bot posts |
| Config | pydantic-settings + `.env.local` | Gemini first; expand per adapter |
| LLM | Google Gemini (`GEMINI_API_KEY`, `GEMINI_MODEL_NAME`) | Hackathon default model stack |
| Tests | pytest | Fixture evals |

---

## 16. Build order mapped to architecture

| Order | Ship | Maps to |
|------|------|---------|
| 1 | `LifeState` + graph skeleton (stub nodes) | Control plane |
| 2 | Adapters with dry-run/fake mode | Data plane testability |
| 3 | Calendar + Notion + Slack + Sheets live | Multi-app writes |
| 4 | Intake/Planner LLM prompts | Intelligence |
| 5 | Critic policies + CLI HITL | Safety |
| 6 | Auditor + fixtures + brief | Reliability score |
| 7 | Gmail draft/send | Full vertical |
| 8 | UI / deploy / glow | Tier 2–3 only |

---

## 17. Architecture decision records (ADR-lite)

| ID | Decision | Status |
|----|----------|--------|
| ADR-1 | Pipeline specialists over free ReAct | Accepted |
| ADR-2 | Shared `LifeState` as only cross-agent bus | Accepted |
| ADR-3 | Adapters behind tools | Accepted |
| ADR-4 | Sheets as durable audit for judges | Accepted |
| ADR-5 | HITL mandatory for email send | Accepted |
| ADR-6 | One intent per run in v1 | Accepted |
| ADR-7 | Memory checkpointer first | Accepted |

---

## 18. Open design risks

| Risk | Mitigation |
|------|------------|
| Google OAuth time sink | Fixture email + live Calendar/Notion/Slack/Sheets first |
| Slack app approval delay | CLI HITL fallback |
| LLM flaky JSON | Pydantic repair loop once; then abort |
| Demo nondeterminism | Golden fixture + idempotent re-run |

---

## 19. Doc ownership

| Change type | Update |
|-------------|--------|
| Product scope / tiers / judging | [`PRD.md`](./PRD.md) |
| Graph, state, adapters, failures | **This file** |
| Event rules | [`Hackathon.md`](./Hackathon.md) |

---

## 20. Working notes

_Add implementation deviations here so the design doc stays truthful._

-
