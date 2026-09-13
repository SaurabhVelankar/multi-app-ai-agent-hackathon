# Life OS — Frontend (`web/`)

Next.js App Router cockpit for the Life OS orchestrator API.

## What it does

- Start a run from a **goal** or **email fixture**
- Poll run state and show the **pipeline + plan steps**
- **Approve / Deny** HITL gates
- Show **execution receipts** / tool results / audit ref
- Admin roster stub (max 10)

Contract: [`../contracts/openapi.yaml`](../contracts/openapi.yaml)

## Setup

```bash
cd web
cp .env.example .env.local
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

### Env

| Variable | Default | Meaning |
|----------|---------|---------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | FastAPI base URL |
| `NEXT_PUBLIC_USE_MOCKS` | `false` | `true` = in-browser mock LifeState (no backend) |

## Talk to the real backend

Terminal A (repo root):

```bash
pip install -e ".[dev,integrations]"
# Windows PowerShell:
$env:LIFE_OS_USE_MOCK_CONNECTORS="1"
uvicorn life_os.api:app --reload --port 8000
```

Terminal B:

```bash
cd web
# NEXT_PUBLIC_USE_MOCKS=false in .env.local
npm run dev
```

## Mock-only UI (no Python)

In `web/.env.local`:

```env
NEXT_PUBLIC_USE_MOCKS=true
```

Then `npm run dev` — Start run → needs_approval → Approve/Deny works entirely in the browser.

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Dev server (Turbopack) |
| `npm run build` | Production build |
| `npm run start` | Serve production build |
| `npm run lint` | ESLint |
