# Life OS — Multi-App AI Agent Hackathon

Hackathon hosted by [Lemma](https://multiappagenthackathon.com/) and Comma Capital · September 2026  
Repo: [SaurabhVelankar/multi-app-ai-agent-hackathon](https://github.com/SaurabhVelankar/multi-app-ai-agent-hackathon)

**Life OS** is a LangGraph-orchestrated multi-agent system that turns a life outcome into coordinated actions across the apps people already live in — with human-in-the-loop approvals where it matters, and an audit trail for everything.

Inspired by the *outcome → sub-agents → apps* shape of [Perplexity Computer](https://www.perplexity.ai/help-center/en/articles/13837784-what-is-computer), scoped for a one-day ship.

---

## For judges — start here

### Demo video (2 minutes)

| | |
|--|--|
| **File** | [`Final Submissions/hackathon_submission_video.mp4`](./Final%20Submissions/hackathon_submission_video.mp4) |
| **On GitHub** | [Open the video in the repo](https://github.com/SaurabhVelankar/multi-app-ai-agent-hackathon/blob/main/Final%20Submissions/hackathon_submission_video.mp4) |

**What the video shows**
1. Life OS operations cockpit (trigger → multi-agent pipeline → side effects)
2. Shared / multi-user sandbox worlds (per-admin inbox & calendar)
3. End-to-end run: goal in → actions across apps → audit trail
4. Human-in-the-loop posture for irreversible actions (e.g. email send)

### What to expect from this submission

| Deliverable | Where |
|-------------|--------|
| Working project | This repository (`main`) |
| 2-minute demo | Video path above |
| System & reliability | [`SYSTEM_DESIGN.md`](./SYSTEM_DESIGN.md), [`EVALS.md`](./EVALS.md), [`CONNECTORS.md`](./CONNECTORS.md) |

**Product in one line:** a multi-step agent that plans and acts across **≥3 apps** (Gmail, Calendar, Notion, Slack, Sheets) for shared life/family ops — not a chatbot wrapper.

**Default demo mode:** connectors use a deterministic **sandbox** (`LIFE_OS_USE_MOCK_CONNECTORS=1`) so judges can reproduce without OAuth. Live Google/Notion is supported when mocks are off ([`FAMILY_ADMIN.md`](./FAMILY_ADMIN.md)).

**Quick try (optional):** see [Setup](#setup-windows-cmd--recommended) below → API `:8000` + UI `:3000` → **Start run**, or open `/sandbox` for multi-user worlds.

---

## How it works

You give it a **goal** ("schedule a sync with Sarah next week") or forward an **email**, and it runs through a fixed pipeline of specialist steps — a LangGraph state machine, not a free-form chat agent:

```
trigger (goal / email)
   │
   ▼
 intake      → pulls out intent(s): what does this actually ask for?
   ▼
 priority    → scores + picks the one intent to act on
   ▼
 planner     → turns it into concrete steps (create event, draft email, notion page, …)
   ▼
 scheduler   → resolves times / calendar conflicts for any time-bound steps
   ▼
 executor    → performs the safe writes, stages anything irreversible (e.g. an email) as a draft
   ▼
 critic      → decides: pass straight through, or stop for human approval?
   │               │
   │ pass           needs_approval
   ▼               ▼
   │           human approves/denies (Slack or CLI) → resumes
   ▼               ▼
 auditor     → logs the outcome (who, what, which apps, errors) to the audit trail
   ▼
 done (pass / needs_approval / abort / error)
```

Every step of a run carries an `admin_id` — whichever family member triggered it — and app writes always use *that* person's connected accounts, even if someone else approves the HITL step. See [`FAMILY_ADMIN.md`](./FAMILY_ADMIN.md) for the multi-admin/approval model and [`EVALS.md`](./EVALS.md) for how this pipeline is tested end-to-end.

---

## Current app state (read this first)

| Area | Status | Notes |
|------|--------|--------|
| **Orchestrator** | Working | LangGraph pipeline — see [How it works](#how-it-works) above |
| **API** | Working | FastAPI on `:8000` — `POST /runs`, `GET /runs/{id}`, `POST /runs/{id}/approve`, `GET /health` |
| **Frontend** | Working | Next.js cockpit in [`web/`](./web/) on `:3000` |
| **LLM** | **Gemini (default)** | `LLM_PROVIDER=gemini`, model `gemini-3.6-flash` — needs `GEMINI_API_KEY` in `.env` |
| **Connectors** | **Mock + sandbox by default** | Per-user worlds under `sandbox/` — live OAuth optional |
| **Live integrations** | Supported | `LIFE_OS_USE_MOCK_CONNECTORS=0` + Google/Notion tokens |
| **Demo video** | Done | [`Final Submissions/hackathon_submission_video.mp4`](./Final%20Submissions/hackathon_submission_video.mp4) |
| **Evals / reliability** | Present | [`EVALS.md`](./EVALS.md) + `tests/` |

**What “Start run → pass” means today:** the **graph + Gemini + mock tools** completed successfully. It does **not** mean a real Gmail/Notion/etc. object was created unless mocks are off and credentials are set.

---

## Docs

| Doc | Purpose |
|-----|---------|
| [`PRD.md`](./PRD.md) | Product requirements + tiers |
| [`SYSTEM_DESIGN.md`](./SYSTEM_DESIGN.md) | Architecture |
| [`CONNECTORS.md`](./CONNECTORS.md) | OAuth, scopes, adapter rules |
| [`contracts/openapi.yaml`](./contracts/openapi.yaml) | Frontend ↔ API contract |
| [`Hackathon.md`](./Hackathon.md) | Event / judging |
| [`sandbox/README.md`](./sandbox/README.md) | Per-user Gmail/Calendar sandbox data (Shared Life OS) |

---

## Prerequisites

- **Python 3.11+** (3.9 will fail; on Windows use `py -3.14` or similar)
- **Node.js 18+** + npm (for `web/`)
- A **Gemini API key**

---

## Setup (Windows CMD — recommended)

Open **Command Prompt** (not PowerShell) unless you know `$env:` syntax.

### 1) Clone & enter repo

```bat
cd /d C:\Users\HP\Desktop\Multi_App_Agent_Hackathon
git pull origin main
```

### 2) Python venv (use 3.11+)

```bat
py -3.14 -m venv .venv
.venv\Scripts\python.exe --version
```

Must show **3.11+**. Prefer calling `.venv\Scripts\python.exe` directly (Activate is flaky on Windows).

### 3) Install backend

```bat
.venv\Scripts\python.exe -m pip install -U pip
.venv\Scripts\python.exe -m pip install -e ".[dev,integrations]"
```

### 4) Env files (backend)

Backend loads **`.env`**, then **`.env.local`** (overrides).

```bat
copy .env.example .env
```

Edit **`.env`** and set at least:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL_NAME=gemini-3.6-flash
LIFE_OS_USE_MOCK_CONNECTORS=1
```

Never commit `.env` / `.env.local`.

### 5) Start API (leave this window open)

```bat
.venv\Scripts\python.exe -m uvicorn life_os.api:app --reload --port 8000
```

Check: http://localhost:8000/health → `{"status":"ok"}`

### 6) Frontend (new CMD window)

```bat
cd /d C:\Users\HP\Desktop\Multi_App_Agent_Hackathon\web
copy .env.example .env.local
npm install
npm run dev
```

`web/.env.local` should contain:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_USE_MOCKS=false
```

Open: http://localhost:3000 → **Start run** with the sample goal.

---

## Setup (macOS / Linux)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev,integrations]"
cp .env.example .env
# edit .env — Gemini key + LIFE_OS_USE_MOCK_CONNECTORS=1

uvicorn life_os.api:app --reload --port 8000
```

```bash
cd web
cp .env.example .env.local
npm install
npm run dev
```

---

## How to play / smoke-test

1. Cockpit shows `api: http://localhost:8000 · up`
2. Click **Start run** (Goal tab) → pipeline should move to **done**, status **pass** (or **needs_approval** if HITL fires)
3. **Side effects** lists mock receipts (calendar / notion / slack / gmail / sheets)
4. Optional CLI:

```bat
set LIFE_OS_HITL_AUTO=approve
.venv\Scripts\python.exe -m life_os --fixture meeting_email.json
```

5. Tests:

```bat
.venv\Scripts\python.exe -m pytest tests\integrations tests\orchestrator -q
```

### UI-only (no Python)

In `web/.env.local` set `NEXT_PUBLIC_USE_MOCKS=true`, then `npm run dev`. Uses in-browser fake `LifeState` (not the real graph).

---

## Repo layout

```text
life_os/                 # Python package — graph, agents, tools, adapters, API
web/                     # Next.js operations cockpit + /sandbox UI
sandbox/                 # Per-user seed data for connectors
contracts/               # openapi.yaml + connector contracts
tests/                   # orchestrator, integrations, evals
Final Submissions/       # Judge demo video
PRD.md / EVALS.md …      # planning & reliability docs
```

---

## Team notes

- **Agent split:** see [`skeleton.md`](./skeleton.md) / [`WORKFLOW.md`](./WORKFLOW.md)
- **Mock → live connectors:** set `LIFE_OS_USE_MOCK_CONNECTORS=0` and fill Google / Notion / Slack vars ([`CONNECTORS.md`](./CONNECTORS.md)); restart API
- **Anthropic (optional):** `LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` (not the default anymore)
- If `python --version` shows 3.9 after activate, you’re on the wrong interpreter — use `.venv\Scripts\python.exe`

---

## License

MIT — see [`LICENSE`](./LICENSE).
