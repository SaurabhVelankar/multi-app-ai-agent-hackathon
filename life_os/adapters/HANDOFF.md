# Agent 2 → Agent 1 handoff

## Contract
- Frozen: `contracts/connectors.md` (awaiting Agent 1 ACK)
- Import from `life_os.tools.*` and `life_os.hitl`

## Wire nodes (Agent 1 already imports these from `life_os.agents.*`)
```python
from life_os.agents.scheduler import scheduler_node
from life_os.agents.executor import executor_node
from life_os.agents.auditor import auditor_node
from life_os.hitl import request_approval, wait_cli_approval
from life_os.tools.gmail import send_gmail  # only after HITL approve
```

Write nodes live at `life_os/agents/{scheduler,executor,auditor}.py` so `life_os/graph.py` stubs resolve.

## Mock (default)
```bash
export LIFE_OS_USE_MOCK_CONNECTORS=1
export LIFE_OS_HITL_AUTO=approve   # non-interactive
pytest tests/integrations -q
```

## Live
```bash
export LIFE_OS_USE_MOCK_CONNECTORS=0
# fill Google / Notion / Slack vars from .env.example
```

## Env keys added for Agent 1 `.env.example`
`LIFE_OS_USE_MOCK_CONNECTORS`, `HITL_POLICY`, `HITL_FALLBACK_CLI`, `LIFE_OS_HITL_AUTO`, `ADMIN_PRIMARY_SLACK`, `SHEETS_AUDIT_RANGE`

## Deps
See `requirements-integrations.txt` — please merge into root requirements when ready.
