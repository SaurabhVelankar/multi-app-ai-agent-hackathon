# Life OS — Product Requirements Document

> **Project anchor.** Everything we build points here.  
> Hackathon context: [`Hackathon.md`](./Hackathon.md) · Idea source: [`ideas.md`](./ideas.md)  
> System design: [`SYSTEM_DESIGN.md`](./SYSTEM_DESIGN.md) · Connectors: [`CONNECTORS.md`](./CONNECTORS.md)  
> **Status:** LOCKED — Idea #1 Life OS  
> **Deadline:** Demo-ready by **4:00 PM PT** (build window ends)

---

## 1. One-liner

**Life OS** is a LangGraph-orchestrated multi-agent system that turns a life outcome into coordinated actions across the apps people already live in — with approvals where it matters, and an audit trail for everything.

---

## 2. Inspiration mirror — [Perplexity Computer](https://www.perplexity.ai/help-center/en/articles/13837784-what-is-computer)

We are **not** cloning Computer. We are shipping a **hackathon-scale vertical** of the same *idea*:

| Perplexity Computer | Life OS (our cut) |
|---------------------|-------------------|
| Describe an **outcome**, not a click-path | Same — outcome → plan → agents → apps |
| Spawns **sub-agents** for research, docs, API work | Explicit named agents in a LangGraph |
| Connects Gmail, Calendar, Slack, Notion, GitHub… | **≥3 free/freemium** connectors, real writes |
| Runs long workflows; stays in the loop on sensitive acts | HITL interrupts before irreversible sends |
| Always-on / scheduled digital worker | Tier-0: on-demand run; schedule = glow-up |
| Hundreds of connectors + local Mac | Narrow, elegant, **demoable** life slice |

**North-star feel:** “Do my life admin” — not “chat about my life admin.”

---

## 3. Problem

Life fragments across inbox, calendar, tasks, and docs. Humans act as the integration layer: read email → remember context → open calendar → create task → update notes → tell someone. That glue is exhausting, error-prone, and invisible.

**Life OS replaces the human as the integration layer** — with a graph of specialist agents, shared state, and hard gates on irreversible actions.

---

## 4. Users & jobs-to-be-done

| Persona | Job |
|---------|-----|
| **Overloaded individual** (student, founder, IC) | “Turn this mess into a plan and execute the safe parts.” |
| **Judge / demo viewer** | Understand architecture in 30s; see ≥3 apps mutate in 2 min. |

**Primary JTBD:** When life signals arrive (email, chat, a stated goal), Life OS plans and executes across apps so the user only approves what can’t be undone.

---

## 5. Product principles

1. **Outcome-first** — Input is a goal or signal; output is side effects + a receipt.  
2. **Specialists, not a blob** — Intake · Priority · Scheduler · Executor · Critic · Auditor.  
3. **Shared typed state** — One `LifeState` object is the source of truth for the run.  
4. **HITL for irreversible** — Never auto-send email / never auto-delete without approval.  
5. **Auditable by default** — Every decision lands in a run log (Sheets or equivalent).  
6. **Tier ruthlessly** — Critical path ships; glow-ups never block 4 PM.

---

## 6. System design

> **Canonical architecture lives in [`SYSTEM_DESIGN.md`](./SYSTEM_DESIGN.md).**  
> This section is a product-facing summary only.

**Shape:** LangGraph pipeline — Intake → Priority → Planner → Scheduler → Executor → Critic → Auditor — with shared `LifeState`, tool adapters for Gmail / Calendar / Notion / Slack / Sheets, and HITL before irreversible actions (e.g. email send).

**For judges / builders:** layers, node contracts, state schema, sequences, failure modes, idempotency, ADRs → see the system design doc.

---

## 7. Tier plan (6-hour reality)

> **Rule:** Lower tiers are **functional requirements**. Higher tiers are **glow-ups** — polish, breadth, delight. **Never** let a glow-up steal time from Tier 0–1.

### Time box (suggested)

| Window (PT) | Focus |
|-------------|--------|
| Now → 12:00 | Tier 0 — skeleton that runs |
| 12:00 → 2:00 | Tier 1 — full demo path + reliability brief draft |
| 2:00 → 3:15 | Tier 2 — harden + record 2-min demo |
| 3:15 → 3:45 | Buffer / Tier 3 only if green |
| 3:45 → 4:00 | Submit freeze |

---

### Tier 0 — Critical infrastructure *(MUST — functional)*

**Ship or we have nothing.**

| ID | Requirement | Done when |
|----|-------------|-----------|
| F0.1 | Repo runnable (`README`, `.env.example`, one entry command) | `python -m life_os ...` (or equiv) starts a run |
| F0.2 | LangGraph orchestrator with **named nodes** for all 6 agents (stubs OK if they pass state) | Graph compiles; trace shows node order |
| F0.3 | Typed / documented `LifeState` | State visible in logs |
| F0.4 | **One** end-to-end happy path: trigger → plan → **≥3 app writes** | Side effects visible in UIs |
| F0.5 | Critic gate + **HITL path** (CLI confirm or Slack react) for email send / low confidence | Irreversible action blocked without approval |
| F0.6 | Auditor writes a run row/trace to **Sheets** (or Notion DB if Sheets blocked) | Judges can see “how we know it works” |
| F0.7 | Fixture trigger (sample email JSON or pasted goal) so demo doesn’t depend on live inbox luck | Deterministic demo |

**Demo narrative (Tier 0):**  
“Here’s a messy meeting email → Life OS ranks it → books Calendar → writes Notion brief → asks Slack approval for the reply draft → logs everything to Sheets.”

---

### Tier 1 — Demo-complete *(MUST if we want to compete — functional)*

| ID | Requirement | Done when |
|----|-------------|-----------|
| F1.1 | Real OAuth/tools for **at least 3** of: Gmail, Calendar, Notion, Slack, Sheets | Live mutations, not print-mocks |
| F1.2 | Intake handles **both** `goal` text and `email` fixture | Two trigger modes |
| F1.3 | Idempotency: re-running same `run_id` / message id doesn’t double-create events | Safe re-demo |
| F1.4 | Structured errors in state; failed tool ≠ silent success | Error path logged + Auditor still runs |
| F1.5 | Short **system & reliability brief** (1–2 pages) mapped to graph edges | Submit artifact ready |
| F1.6 | 2-minute demo rehearsed (script + screenshare order) | Timed ≤ 2:00 |

---

### Tier 2 — Competitive harden *(SHOULD — still functional, only after Tier 1)*

| ID | Requirement | Done when |
|----|-------------|-----------|
| F2.1 | Priority scoring explained (rubric in brief + in logs) | Not a black box |
| F2.2 | Calendar conflict detection (read busy → propose alt) | Conflict → alternate suggestion |
| F2.3 | Eval harness: ≥3 golden fixtures with assertable side-effect checks | `pytest` or script exits 0 |
| F2.4 | Checkpoint resume after HITL interrupt | Continue without redoing prior tools |
| F2.5 | Optional public URL (FastAPI/Streamlit/Vercel) for judges to paste a goal | Live try link |

---

### Tier 3 — Glow-ups *(NICE — non-blocking, not required for “works”)*

> These improve wow / originality. **Zero of these are functional requirements for submission.**

| ID | Glow-up |
|----|---------|
| G3.1 | Beautiful run timeline UI (node-by-node streaming) |
| G3.2 | Multi-intent batching in one run (“email had 3 asks”) |
| G3.3 | Morning briefing scheduled job |
| G3.4 | Discord/Telegram as alternate intake |
| G3.5 | Voice / mobile trigger |
| G3.6 | Model routing (fast model for intake, strong model for planner) |
| G3.7 | Persistent cross-run memory (“knows my preferences”) |
| G3.8 | Extra life domains (expenses, travel, chores) beyond meeting/admin |
| G3.9 | Brand polish, landing page, animated architecture diagram |
| G3.10 | Local file tools (Perplexity Personal Computer–style) — **explicitly out of hackathon critical path** |

---

## 8. Out of scope (today)

- Building a full Perplexity Computer competitor  
- Local desktop/filesystem control  
- Paid-only APIs as demo blockers  
- Auto-sending email without HITL  
- Supporting every life domain in v1 (we **design** for life-wide; we **demo** meeting/admin vertical)

---

## 9. Success metrics (hackathon)

| Lens | Pass bar |
|------|----------|
| **Technical (30%)** | Live multi-agent graph; ≥3 app actions |
| **Reliability (25%)** | Auditor + HITL + brief + at least one failure story |
| **Usefulness (20%)** | Judges nod at “I’d use this for life admin” |
| **Originality (15%)** | Life OS framing + critic/audit, not Zapier-with-LLM |
| **Demo (10%)** | Crisp 2-minute outcome story |

---

## 10. Deliverables checklist

- [ ] Working repo  
- [ ] `.env.example` (no secrets committed)  
- [ ] System & reliability brief  
- [ ] 2-minute demo  
- [ ] (Optional) Live URL  
- [ ] This PRD kept truthful if scope shrinks  

---

## 11. Decision log

| When | Decision |
|------|----------|
| 2026-09-13 | Locked **Life OS** (#1) as the project |
| 2026-09-13 | Mirror: Perplexity Computer (outcome → sub-agents → apps → HITL) |
| 2026-09-13 | Orchestration: **LangChain + LangGraph** |
| 2026-09-13 | Demo vertical: **meeting / life-admin** path across Gmail · Calendar · Notion · Slack · Sheets |
| 2026-09-13 | Tier rule: F0 → F1 before any G3 glow-up |

---

## 12. Open questions (resolve fast)

1. Which Google Cloud project / OAuth clients do we already have?  
2. Slack workspace ready for a bot?  
3. Notion integration token ready?  
4. LLM key for today (whatever freemium/paid we already hold)?  
5. CLI-only demo vs minimal web UI (Tier 2.5)?

---

## 13. Working notes

_Add build discoveries, cut decisions, and API blockers here._

-
