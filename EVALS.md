# Agent Evals

How we check "does the graph actually do the right thing," as distinct from
unit tests of a single function. Maps to `PRD.md` F2.3 (golden fixtures with
assertable side-effect checks) and `SYSTEM_DESIGN.md` §10.2.

An eval here means: run a trigger (an email, a goal) through the real
LangGraph pipeline — Intake → Priority → Planner → Scheduler → Executor →
Critic → (HITL) → Auditor — in **mock connector mode**, then assert on the
resulting state: which apps got written, whether HITL was correctly
triggered (or correctly skipped), and that the audit row exists. No live
Gmail/Calendar/Notion/Slack calls are made; `LIFE_OS_USE_MOCK_CONNECTORS=1`
makes every tool return a deterministic fake `external_id` instead.

---

## 1. Golden fixtures

Trigger payloads live in [`life_os/fixtures/`](life_os/fixtures/):

| Fixture | Type | Exercises |
|---------|------|-----------|
| `meeting_email.json` | `email` | Clear meeting → calendar + notion + slack + sheets audit; Gmail draft only (no send) |
| `goal_simple.json` | `goal` | Free-text goal → follow-up + Notion + audit |
| `ambiguous_email.json` | `email` | Low confidence / irreversible → `needs_approval`; never Gmail send |
| `newsletter_not_meeting.json` | `email` | FYI / info_only → no calendar write; clean `pass`/`abort` + audit when pass |

PRD F2.3 asks for **≥3 golden fixtures with assertable side-effect checks** — covered by the suite above.

A fixture is a plain JSON file with:

```jsonc
{
  "fixture_id": "fixture-meeting-001",  // used as the idempotency source_id
  "type": "email",                      // "email" | "goal"
  // "email": subject/from/to/date/body
  // "goal": a "goal" string
}
```

---

## 2. Running a fixture by hand

The CLI streams each node's output and prints the final status:

```bash
export LIFE_OS_USE_MOCK_CONNECTORS=1
export ANTHROPIC_API_KEY=...        # or GEMINI_API_KEY — intake/priority/planner call the LLM

python -m life_os --fixture meeting_email.json --admin-id admin_01
python -m life_os --fixture goal_simple.json
```

Skip the LLM key by auto-approving and reading `tool_results` / `audit_ref`
instead of the LLM-derived intents — or use the pytest evals below, which
mock the LLM entirely and don't need a key.

If the run pauses (`needs_approval: true`), resolve it:

```bash
curl -X POST http://localhost:8000/runs/<run_id>/approve \
  -H 'content-type: application/json' \
  -d '{"decision": "approve", "admin_id": "admin_01"}'
```

(`LIFE_OS_HITL_AUTO=approve` auto-approves for non-interactive fixture runs
that don't go through the API.)

---

## 3. Running the eval-style pytest suite

These don't hit any LLM or network — the LLM classes are patched with
canned intake/priority/planner responses, and connectors run in mock mode.

```bash
source .venv/bin/activate
pip install -e ".[dev]"

# Golden fixtures through the full graph (EVALS.md / PRD F2.3):
pytest tests/evals/ -q

# Ad-hoc single fixture (mock LLM defaults for meeting_email.json):
python -m life_os.evals meeting_email.json

# Full graph smoke:
pytest tests/orchestrator/test_graph.py -q

# Per-app side-effect assertions (scheduler → executor → auditor):
pytest tests/integrations/test_tools_mock.py -q

# Everything (unit + eval-style):
pytest tests/ -q
```

What each currently asserts:

- `tests/evals/test_golden_fixtures.py` — full-graph golden evals via
  `life_os.evals.run_eval` (mocked LLM + `LIFE_OS_USE_MOCK_CONNECTORS=1`):
  - meeting email → `calendar`/`notion`/`slack`/`sheets` ok, `audit_ref`, no send
  - goal simple → notion + sheets audit, no send
  - ambiguous → `needs_approval`, no Gmail send
  - newsletter → no calendar write; `pass`/`abort` with audit on pass
- `tests/orchestrator/test_graph.py::test_stub_run_reaches_pass` — a mocked
  meeting request reaches a terminal status, never hangs mid-graph.
- `tests/orchestrator/test_graph.py::test_graph_has_all_nodes` — the 8
  pipeline nodes are all wired into the compiled graph.
- `tests/integrations/test_tools_mock.py::test_scheduler_executor_auditor_happy_path`
  — node-level happy path: calendar + Notion + Slack + Gmail-draft through
  scheduler → executor → auditor.
- `tests/integrations/test_tools_mock.py::test_calendar_propose_only` —
  `create=False` never fabricates a real write (`proposed_only: true`).
- `tests/integrations/test_tools_mock.py::test_send_blocked_on_error_draft` —
  a failed draft can never be sent.

Family/roster/audit-trail specific checks (who ran it, whose tokens were
used, who approved) live in `tests/orchestrator/test_admins.py`,
`tests/orchestrator/test_api.py`, and `tests/orchestrator/test_auditor.py` —
see [`FAMILY_ADMIN.md`](FAMILY_ADMIN.md) §5.

---

## 4. Adding a new golden fixture

1. Drop a JSON file in `life_os/fixtures/` (see the shape in §1).
2. Add a pytest case in `tests/evals/test_golden_fixtures.py` that calls
   `life_os.evals.run_eval(fixture_name, intake_json=..., priority_json=...,
   planner_json=...)` and asserts on *side effects* (apps in `tool_results`,
   `needs_approval`, `audit_ref`, no Gmail `send`) — not just status.
3. Run it in isolation first (`pytest tests/evals/test_golden_fixtures.py -q -k your_case -v`)
   before folding it into the full suite.

---

## 5. Reading results

Every run — real or eval — leaves the same trail, which is what the
assertions in §3 actually check:

- `tool_results[]` — one entry per attempted write, `{ok, app, action,
  external_id, error}`.
- `execution_receipts[]` — the subset that succeeded, per app.
- `errors[]` — non-fatal failures (partial success is allowed — see
  `SYSTEM_DESIGN.md` §10).
- `audit_ref` — set by the Auditor node once the Sheets audit row is
  appended (`life_os/agents/auditor.py`).

In mock mode all of the above use deterministic fake ids
(`mock-draft-<run_id>`, `mock-sheets-row-<run_id>`, …), which is what makes
these evals reproducible and CI-friendly with no credentials.
