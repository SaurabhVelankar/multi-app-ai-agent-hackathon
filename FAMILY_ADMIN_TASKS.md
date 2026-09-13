# Family Shared Admin — Task List

> Branch: **`shared-LifeOS`**  
> Plan: Cursor plan *Family Shared Admin*  
> Cap: **≤ 10** family members · **per-user OAuth** (each member’s own login) · HITL default **`any_of`**

Use this checklist while implementing. Mark items `[x]` as you finish them.

---

## Tasks

### T1 — Roster module
- [x] Add [`life_os/admins.py`](life_os/admins.py) — load `Admin` objects from env (`ADMIN_IDS`, `ADMIN_XX_*`)
- [x] Include per-admin `GOOGLE_TOKEN_PATH` / `NOTION_TOKEN` fields (default `.oauth/{admin_id}_google.json`)
- [x] Wire [`life_os/config.py`](life_os/config.py) — `FAMILY_ID`, `ADMIN_MAX=10`, `HITL_POLICY=any_of`
- [x] Startup: refuse roster length > 10; warn if not exactly one `owner`
- [x] Update [`.env.example`](.env.example) with a 2–3 person family + token path example

### T2 — Per-user OAuth (every admin’s own login)
- [x] Refactor [`life_os/adapters/google_auth.py`](life_os/adapters/google_auth.py) — `token_path_for(admin_id)`, `load_credentials(admin_id)`, no global-only token
- [x] One shared Google OAuth **client**; **separate refresh token file per admin**
- [x] Routes: `GET /admins/{id}/oauth/google/start`, `GET /oauth/google/callback`, `GET /admins/{id}/oauth/status`
- [x] CLI: `python -m life_os.oauth_google --admin-id …` for local consent
- [x] Thread `admin_id` through Calendar / Gmail / Sheets / Notion tools → resolve that user’s credentials
- [x] Update [`contracts/connectors.md`](contracts/connectors.md): writes require `admin_id`; credentials are per-user
- [x] Mock mode still works without tokens (`LIFE_OS_USE_MOCK_CONNECTORS=1`)

### T3 — State + contracts
- [x] Extend [`life_os/state.py`](life_os/state.py) with `family_id`, `shared_with[]`, `approval_assignee`
- [x] Update [`contracts/openapi.yaml`](contracts/openapi.yaml) — LifeState fields, `/admins`, OAuth endpoints

### T4 — API enforce
- [x] Refactor [`life_os/api.py`](life_os/api.py) — config-loaded roster; reject unknown `admin_id`
- [x] Block `viewer` on approve; owner-only add/delete; hard stop at 10
- [x] Idempotency: **`(admin_id, source_id)`** / **`(admin_id, idempotency_key)`** for app writes
- [x] `GET/POST/DELETE /admins`
- [x] CLI [`life_os/__main__.py`](life_os/__main__.py): `--admin-id` must be in roster when configured

### T5 — HITL routing
- [x] Update [`life_os/hitl.py`](life_os/hitl.py) — `any_of` @mentions all owners+operators
- [x] Keep `primary`; document `round_robin`
- [x] Set `approval_assignee`; CLI fallback if Slack down
- [x] After approve, Gmail send still uses **requester** `admin_id` tokens (not approver’s)

### T6 — Audit + idempotency
- [x] Auditor row: `family_id`, requester `admin_id`, approver, `approval_assignee`, oauth account if known
- [x] Never use another admin’s token for writes

### T7 — Tests + docs
- [x] [`tests/orchestrator/test_admins.py`](tests/orchestrator/test_admins.py) — cap, unknown id, viewer deny, any_of
- [x] OAuth resolve tests — different `admin_id` → different token paths
- [x] Add [`FAMILY_ADMIN.md`](FAMILY_ADMIN.md) — roster + **each member runs Google login**
- [x] Link from [`README.md`](README.md)

---

## Done when

- [x] Family of 2–10 loads from env; hard refuse >10
- [x] Each admin completes **their own** Google OAuth; tokens isolated by `admin_id`
- [x] Live writes use the **requester’s** token only
- [x] Only roster members trigger/approve; viewers blocked on approve
- [x] HITL `any_of` works; approve does not switch credentials
- [x] Audit shows requester + approver; tests green; doc explains per-user OAuth

---

## Out of scope (this branch)

- Real Life OS JWT login (beyond `admin_id` + OAuth connect)
- Quorum (2-of-N)
- Frontend roster / OAuth UI
- Per-user Slack user OAuth (family bot + @mention is enough)