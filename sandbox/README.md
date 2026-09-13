# Life OS — Connector Sandbox

> **What this is:** Fake-but-realistic per-user Gmail/Calendar (plus Notion/Slack/Sheets) data that connectors read/write in mock mode — ready for **Shared Life OS** multi-user.

---

## What it means for the project

| Before | After (sandbox) |
|--------|------------------|
| Mock tools invent random IDs in memory | Tools persist into a **per-user world** under `sandbox/.runtime/` |
| One anonymous demo identity | **10 users** (`admin_01`–`admin_10`) with distinct inboxes/calendars |
| Hard to eval “did calendar conflict?” | Jordan/Taylor already have busy blocks for conflict scenarios |
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
    alex/ … taylor/      # 10 per-user worlds
  .runtime/users/        # copy-on-write mutations (gitignored)
life_os/sandbox/
  store.py               # load/list/create APIs
  __main__.py            # CLI
```

---

## Users

| user_id | admin_id | email | Seed focus |
|---------|----------|-------|------------|
| `alex` | `admin_01` | alex@lifeos.sandbox | Clear / ambiguous / newsletter |
| `jordan` | `admin_02` | jordan@lifeos.sandbox | Calendar conflict (Mon 2pm) |
| `sam` | `admin_03` | sam@lifeos.sandbox | Irreversible board email (HITL) |
| `riley` | `admin_04` | riley@lifeos.sandbox | Family school pickup |
| `morgan` | `admin_05` | morgan@lifeos.sandbox | Info-only / promo / receipts |
| `casey` | `admin_06` | casey@lifeos.sandbox | Multi-attendee + busy Thursday |
| `avery` | `admin_07` | avery@lifeos.sandbox | Travel / timezone |
| `quinn` | `admin_08` | quinn@lifeos.sandbox | Tasks, no meeting |
| `cameron` | `admin_09` | cameron@lifeos.sandbox | Cold-start empty calendar |
| `taylor` | `admin_10` | taylor@lifeos.sandbox | Double-book risk |

Cockpit **admin_0N** maps to that user’s mailbox/calendar.

---

## Scenarios (eval seeds)

| Scenario id | User | Message | Intent |
|-------------|------|---------|--------|
| `meeting_clear` | alex | msg-alex-001 | Clear Q4 meeting ask |
| `meeting_ambiguous` | alex | msg-alex-002 | Vague “sometime” → HITL-ish |
| `not_a_meeting` | alex | msg-alex-003 | Newsletter → no calendar |
| `shared_conflict` | jordan | msg-jordan-001 | Mon 2pm ask vs existing busy |
| `irreversible_send` | sam | msg-sam-001 | Board delay email → HITL |
| `family_school` | riley | msg-riley-001 | School pickup calendar block |
| `info_only_promo` | morgan | msg-morgan-003 | Promo → no writes |
| `multi_attendee` | casey | msg-casey-001 | Multi-person + Thu busy |
| `travel_timezone` | avery | msg-avery-001 | NYC local-time ask |
| `task_follow_up` | quinn | msg-quinn-001 | Notion/Slack, no meeting |
| `cold_start_meeting` | cameron | msg-cameron-001 | Onboarding on empty calendar |
| `double_book_risk` | taylor | msg-taylor-001 | Conflict / propose alternate |

---

## Conflict detection

Sandbox calendars compare busy windows with **timezone-aware** ISO parsing
(`Z` and `±offset`). If a create overlaps a busy seed event, the calendar tool
returns `propose_event` / `proposed_only: true` with a `conflicts[]` list — it
does **not** double-book. See scenarios `shared_conflict` (jordan) and
`double_book_risk` (taylor).

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

1. Graph runs with `admin_id` (e.g. `admin_01`).
2. Tools resolve `admin_id` → sandbox `user_id` (e.g. `alex`).
3. Calendar create / Gmail draft / Notion / Slack / Sheets append land in `sandbox/.runtime/users/<user>/…`.
4. You can open those JSON files to **see** what the agent did — great for demos and reliability evidence.

---

## Shared Life OS

Teammate’s multi-user branch can keep using:
- `manifest.json` users list
- `resolve_user_id(admin_id=…)`
- same seed paths

Add more users by copying a `seed/users/<id>/` folder (profile + gmail + calendar + notion + slack + sheets) and registering in `manifest.json` (cap: 10 for family admin).
