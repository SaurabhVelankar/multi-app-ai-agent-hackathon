# Life OS — Multi-App AI Agent Hackathon

Hackathon hosted by [Lemma](https://multiappagenthackathon.com/) and Comma Capital · September 2026  
Repo: [SaurabhVelankar/multi-app-ai-agent-hackathon](https://github.com/SaurabhVelankar/multi-app-ai-agent-hackathon)

**Life OS** is a LangGraph-orchestrated multi-agent system that turns a life outcome into coordinated actions across the apps people already live in — with human-in-the-loop approvals where it matters, and an audit trail for everything.

Inspired by the *outcome → sub-agents → apps* shape of [Perplexity Computer](https://www.perplexity.ai/help-center/en/articles/13837784-what-is-computer), scoped for a one-day ship.

---

## Docs (start here)

| Doc | Purpose |
|-----|---------|
| [`PRD.md`](./PRD.md) | **Product anchor** — requirements, tiers, success bar |
| [`SYSTEM_DESIGN.md`](./SYSTEM_DESIGN.md) | **Architecture anchor** — graph, state, adapters, failures |
| [`Hackathon.md`](./Hackathon.md) | Event brief, judging, team constraints |
| [`ideas.md`](./ideas.md) | Idea backlog (Life OS locked) |

**Build rule:** Tier 0 → Tier 1 functional path before any glow-ups. See PRD §7.

---

## Environment setup

```bash
cp .env.example .env.local
# then edit .env.local — start with Gemini:
#   GEMINI_API_KEY=...
#   GEMINI_MODEL_NAME=gemini-2.5-flash
```

| File | Commit? | Purpose |
|------|---------|---------|
| [`.env.example`](./.env.example) | Yes | Template for the team |
| `.env.local` | **No** | Your real keys (gitignored) |
| [`.gitignore`](./.gitignore) | Yes | Keeps secrets, venvs, tokens out of git |

We load from `.env.local` (preferred) or `.env`. More integration vars will land in `.env.example` as we wire Gmail / Calendar / Notion / Slack / Sheets.

---

## Target stack

- **Orchestration:** LangChain + LangGraph (multi-agent graph)
- **Agents:** Intake · Priority · Planner · Scheduler · Executor · Critic · Auditor
- **Apps (free/freemium):** Gmail · Google Calendar · Notion · Slack · Google Sheets (audit)
- **Demo vertical:** Meeting / life-admin happy path

---

## Status

- [x] Repo + license
- [x] PRD / hackathon / ideas anchors
- [ ] Tier 0 critical infra (runnable graph + ≥3 app writes)
- [ ] Tier 1 demo-complete + reliability brief
- [ ] 2-minute demo

---

## License

MIT — see [`LICENSE`](./LICENSE).
