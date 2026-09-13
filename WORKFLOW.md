# Life OS — Codebase Workflow & App Connections

> Companion to [`PRD.md`](./PRD.md). Maps how a run moves through the graph, which apps we wire, and how **Admin** scales from 1 → **10 people**.

---

## 1. End-to-end run (happy path)

```
Trigger (goal | email fixture | chat)
        │
        ▼
┌───────────────────┐
│  Life OS entry    │  CLI / API / optional web UI
│  create run_id    │  load LifeState + checkpointer
└─────────┬─────────┘
          ▼
┌───────────────────┐
│  Intake           │  Normalize → intents[]
└─────────┬─────────┘
          ▼
┌───────────────────┐
│  Priority         │  Rank by deadline / people / irreversibility
└─────────┬─────────┘
          ▼
┌───────────────────┐
│  Planner          │  Ordered plan_steps[] bound to tools
└─────────┬─────────┘
          ▼
┌───────────────────┐
│  Scheduler        │  Calendar propose/create + conflict check
└─────────┬─────────┘
          ▼
┌───────────────────┐
│  Executor         │  Notion · Gmail drafts · Slack posts
└─────────┬─────────┘
          ▼
┌───────────────────┐
│  Critic           │  Confidence + policy → pass | HITL | abort
└─────┬─────────┬───┘
      │         │ needs_approval
      │         ▼
      │    HITL interrupt (CLI confirm or Slack react)
      │         │
      ▼         ▼
┌───────────────────┐
│  Auditor          │  Append run trace → Sheets
└─────────┬─────────┘
          ▼
         END
```

**Demo narrative:** messy meeting email → rank → book Calendar → write Notion brief → Slack approval for reply draft → log to Sheets.

---

## 2. Codebase workflow (suggested layout)

Target package shape for Tier 0+ (names can flex; responsibilities should not).  
**Build split:** three parallel agents — see [`skeleton.md`](./skeleton.md).

| Agent | Owns | Graph stages |
|-------|------|--------------|
| **1 — Orchestrator** | `graph`, `state`, `api`, Intake · Priority · Planner · Critic | Plan + gate |
| **2 — Integrations** | `connectors/**`, Scheduler · Executor · Auditor, HITL channels | Writes + audit |
| **3 — Frontend** | `web/**` | Trigger · timeline · Approve/Deny UI |

```
life_os/
├── __main__.py          # Agent 1 — python -m life_os … entry
├── api.py               # Agent 1 — FastAPI
├── graph.py             # Agent 1 — LangGraph compile + edges
├── state.py             # Agent 1 — LifeState
├── config.py            # Agent 1 — env, Admin roster (≤10)
├── agents/
│   ├── intake.py        # Agent 1
│   ├── priority.py      # Agent 1
│   ├── planner.py       # Agent 1
│   ├── critic.py        # Agent 1
│   ├── scheduler.py     # Agent 2
│   ├── executor.py      # Agent 2
│   └── auditor.py       # Agent 2
├── connectors/          # Agent 2 — one module per external app
│   ├── gmail.py
│   ├── calendar.py
│   ├── notion.py
│   ├── slack.py
│   └── sheets.py
├── hitl.py              # Agent 2 — CLI / Slack approval interrupt
└── fixtures/            # Agent 1 — sample email JSON, golden goals

web/                     # Agent 3 — Next.js UI only
contracts/
├── openapi.yaml         # Agent 1 ↔ 3
└── connectors.md        # Agent 2 edits; Agent 1 ACK
```

### Node → state contract

| Stage | Reads | Writes |
|-------|-------|--------|
| Intake | `trigger` | `intents[]` |
| Priority | `intents[]` | `priority_scores{}` |
| Planner | top intents + scores | `plan_steps[]` |
| Scheduler | time-bound steps | `calendar_actions[]`, `tool_results` |
| Executor | remaining steps | `drafts[]`, Notion/Slack `tool_results` |
| Critic | drafts + confidence | `approvals{}`, `status`, `needs_approval` |
| Auditor | full `LifeState` | Sheets row; run `status` terminal |

Minimum `LifeState` (from PRD):

```text
run_id, trigger, intents[], priority_scores{},
plan_steps[], calendar_actions[], drafts[],
approvals{}, tool_results{}, errors[], status
```

### Graph edges (routing)

| Edge | Condition |
|------|-----------|
| Intake → Priority | intents non-empty |
| Priority → Planner | confidence ≥ threshold **or** Admin forced |
| Planner → Scheduler | plan has time-bound steps |
| Scheduler → Executor | calendar OK / skipped |
| Executor → Critic | always |
| Critic → HITL | irreversible pending (e.g. Gmail send) |
| Critic → Auditor | pass **or** after HITL resolve |
| Any failure → Auditor → END | safe failure still audited |

**Checkpointing:** memory for Tier 0; SQLite glow-up. Resume after HITL without redoing prior tool calls.

---

## 3. Apps to connect

All v1 connectors are **free/freemium**. Hard bar: **≥3 real writes** on the happy path.

| App | Why it’s in the graph | Auth | Agent(s) | Write policy |
|-----|----------------------|------|----------|--------------|
| **Gmail** | Intake signal + draft/send replies | Google OAuth | Intake (read), Executor (draft/send) | Draft OK; **send = HITL** |
| **Google Calendar** | Propose/create meeting blocks; conflicts | Google OAuth | Scheduler | Create if high confidence; else propose only |
| **Notion** | Life notes / task / meeting brief | Notion integration token | Executor | Create page/row allowed |
| **Slack** | Approvals + run receipt to Admins | Slack bot (workspace) | Executor, HITL, Auditor notify | Post receipt allowed; react = approve/deny |
| **Google Sheets** | Audit / reliability evidence | Google OAuth | Auditor | **Always** append run row |

### Recommended live writes for demo

**Calendar + Notion + Slack + Sheets** (Gmail live draft preferred; mock inbox fixture OK if OAuth burns time).

### Connector checklist (build order)

1. **Sheets** — Auditor always runs; proves reliability early  
2. **Calendar** — visible side effect for judges  
3. **Notion** — second durable write  
4. **Slack** — HITL + receipt (also Admin fan-out)  
5. **Gmail** — live draft; send only behind approval  

### Trust matrix (unchanged at any Admin scale)

| Action | Policy |
|--------|--------|
| Create Calendar event | Allowed if confidence high; else propose |
| Create Notion page/row | Allowed |
| Post Slack receipt | Allowed |
| Append Sheets audit | Always |
| **Send Gmail** | **HITL required** |
| Delete anything | Forbidden (hackathon) |

---

## 4. Admin scaling (1 → 10 people)

Life OS v1 demos as a single operator. Product design includes an **Admin roster** so the same graph can serve a small team or household — **capped at 10 Admins**.

### What an Admin is

An **Admin** is a person authorized to:

- Trigger runs (goal / email / chat)
- Receive Slack HITL prompts and resolve approvals
- View audit rows for runs they own or are shared into
- (Optional) Force Priority → Planner when confidence is low

Admins are **not** separate agent personas. They are humans in the loop around one shared orchestrator.

### Scale model

| Mode | Admins | Behavior |
|------|--------|----------|
| **Solo** (hackathon default) | 1 | All HITL + receipts → one Slack user / CLI |
| **Small team** | 2–5 | Shared workspace; approvals routed by policy |
| **Full Admin cap** | **≤ 10** | Hard limit in config; refuse add beyond 10 |

```text
ADMIN_MAX = 10
admins[] = { admin_id, name, slack_user_id, email, role, scopes[] }
```

### Suggested roles (within the 10)

| Role | Count guidance | Powers |
|------|----------------|--------|
| **Owner** | 1 | Full; manage Admin roster |
| **Operator** | ≤ 9 | Trigger runs; approve HITL in scope |
| **Viewer** *(optional)* | counts toward 10 | Audit read-only; no send approval |

Total of Owner + Operator + Viewer **must be ≤ 10**.

### HITL routing when N > 1

| Policy | When to use |
|--------|-------------|
| **Primary Admin** | Default: first Admin in roster gets Slack interrupt |
| **Round-robin** | Spread load across Operators |
| **Any-of** | First react wins (good for demo / on-call) |
| **Quorum** *(glow-up)* | 2-of-N for send email — only if time allows |

Hackathon Tier 0–1: implement **Primary Admin** + optional **Any-of**. Document Round-robin / Quorum as scale path.

### Per-Admin isolation (keep simple)

Extend `LifeState` when multi-Admin is on:

```text
admin_id, shared_with[], approval_assignee
```

| Concern | Approach |
|---------|----------|
| Triggers | Tag run with `admin_id` of requester |
| Calendar / Gmail / Notion | Use that Admin’s OAuth tokens (or shared service account + ACL) |
| Slack | DM assignee **or** post to `#life-os-approvals` and @mention |
| Sheets audit | Column `admin_id` (+ optional `shared_with`) on every row |
| Idempotency | Key on `(admin_id, message_id | run_id)` so re-demos don’t collide across people |

### Config sketch (`.env` / `config.py`)

```bash
# Solo (demo)
ADMIN_IDS=admin_01
ADMIN_01_NAME=Demo User
ADMIN_01_SLACK=U_XXXX
ADMIN_01_EMAIL=you@example.com
ADMIN_01_ROLE=owner

# Scale example (≤10)
# ADMIN_IDS=admin_01,admin_02,...,admin_10
ADMIN_MAX=10
HITL_POLICY=primary   # primary | any_of | round_robin
```

### What does *not* change at 10 Admins

- Same LangGraph nodes and edges  
- Same five app connectors  
- Same Critic policies (send still HITL; delete still forbidden)  
- Same Auditor → Sheets requirement  

Only **who can trigger**, **who must approve**, and **whose credentials/apps** are used.

---

## 5. Trigger → apps map (meeting / life-admin vertical)

| Trigger | Intake produces | Typical writes |
|---------|-----------------|----------------|
| Meeting email fixture | `meeting`, `follow_up` | Calendar event, Notion brief, Slack receipt, Sheets row; Gmail draft (+ HITL send) |
| Pasted goal (“prep for X”) | `task`, `info` | Notion task/page, optional Calendar block, Slack + Sheets |
| Slack mention *(glow-up)* | same as goal | Same path; Admin = mentioning user if in roster |

---

## 6. Idempotency & failure

- Re-run with same `run_id` / message id → **no double Calendar/Notion creates**  
- Failed tool → structured `errors[]`; **Auditor still runs**  
- Critic abort → status `aborted`; audit row explains why  
- Multi-Admin: scope idempotency keys with `admin_id`

---

## 7. Tier alignment (what to build when)

| Tier | Workflow focus | Apps | Admin scale |
|------|----------------|------|-------------|
| **0** | Full graph + stubs OK; one E2E path | ≥3 live writes | Solo (1 Admin) |
| **1** | Real OAuth ×3+; goal + email triggers; HITL | Prefer Calendar · Notion · Slack · Sheets | Solo; config ready for roster |
| **2** | Conflicts, eval harness, checkpoint resume | Harden connectors | Optional 2–3 Admins + Any-of HITL |
| **3** | Timeline UI, batch intents, schedule | Extra channels | Roster UI up to **10**; quorum |

---

## 8. Quick reference — connection inventory

| # | App | Required for demo? | Notes |
|---|-----|--------------------|-------|
| 1 | Google Calendar | **Yes** (recommended) | Scheduler writes |
| 2 | Notion | **Yes** (recommended) | Executor writes |
| 3 | Slack | **Yes** (recommended) | Receipt + HITL; Admin fan-out |
| 4 | Google Sheets | **Yes** (Auditor) | Reliability evidence |
| 5 | Gmail | Prefer live draft | Send only with Admin approval |

**Admin cap:** configure **1–10** people; enforce `ADMIN_MAX=10` in code so the product stays a small trusted circle, not an unbounded org tool.

---

## 9. Decision notes

| Decision | Choice |
|----------|--------|
| Orchestration | LangChain + LangGraph |
| Shared truth | One `LifeState` per run |
| Demo vertical | Meeting / life-admin |
| App set | Gmail · Calendar · Notion · Slack · Sheets |
| Multi-user | Admin roster, **hard max 10** |
| HITL default at scale | Primary Admin (Any-of optional) |
