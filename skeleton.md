# Life OS — Parallel Work Skeleton (3 Agents)

> Ground rules for **three people / three agents** building Life OS at the same time.  
> Anchors: [`PRD.md`](./PRD.md) · [`WORKFLOW.md`](./WORKFLOW.md)  
> Goal: ship Tier 0–1 without merge fights.

---

## 1. Locked tech stack

Do **not** swap these without all three agreeing in chat + updating this file.

| Layer | Choice | Notes |
|-------|--------|-------|
| Language (backend) | **Python 3.11+** | Graph + API + connectors |
| Orchestration | **LangChain + LangGraph** | Named agent nodes only |
| API surface | **FastAPI** | Frontend talks only to this |
| Frontend | **Next.js (App Router) + TypeScript** | Deploy-ready; Vercel-friendly |
| UI styling | **Tailwind CSS** | Keep UI thin |
| State / types contract | **`contracts/openapi.yaml`** | FE ↔ Orchestrator airlock |
| Connector contract | **`contracts/connectors.md`** | Orchestrator ↔ Integrations airlock |
| Config | **`.env` / `.env.example`** | No secrets in git |
| Package mgmt (BE) | **`pyproject.toml` or `requirements.txt`** | Orchestrator owns root Python deps |
| Package mgmt (FE) | **`web/package.json` (npm)** | Frontend owns |
| Tests | **pytest** | Split by folder — see §3 |
| Checkpointer (Tier 0) | **Memory** | SQLite = glow-up only |
| Apps | Gmail · Calendar · Notion · Slack · Sheets | Integrations owns live SDKs |

**Out of stack for hackathon:** microservices, Redis, heavy ORMs, Electron, local filesystem agents.

---

## 2. Three-agent map (simultaneous tracks)

```
                    contracts/openapi.yaml
                            │
         ┌──────────────────┼──────────────────┐
         ▼                  ▼                  ▼
   ┌───────────┐     ┌─────────────┐     ┌───────────┐
   │ Agent 1   │     │  Agent 2    │     │ Agent 3   │
   │ Orchestrator│◄──►│ Integrations│     │ Frontend  │
   │ (brain)   │     │ (hands)     │     │ (cockpit) │
   └─────┬─────┘     └──────┬──────┘     └─────┬─────┘
         │                  │                  │
         ▼                  ▼                  ▼
   life_os/graph     life_os/connectors      web/
   life_os/agents/   + write agents          UI only
   (read/plan/gate)  + HITL Slack/CLI
```

| | **Agent 1 — Orchestrator** | **Agent 2 — Integrations** | **Agent 3 — Frontend** |
|--|---------------------------|----------------------------|------------------------|
| **Mission** | LangGraph brain + FastAPI + `LifeState` | Real app writes + HITL channels | Demo UI: trigger, timeline, approve |
| **Owns directories** | `life_os/graph.py`, `state.py`, `api.py`, `__main__.py`, `config.py`, `fixtures/`, `agents/intake.py`, `priority.py`, `planner.py`, `critic.py`, `tests/orchestrator/` | `life_os/connectors/**`, `hitl.py`, `agents/scheduler.py`, `executor.py`, `auditor.py`, `tests/integrations/` | `web/**` |
| **LangGraph nodes** | Intake · Priority · Planner · Critic | Scheduler · Executor · Auditor | — (displays node status only) |
| **Apps** | Calls connector **interfaces** only (stubs OK day one) | Gmail · Calendar · Notion · Slack · Sheets — live SDKs | Never calls app SDKs |
| **Tier 0** | Graph compiles; stub→real node handoff; `POST/GET /runs`; CLI entry | ≥3 live writes on happy path; Sheets audit; Slack/CLI HITL | Goal input, run timeline, HITL buttons against mocks |
| **Tier 1** | Idempotent run_id; errors in state; approve route resumes graph | OAuth hardened; conflict detect; fixture email→writes | Wire live API; Admin roster UI (≤10) |
| **Does not touch** | `web/**`, `connectors/**` implementations | `web/**`, `graph.py` edges, read-only agent files | `life_os/**`, `tests/**` |
| **Demo fallback** | `python -m life_os` with connector stubs | Print-mock → flip to live without changing graph API | `NEXT_PUBLIC_USE_MOCKS=true` |

---

## 3. Repo layout (ownership walls)

```
multi-app-ai-agent-hackathon/
├── contracts/                      # SHARED — sequential ACK (§5)
│   ├── openapi.yaml                # FE ↔ Agent 1
│   └── connectors.md               # Agent 2 edits; Agent 1 ACK only
├── life_os/
│   ├── __main__.py                 # Agent 1
│   ├── api.py                      # Agent 1
│   ├── graph.py                    # Agent 1  (wires nodes; imports Agent 2 funcs)
│   ├── state.py                    # Agent 1  (LifeState — contract-aligned)
│   ├── config.py                   # Agent 1  (incl. ADMIN_MAX=10)
│   ├── hitl.py                     # Agent 2
│   ├── agents/
│   │   ├── intake.py               # Agent 1
│   │   ├── priority.py             # Agent 1
│   │   ├── planner.py              # Agent 1
│   │   ├── critic.py               # Agent 1
│   │   ├── scheduler.py            # Agent 2
│   │   ├── executor.py             # Agent 2
│   │   └── auditor.py              # Agent 2
│   ├── connectors/                 # Agent 2 ONLY
│   │   ├── gmail.py
│   │   ├── calendar.py
│   │   ├── notion.py
│   │   ├── slack.py
│   │   └── sheets.py
│   └── fixtures/                   # Agent 1 (sample email / goals)
├── web/                            # Agent 3 ONLY
│   ├── package.json
│   ├── app/
│   ├── components/
│   ├── lib/                        # API client + mocks
│   └── public/
├── tests/
│   ├── orchestrator/               # Agent 1
│   └── integrations/               # Agent 2
├── .env.example                    # Agent 2 proposes keys; Agent 1 merges to file
├── PRD.md / WORKFLOW.md / skeleton.md
└── README.md                       # Agent 1 owns root; others use sub-READMEs
```

**Hard rules**

1. Agent 3 never edits `life_os/**` or `tests/**`.  
2. Agent 2 never edits `web/**`, `graph.py`, `state.py`, or Agent 1 agent files.  
3. Agent 1 never edits `web/**`, connector **bodies**, or `contracts/connectors.md` — read/import signatures only.  
4. If Agent 1 needs a new tool call: **propose** the signature in chat → both ACK → **Agent 2 edits** `contracts/connectors.md` → Agent 2 implements → Agent 1 wires.

---

## 4. Parallel day-one split (no waiting)

### Agent 1 — Orchestrator

1. Define `LifeState` + stub all 7 nodes (pass-through OK for Scheduler/Executor/Auditor).  
2. Compile LangGraph; CLI: `python -m life_os --fixture meeting_email.json`.  
3. FastAPI: `POST /runs`, `GET /runs/{id}`, `POST /runs/{id}/approve`, `GET /health`.  
4. Critic sets `needs_approval` for Gmail send / low confidence.  
5. Import Agent 2 functions when ready — swap stubs without changing edges.

### Agent 2 — Integrations

1. Scaffold `connectors/*` with the signatures in `contracts/connectors.md`.  
2. Live writes: **Calendar · Notion · Slack · Sheets** (Gmail draft if time).  
3. Implement `scheduler.py` / `executor.py` / `auditor.py` against those connectors.  
4. HITL: Slack react **or** CLI confirm → result Agent 1 can resume on.  
5. Document required env vars; send list to Agent 1 for `.env.example`.

### Agent 3 — Frontend

1. Next.js scaffold under `web/`.  
2. Goal paste + “Start run”.  
3. Run timeline (Intake → … → Auditor) from mock `LifeState`.  
4. HITL Approve / Deny panel.  
5. Admin roster UI stub (1–10 slots; disable add at 10).  
6. Flip `NEXT_PUBLIC_USE_MOCKS=false` when Agent 1 API is up.

All three work the **entire** build window in parallel once §5 contracts are frozen (~first 30–60 min).

---

## 5. Shared contracts (the only merge hotspots)

### A. `contracts/openapi.yaml` — Agent 1 ↔ Agent 3

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/runs` | `{ trigger_type, trigger_payload, admin_id? }` → `{ run_id, status }` |
| `GET` | `/runs/{run_id}` | Full snapshot (`LifeState` + node trace) |
| `POST` | `/runs/{run_id}/approve` | `{ decision: approve\|deny, admin_id }` |
| `GET` | `/health` | Liveness |

`LifeState` minimum fields: match PRD + `admin_id?`, `needs_approval?`.

**Change protocol:** propose → **Agent 1 + Agent 3 ACK** → implement. Agent 2 only cares if audit/HITL fields change.

### B. `contracts/connectors.md` — Agent 1 ↔ Agent 2

**Sole file editor: Agent 2.** Agent 1 may propose signatures but must not commit edits to this file.

Freeze function names + args early. Example surface:

```text
create_calendar_event(run_id, title, start, end, idempotency_key) -> tool_result
create_notion_page(run_id, title, body, idempotency_key) -> tool_result
post_slack_receipt(run_id, text) -> tool_result
request_slack_approval(run_id, summary) -> approval_request_id
append_sheets_audit(run_id, life_state_row) -> tool_result
draft_gmail_reply(run_id, thread_id, body) -> draft
send_gmail(run_id, draft_id) -> tool_result   # Critic/HITL gated only
```

**Change protocol:** Agent 1 or 2 proposes in chat → **both ACK** → **Agent 2 updates `connectors.md`** → Agent 2 implements → Agent 1 swaps stub import.

### C. Files that more than one agent might touch

| File | Owner | Others |
|------|-------|--------|
| `contracts/openapi.yaml` | Agent 1 (editor) | Agent 3 ACK; Agent 2 notified |
| `contracts/connectors.md` | Agent 2 (editor) | Agent 1 ACK |
| `.env.example` | Agent 1 (merger) | Agent 2 supplies key names |
| `README.md` (root) | Agent 1 | Agent 2 → `life_os/connectors/README.md`; Agent 3 → `web/README.md` |
| `graph.py` | Agent 1 only | Agent 2 never edits edges |
| `state.py` | Agent 1 only | Field adds go through OpenAPI + connectors note |

---

## 6. Git rules (merge-conflict prevention)

1. **Branches**
   - `main` — integrate only at checkpoints  
   - `feat/orch-*` — Agent 1 only  
   - `feat/integ-*` — Agent 2 only  
   - `feat/web-*` — Agent 3 only  
   - `chore/contracts-*` — short-lived; merge before feature branches diverge  

2. **One ownership set per branch.** No cross-directory drive-bys.

3. **Pull `main` often.** Prefer small merges.

4. **No force-push to `main`.**

5. **Lockfiles:** Agent 1 = Python deps; Agent 3 = `web/package-lock.json`; Agent 2 adds Python packages via Agent 1 PR or coordinated edit to requirements (one editor at a time).

6. **Conflict in `contracts/`:** freeze features → fix contract branch → all three pull → resume.

---

## 7. Workflow handoff (who owns which stage of a run)

| Stage | Builder | Runtime role |
|-------|---------|--------------|
| Trigger API / CLI | Agent 1 | Create `run_id`, load state |
| Intake → Priority → Planner | Agent 1 | Intents + plan |
| Scheduler | Agent 2 | Calendar write / propose |
| Executor | Agent 2 | Notion · Gmail draft · Slack |
| Critic | Agent 1 | Pass / HITL / abort |
| HITL interrupt | Agent 2 (Slack/CLI) + Agent 3 (UI approve) + Agent 1 (resume graph) | Irreversible gate |
| Auditor | Agent 2 | Sheets row |
| Timeline display | Agent 3 | Poll `GET /runs/{id}` |

See [`WORKFLOW.md`](./WORKFLOW.md) §2 for the full graph; this table is the **build** split of that same path.

---

## 8. Admin scale (1 → 10) — split cleanly

| Concern | Agent 1 | Agent 2 | Agent 3 |
|---------|---------|---------|---------|
| Cap | `ADMIN_MAX=10` in `config.py` | Pass `admin_id` into audit/Slack | UI max 10 rows; disable Add at 10 |
| Identity | `admin_id` on `LifeState` + API | Sheets column + Slack @assignee | Send `admin_id` on create/approve |
| HITL policy | Resume graph on approve | Primary / Any-of Slack routing | Approve/Deny when `needs_approval` |
| OAuth | Knows which admin’s tokens to select | Stores/uses tokens in connectors | No secrets in browser |

---

## 9. Definition of done (3-way integration)

- [ ] Agent 1: graph + API run with fixtures  
- [ ] Agent 2: ≥3 live app writes + Sheets audit on that run  
- [ ] Agent 3: UI creates run, shows timeline, Approve/Deny works  
- [ ] HITL: UI **or** Slack approval resumes without redoing prior tools  
- [ ] Admin: at least solo path; roster UI respects max 10  

Until then: merge to `main` only inside your walls.

---

## 10. Communication cheat sheet

| Event | Who | Message |
|-------|-----|---------|
| New `LifeState` field | Agent 1 | “OpenAPI + state: add `X` — A2/A3 ACK?” |
| New connector fn | Agent 2 (sole editor of file) | “connectors.md: add `Y` — A1 ACK?” |
| Need new tool call | Agent 1 proposes; **does not edit file** | “Need `Y(args)` — ACK? A2 updates connectors.md” |
| OAuth live | Agent 2 | “Calendar+Notion+Sheets live; A1 can drop stubs” |
| API up | Agent 1 | “`/runs` live on :8000; A3 drop mocks” |
| UI blocked | Agent 3 | Paste expected JSON; ask A1 to match OpenAPI |
| Demo −30 min | All | Freeze contracts; A2 live writes; A3 screenshare; A1 CLI backup |

---

## 11. Anti-patterns (will cause conflicts)

- Two agents editing the same `agents/*.py` file  
- Frontend calling Google/Notion/Slack SDKs  
- Orchestrator embedding raw SDK calls inside Intake/Planner (belongs in connectors)  
- Integrations rewriting `graph.py` edges “just to test”  
- Duplicating types in TS and Python with no OpenAPI  
- Root-level `package.json`  
- Expanding past **10 Admins** without a product decision  

---

**Summary:** Agent 1 = brain + API · Agent 2 = app hands + audit/HITL channels · Agent 3 = cockpit. Directory walls + two contracts (`openapi.yaml`, `connectors.md`) keep three parallel streams merge-safe.
