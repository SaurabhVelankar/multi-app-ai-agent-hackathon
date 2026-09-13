"""Slack Web API client."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Optional

from life_os.tools._common import env, use_mock_connectors


class SlackClientError(RuntimeError):
    pass


def credentials_available() -> bool:
    if use_mock_connectors():
        return False
    return bool(env("SLACK_BOT_TOKEN") and env("SLACK_CHANNEL_ID"))


def _api(method: str, payload: dict[str, Any]) -> dict[str, Any]:
    token = env("SLACK_BOT_TOKEN")
    if not token:
        raise SlackClientError("SLACK_BOT_TOKEN missing")
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(
        f"https://slack.com/api/{method}",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise SlackClientError(f"Slack network error: {exc}") from exc
    if not body.get("ok"):
        raise SlackClientError(f"Slack {method} error: {body.get('error', body)}")
    return body


def post_message(text: str, *, channel: Optional[str] = None, mention: Optional[str] = None) -> dict[str, Any]:
    channel_id = channel or env("SLACK_CHANNEL_ID")
    if not channel_id:
        raise SlackClientError("SLACK_CHANNEL_ID missing")
    content = text
    if mention:
        content = f"<@{mention}> {text}"
    return _api("chat.postMessage", {"channel": channel_id, "text": content})


def healthcheck() -> bool:
    try:
        _api("auth.test", {})
        return True
    except SlackClientError:
        return False
