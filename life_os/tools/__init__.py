"""Tools package — LangChain-ready wrappers over adapters (Agent 2)."""

from life_os.tools.calendar import create_calendar_event
from life_os.tools.gmail import draft_gmail_reply, send_gmail
from life_os.tools.notion import create_notion_page
from life_os.tools.sheets import append_sheets_audit
from life_os.tools.slack import post_slack_receipt, request_slack_approval

__all__ = [
    "create_calendar_event",
    "create_notion_page",
    "post_slack_receipt",
    "request_slack_approval",
    "append_sheets_audit",
    "draft_gmail_reply",
    "send_gmail",
]
