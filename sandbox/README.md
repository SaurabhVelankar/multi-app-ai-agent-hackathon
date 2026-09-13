# Life OS — Connector Sandbox

> **What this is:** Fake-but-realistic per-user Gmail/Calendar (plus Notion/Slack/Sheets) data that connectors read/write in mock mode — ready for **Shared Life OS** multi-user.

---

## What it means for the project

| Before | After (sandbox) |
|--------|------------------|
| Mock tools invent random IDs in memory | Tools persist into a **per-user world** under `sandbox/.runtime/` |
| One anonymous demo identity | Users **alex** (`admin-1`) and **jordan** (`admin-2`) |
| Hard to eval “did calendar conflict?” | Jordan already has a busy block Mon 2pm for Sam’s ask |
| Shared Life OS merge needs data shape | Seed + `admin_id` → `user_id` mapping matches multi-user |

**Still not live Google OAuth.** Sandbox ≠ production Gmail. It’s the safe layer between “print mock” and “real APIs.”

When `LIFE_OS_USE_MOCK_CONNECTORS=1` (default), sandbox is **on** automatically.  
Set `LIFE_OS_USE_SANDBOX=0` to fall back to ephemeral mocks.  
Set `LIFE_OS_USE_MOCK_CONNECTORS=0` for real vendor APIs (ignores sandbox writes).

---

## Layout

```text
sandbox/
  manifest.json          # users + eval scenarios
  seed/users/
    alex/                # inbox, calendar, notion, slack, sheets
    jordan/
  .runtime/users/        # copy-on-write mutations (gitignored)
life_os/sandbox/
  store.py               # load/list/create APIs
  __main__.py            # CLI
```

---

## Users

| user_id | admin_id | email |
|---------|----------|-------|
| `alex` | `admin_01` (aliases: `admin-1`) | alex@lifeos.sandbox |
| `jordan` | `admin_02` (aliases: `admin-2`) | jordan@lifeos.sandbox |

Cockpit / Family Admin **admin_01** → Alex’s mailbox/calendar. **admin_02** → Jordan’s.

---

## Scenarios (eval seeds)

| Scenario id | User | Message | Intent |
|-------------|------|---------|--------|
| `meeting_clear` | alex | msg-alex-001 | Clear Q4 meeting ask |
| `meeting_ambiguous` | alex | msg-alex-002 | Vague “sometime” → HITL-ish |
| `not_a_meeting` | alex | msg-alex-003 | Newsletter → no calendar |
| `shared_conflict` | jordan | msg-jordan-001 | Mon 2pm ask vs existing busy |

---

## CLI

```bat
.venv\Scripts\python.exe -m life_os.sandbox list
.venv\Scripts\python.exe -m life_os.sandbox scenario meeting_clear
.venv\Scripts\python.exe -m life_os.sandbox reset
```

`reset` wipes `.runtime` and re-copies seed (clean slate between demos).

---

## How connectors use it

1. Graph runs with `admin_id` (e.g. `admin-1`).
2. Tools resolve `admin_id` → `alex`.
3. Calendar create / Gmail draft / Notion / Slack / Sheets append land in `sandbox/.runtime/users/alex/…`.
4. You can open those JSON files to **see** what the agent did — great for demos and reliability evidence.

---

## Shared Life OS

Teammate’s multi-user branch can keep using:
- `manifest.json` users list
- `resolve_user_id(admin_id=…)`
- same seed paths

Add more users by copying `seed/users/_template` pattern (alex/jordan) and registering in `manifest.json`.
