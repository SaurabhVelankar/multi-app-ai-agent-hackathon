# Life OS — Multi-App AI Agent Hackathon

Hackathon hosted by [Lemma](https://multiappagenthackathon.com/) and Comma Capital · September 2026  
Repo: [SaurabhVelankar/multi-app-ai-agent-hackathon](https://github.com/SaurabhVelankar/multi-app-ai-agent-hackathon)

**Life OS** is a LangGraph-orchestrated multi-agent system that turns a life outcome into coordinated actions across the apps people already live in — with human-in-the-loop approvals where it matters, and an audit trail for everything.

Inspired by the *outcome → sub-agents → apps* shape of [Perplexity Computer](https://www.perplexity.ai/help-center/en/articles/13837784-what-is-computer), scoped for a one-day ship.

---

## Current app state (read this first)

| Area | Status | Notes |
|------|--------|--------|
| **Orchestrator** | Working | LangGraph: intake → priority → planner → scheduler → executor → critic → HITL → auditor |
| **API** | Working | FastAPI on `:8000` — `POST /runs`, `GET /runs/{id}`, `POST /runs/{id}/approve`, `GET /health` |
| **Frontend** | Working | Next.js cockpit in [`web/`](./web/) on `:3000` |
| **LLM** | **Gemini (default)** | `LLM_PROVIDER=gemini`, model `gemini-3.6-flash` — needs `GEMINI_API_KEY` in `.env` |
| **Connectors** | **Mock + sandbox by default** | Writes land in `sandbox/.runtime/` per user (alex/jordan) — not live Gmail yet |
| **Live integrations** | Not required to run | Set mock flag to `0` + fill tokens when ready ([`CONNECTORS.md`](./CONNECTORS.md)) |
| **Reliability brief / 2-min demo** | TODO | Next team focus |

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
life_os/           # Python package — graph, agents, tools, adapters, API
web/               # Next.js operations cockpit
contracts/         # openapi.yaml + connector contracts
tests/             # orchestrator + integrations
PRD.md …           # planning docs
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
