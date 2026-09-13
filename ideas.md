# Ideas — Big Multi-Agent Systems

> **Scale up.** Multi-agent · multi-app · **LangChain + LangGraph** orchestration · system design as the product.  
> Free/freemium integrations preferred.  
> Anchor: [`Hackathon.md`](./Hackathon.md).  
> Mark the locked idea with ✅.

---

## What “bigger” means here

| Thin (we reject) | Big (we chase) |
|------------------|----------------|
| One agent, 3 API calls | **Graph of agents** with roles, handoffs, and shared state |
| “Summarize my inbox” | End-to-end **operating system** for a painful life/org workflow |
| Happy path only | Designed for **failure, retry, HITL, audit, eval** |
| Demo = chat UI | Demo = **orchestrated side effects** across apps + architecture slide |

**Orchestration stack (assumed):** LangGraph (state machine / supervisor / swarm) + LangChain tools/retrievers + checkpointing + optional human-in-the-loop interrupts.

---

## System design template (every idea below)

Use this shape so judges see *architecture*, not just features:

```
Trigger → Intake Agent → Planner Agent → [Worker Agents × N] → Critic/Eval Agent → Executor / Notifier
                ↑________________ state + checkpoints (LangGraph) ________________↑
```

| Layer | Responsibility |
|-------|----------------|
| **State** | Typed shared state: goal, evidence, plan, tool results, approvals, errors |
| **Routing** | Conditional edges: retry, escalate, abort, ask-human |
| **Workers** | One agent (or subgraph) per domain / app cluster |
| **Tools** | Thin adapters to free/freemium APIs (idempotent where possible) |
| **Memory** | Checkpoints + run log (Sheets/Notion as durable audit if needed) |
| **Evals** | Critic agent + golden-path fixtures + “did side effects land?” checks |
| **Observability** | Step traces mapped to graph nodes for the reliability brief |

---

## Free / freemium integration palette

| App | Free-ish use | Role in a big system |
|-----|--------------|----------------------|
| **GitHub** | Free API | Work items, PRs, runbooks-as-code |
| **Gmail** | Google OAuth quota | Intake + outbound comms |
| **Google Calendar** | Same | Scheduling / capacity |
| **Google Sheets** | Same | System of record / audit / metrics |
| **Slack** | Free workspace bots | HITL, alerts, approvals |
| **Discord** | Free bots | Community ops / intake |
| **Notion** | Free personal API | Knowledge base / CRM / SOPs |
| **Linear** | Free small teams | Execution backlog |
| **Trello / Todoist** | Free tiers | Task fan-out |
| **Telegram** | Free Bot API | Mobile trigger / confirm |
| **Resend / Brevo** | Free tier | Transactional mail |
| **Cal.com** | Free | Booking links |

---

## Flagship big ideas

### 1. Life OS — Autonomous Personal Operations Graph
**Problem scale:** People don’t have a chief of staff. Inbox, calendar, tasks, and docs fight each other.  
**Ambient category:** Everyday, integral.

**Multi-agent design (LangGraph):**
| Agent | Job |
|-------|-----|
| **Intake** | Normalize Gmail / Telegram / Slack signals into structured intents |
| **Priority** | Rank by deadlines, people, irreversibility |
| **Scheduler** | Negotiate Calendar capacity; propose blocks |
| **Executor** | Write Notion notes, Todoist/Linear tasks, draft Gmail replies |
| **Critic** | Block low-confidence auto-sends; demand HITL via Slack |
| **Auditor** | Append every decision to Sheets run-log |

**Apps (≥3):** Gmail · Google Calendar · Notion · Slack · Sheets (audit)  
**System-design flex:** Shared `LifeState`; interrupt nodes for approval; idempotent “already scheduled?” checks; eval suite on sample email corpus.  
**2-min demo slice:** One messy email → ranked plan → calendar block + Notion note + Slack approval → Sheets audit row.  
**Why it’s big:** It’s an *operating system*, not a feature.

---

### 2. Incident Command Graph — Always-On Response Room
**Problem scale:** Incidents fail because signal → ticket → comms → postmortem is tribal knowledge.  
**Ambient category:** Corporate / ops (also OSS maintainers).

**Multi-agent design:**
| Agent | Job |
|-------|-----|
| **Signal** | Ingest Slack alert / GitHub issue / email |
| **Triage** | Severity, blast radius, owners |
| **Commander** | Open Linear/GitHub incident; assign roles |
| **Comms** | Status updates to Slack + stakeholder Gmail |
| **Scribe** | Living Notion timeline; Sheets metric ticks |
| **Retro** | After resolve → draft postmortem + action items |

**Apps:** Slack · GitHub/Linear · Notion · Gmail · Sheets  
**System-design flex:** Stateful incident subgraph with phases (`detect → mitigate → resolve → retro`); timeout edges; duplicate-signal suppression; evals: “was severity consistent?”  
**Demo slice:** Inject fake Pager-style Slack message → ticket + war-room thread + Notion timeline + status email draft.  
**Why it’s big:** Classic distributed *command & control* — judges feel production systems.

---

### 3. Hiring / Talent Pipeline Fabric
**Problem scale:** Recruiting is a multi-party state machine (candidate, hiring manager, calendar, CRM) that decays.  
**Ambient category:** Corporate; also campus orgs.

**Multi-agent design:**
| Agent | Job |
|-------|-----|
| **Sourcer** | Parse inbound Gmail / Notion applications |
| **Screener** | Score vs rubric; ask clarifying Qs via email |
| **Coordinator** | Calendar multi-party scheduling |
| **CRM Writer** | Notion/Sheets pipeline stages |
| **Interviewer Ops** | Linear prep tasks + Slack briefings |
| **Fairness Critic** | Flag missing rubric fields / bias-risk patterns |

**Apps:** Gmail · Calendar · Notion · Slack · Linear  
**System-design flex:** Explicit pipeline FSM in LangGraph state; stage gates; human override; evals on rubric completeness.  
**Demo slice:** One application email → scored Notion card → interview hold on Calendar → Slack briefing to “hiring manager.”  
**Why it’s big:** High-stakes workflow + critic agent = reliability theater that matters.

---

### 4. Revenue Intake Fabric — Lead → Qualified → Action
**Problem scale:** Small companies lose money because inbound is chaos.  
**Ambient category:** Corporate / founder ops.

**Multi-agent design:**
| Agent | Job |
|-------|-----|
| **Catcher** | Gmail / form forwards |
| **Researcher** | Public-web + free enrichment only |
| **Qualifier** | ICP score + next-best-action |
| **CRM** | Notion deal room + Sheets funnel metrics |
| **Closer Ops** | Calendar booking (Cal.com) + Slack #sales |
| **Compliance Critic** | Block creepy/overreach outreach |

**Apps:** Gmail · Notion · Slack · Calendar/Cal.com · Sheets  
**System-design flex:** Scoring subgraph; confidence thresholds; “do not contact” list; funnel metrics as first-class state.  
**Demo slice:** Sample lead → research brief → CRM row → booking link → Slack ping.  
**Why it’s big:** Full funnel as a graph, not a Zapier clone narrative.

---

### 5. Knowledge → Action Foundry (Org Brain that *ships work*)
**Problem scale:** Wikis don’t execute. SOPs rot. Work still falls through.  
**Ambient category:** Corporate / communities.

**Multi-agent design:**
| Agent | Job |
|-------|-----|
| **Librarian** | Index Notion / GitHub docs (RAG) |
| **Interpreter** | Map a Slack/Discord ask → matching SOP |
| **Planner** | Break SOP into executable steps |
| **Workers** | Create Linear/GitHub issues, Calendar reminders, Sheets checklists |
| **Verifier** | Confirm artifacts exist; loop until done or escalate |

**Apps:** Notion · Slack/Discord · GitHub/Linear · Calendar · Sheets  
**System-design flex:** Plan–execute–verify loop (classic LangGraph pattern); retrieval evals; “SOP coverage” metrics.  
**Demo slice:** “Onboard contractor X” in Slack → pull Notion SOP → create tickets + calendar + checklist → verify links.  
**Why it’s big:** Turns knowledge into a **closed-loop execution system**.

---

### 6. Household / Shared-Life Coordination Graph
**Problem scale:** Multi-human logistics (roommates, partners, caregivers) — money, chores, schedules, health admin.  
**Ambient category:** Everyday, deeply integral.

**Multi-agent design:**
| Agent | Job |
|-------|-----|
| **Intake** | Telegram/Discord messages + Gmail bills |
| **Allocator** | Fair chore / expense split → Sheets ledger |
| **Scheduler** | Shared Calendar negotiation |
| **Buyer/Ops** | Notion shopping / care lists; reminders |
| **Mediator** | Conflict detection → propose options (HITL) |
| **Auditor** | Weekly digest via email/Slack |

**Apps:** Telegram · Sheets · Calendar · Notion · Gmail  
**System-design flex:** Multi-user identity in state; fairness constraints; weekly batch subgraph.  
**Demo slice:** “Pay rent + buy groceries + move dentist” → split sheet rows + calendar + Notion list + digest.  
**Why it’s big:** Multi-stakeholder coordination is a *hard* systems problem judges respect.

---

### 7. Open-Source Maintainer Command Center
**Problem scale:** Maintainers drown; issues, Discord, releases, docs diverge.  
**Ambient category:** Community + engineering.

**Multi-agent design:**
| Agent | Job |
|-------|-----|
| **Signal Hub** | GitHub issues/PRs + Discord questions |
| **Classifier** | Bug / feature / question / security |
| **Responder** | Draft replies; label; request info |
| **Board** | Notion triage + Linear milestones |
| **Release** | Checklist issues + changelog draft |
| **Health Critic** | Stale PR / unanswered question alarms → Slack |

**Apps:** GitHub · Discord · Notion · Linear · Slack  
**System-design flex:** Priority queues in state; security fast-path edge; maintainer HITL for merges.  
**Demo slice:** New issue + Discord ping → classified labels + Notion card + Slack digest.  
**Why it’s big:** Real maintainer pain; multi-channel orchestration.

---

### 8. Care / Life-Admin Crisis Graph (high empathy, high structure)
**Problem scale:** Navigating medical, insurance, school, or legal admin across email/calendar/docs.  
**Ambient category:** Everyday, high stakes. *(Stay assistive — human always approves irreversible sends.)*

**Multi-agent design:**
| Agent | Job |
|-------|-----|
| **Intake** | Gmail threads + user Telegram notes |
| **Case Manager** | Build Notion case file (timeline, docs needed) |
| **Scheduler** | Calendar appointments + prep blocks |
| **Comms Drafter** | Email drafts only — never auto-send without HITL |
| **Tracker** | Sheets checklist of required actions |
| **Safety Critic** | Hard interrupt on medical/legal claims uncertainty |

**Apps:** Gmail · Notion · Calendar · Sheets · Telegram/Slack  
**System-design flex:** Mandatory approval nodes; conservative critic; audit everything.  
**Demo slice:** Forward insurance email → case file + checklist + draft reply awaiting Slack ✅.  
**Why it’s big:** Shows judgment, safety, and system design under constraint.

---

## Architecture patterns (pick one spine)

| Pattern | When to use | LangGraph shape |
|---------|-------------|-----------------|
| **Supervisor** | Clear “boss” routes to specialists | Supervisor node → worker nodes → back |
| **Swarm / handoff** | Peer experts pass the baton | Agent nodes with transfer tools |
| **Plan–Execute–Critic** | Long workflows needing QA | Planner → execute loop → critic → gate |
| **Hierarchical subgraphs** | Huge domains (incident, hiring) | Parent graph + nested phase graphs |
| **HITL interrupts** | Irreversible actions (email send, money) | `interrupt_before` on executor tools |

**Reliability brief should map 1:1** to: state fields, edges, retry policies, idempotency keys, eval fixtures.

---

## Recommended shortlist (team of 2, big but shippable)

| Rank | Idea | Why |
|------|------|-----|
| ✅ **LOCKED** | **#1 Life OS** | Full PRD: [`PRD.md`](./PRD.md) |
| Backup | **#2 Incident Command Graph** | If Gmail/Calendar OAuth blocks us hard |
| Backup | **#5 Knowledge → Action Foundry** | Alternate spine |

---

## Decision log

| When | Decision | Notes |
|------|----------|-------|
| 2026-09-13 | ✅ Idea locked | **#1 Life OS** — see [`PRD.md`](./PRD.md) |
| 2026-09-13 | LangGraph pattern | Plan → Execute → Critic (+ HITL interrupts) |
| 2026-09-13 | Agent roster (v1) | Intake · Priority · Planner · Scheduler · Executor · Critic · Auditor |
| 2026-09-13 | Three+ apps | Gmail · Calendar · Notion · Slack · Sheets (audit) |
| 2026-09-13 | HITL points | Gmail send + low-confidence irreversible acts |
| 2026-09-13 | Checkpointing / audit store | Memory checkpointer Tier 0; Sheets = durable audit |
| | Deploy (optional) | Tier 2 — only after demo path is green |

---

## Scratchpad

-
