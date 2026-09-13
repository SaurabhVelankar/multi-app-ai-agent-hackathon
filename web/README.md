# Life OS — Frontend (`web/`)

Next.js App Router cockpit for the Life OS orchestrator API.

## What it does

- Start a run from a **goal** or **email fixture**
- Poll run state and show the **pipeline + plan steps**
- **Approve / Deny** HITL gates
- Show **execution receipts** / tool results / audit ref
- Family roster from `GET /admins` (roles, Google connect status, max 10)
- Per-admin Google OAuth start via `GET /admins/{id}/oauth/google/start`
- HITL approve/deny with role checks (owner/operator only); token owner stays the run requester

Aligned with shared-LifeOS backend fields: `family_id`, `admin_id`, `shared_with`, `approval_assignee`.

Contract: [`../contracts/openapi.yaml`](../contracts/openapi.yaml) · [`../FAMILY_ADMIN.md`](../FAMILY_ADMIN.md)

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
