# Multi-App AI Agent Hackathon — Anchor

> Living doc for **what this hackathon is**. Edit as we learn more.  
> Product/build ideas live in `[ideas.md](./ideas.md)`.

**Official site:** [multiappagenthackathon.com](https://multiappagenthackathon.com/)

---

## Snapshot


|                |                                      |
| -------------- | ------------------------------------ |
| **What**       | Virtual Multi-App AI Agent Hackathon |
| **When**       | Sunday, September 13, 2026 (Pacific) |
| **Hosted by**  | Lemma · Comma Capital                |
| **Judged by**  | Founders of Arga Labs / Userlens     |
| **Team**       | Us — 2 people (allowed: 1–4)         |
| **Prize pool** | $15,000 cash + interviews for top 3  |


---

## The brief (official)

> Build an AI agent that takes action across multiple external apps.

More precisely:

1. **One** useful, **multi-step** AI agent
2. Connects to **at least three external apps**
3. Show **how you know it works** (reliability / evaluation)

Not: a chatbot that only talks.  
Yes: an agent that **does things** in other products.

---



## Schedule (Pacific)


| Time              | Block               |
| ----------------- | ------------------- |
| 9:00 AM           | Opening             |
| 9:30 AM – 4:00 PM | **Build**           |
| 4:00 – 4:40 PM    | Judging & selection |
| 4:40 – 5:00 PM    | Awards              |


---



## What to submit

- [ ] Working project / repository  
- [ ] **Two-minute** demo  
- [ ] Short **system and reliability** brief  
- [ ] (Optional but nice) Live demo judges can try — e.g. public URL (Vercel-style deploy)

---



## Judging weights


| Weight  | Criterion                | How we interpret it                                           |
| ------- | ------------------------ | ------------------------------------------------------------- |
| **30%** | Technical execution      | Real multi-step agent; ≥3 apps; actions, not just reads       |
| **25%** | Reliability & evaluation | Retries, failure modes, traces, evals, “how we know it works” |
| **20%** | Usefulness               | Everyday customer-facing **or** corporate — both welcome      |
| **15%** | Originality              | Sharp problem + clever glue, not “generic assistant”          |
| **10%** | Demo clarity             | 2-min story a judge can follow instantly                      |




### Judge signals (from us / briefing)

- **Problem space:** Everyday customer-facing problems that feel integral to life are great. Corporate / B2B workflows are equally welcome. **No official preference** on vertical.
- **Live demo:** Highly optional, but a tryable deploy (e.g. Vercel) is a strong differentiator if we can ship it.
- **Paid APIs:** You do **not** have to pay for external app connections. Prefer **free** or **freemium** (day-of usage is fine). Avoid locking the demo behind paid-only APIs.

---

## Our build preference (team)

We are **not** optimizing for a thin single-agent glue script. We want a **big problem** with **serious system design**, even if the demo slice is narrow.

| Preference | Meaning |
|------------|---------|
| **Problem scale** | Workflows that matter at life / org / ops scale — not “nice chatbot helpers” |
| **Multi-agent** | Specialized agents (research, planner, executor, critic, notifier…) coordinated as a system |
| **Orchestration** | **LangChain + LangGraph** as the control plane (graphs, state, checkpoints, human-in-the-loop) |
| **Multi-app** | ≥3 external apps; agents take **real actions** across them |
| **System design first** | Explicit architecture: state schema, routing, retries, idempotency, evals, observability |
| **Integrations** | Free / freemium APIs preferred (day-of freemium OK) |
| **Demo honesty** | 2-min happy path + architecture that clearly *could* run the full system |

**Stack intent:** LangGraph graph(s) · shared typed state · tool nodes per app · supervisor or swarm pattern · checkpointing · reliability brief that maps to graph edges/failure modes.

---

## Non-negotiable constraints (our team)

1. **≥3 external apps** with real actions (create/update/send/post — not only fetch).
2. **Free / freemium** integrations first; paid only if unavoidable and we already have keys.
3. **LangGraph-orchestrated multi-agent** design (not a single monolithic prompt loop).
4. **Reliability story** is half the win — log steps, handle failures, write the brief early.
5. **Demoable in ≤2 minutes** — one happy-path workflow, filmed or live; architecture still looks “big.”
6. Scope for **one build day** — ship a vertical slice of a large system, not a toy one-shot script.

---



## Prizes


| Place | Cash        | Extra                                        |
| ----- | ----------- | -------------------------------------------- |
| 1st   | **$10,000** | Guaranteed interview (Arga Labs or Lemma AI) |
| 2nd   | **$4,000**  | Same                                         |
| 3rd   | **$1,000**  | Same                                         |


---



## Definition of done (hackathon)

- [ ] LangGraph multi-agent system completes one end-to-end workflow across ≥3 apps  
- [ ] Architecture is explicit (state, agents, edges, HITL, failure modes) — even if demo is a slice  
- [ ] Repo runs with clear README + env example (no secrets committed)  
- [ ] Reliability notes: failure cases, retries, evals mapped to the graph  
- [ ] 2-minute demo recorded (or rehearsed live)  
- [ ] Optional: public URL for judges to poke at  

---



## Working notes / updates

*Add clarifications from Discord, judges, or teammates below.*

- Opening / judge Q&A: everyday + corporate both OK; free/freemium APIs preferred; live deploy optional.  
- Team preference: **big problems**, multi-agent, LangChain/LangGraph, heavy system design (see section above).  
- **LOCKED project:** Life OS — see [`PRD.md`](./PRD.md) (Perplexity Computer–inspired; tiered for 4 PM).  
- *(more)*

---



## Links

- Hackathon site: [https://multiappagenthackathon.com/](https://multiappagenthackathon.com/)  
- Ideas backlog: [`ideas.md`](./ideas.md)  
- **Project PRD (locked — Life OS):** [`PRD.md`](./PRD.md)  
- **System design:** [`SYSTEM_DESIGN.md`](./SYSTEM_DESIGN.md)  
- **Connectors / OAuth:** [`CONNECTORS.md`](./CONNECTORS.md)

