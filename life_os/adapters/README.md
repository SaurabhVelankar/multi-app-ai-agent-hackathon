# Life OS adapters (Agent 2)

Thin vendor clients. Tools in `life_os/tools/` call these; graph nodes never import SDKs directly.

## Mock vs live

```bash
LIFE_OS_USE_MOCK_CONNECTORS=1   # default — deterministic fakes, no network
LIFE_OS_USE_MOCK_CONNECTORS=0   # live — requires credentials below
```

## Env keys

See `contracts/connectors.md` and root `.env.example`.

| App | Required |
|-----|----------|
| Sheets / Calendar / Gmail | `GOOGLE_OAUTH_*`, token JSON, `SHEETS_SPREADSHEET_ID` / `GOOGLE_CALENDAR_ID` |
| Notion | `NOTION_TOKEN` + `NOTION_PARENT_PAGE_ID` or `NOTION_DATABASE_ID` |
| Slack | `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID` |

## Python deps (ask Agent 1 to merge into root requirements)

```
google-auth
google-auth-oauthlib
google-api-python-client
pytest
```

Notion and Slack use stdlib `urllib` only.
