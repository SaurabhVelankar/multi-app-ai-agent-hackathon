"""Notion HTTP client (internal integration token)."""

from __future__ import annotations

from typing import Any, Optional

import urllib.error
import urllib.request
import json

from life_os.tools._common import env, use_mock_connectors

NOTION_VERSION = "2022-06-28"


class NotionClientError(RuntimeError):
    pass


def credentials_available() -> bool:
    if use_mock_connectors():
        return False
    return bool(env("NOTION_TOKEN") and (env("NOTION_PARENT_PAGE_ID") or env("NOTION_DATABASE_ID")))


def _headers(admin_id: Optional[str] = None) -> dict[str, str]:
    from life_os.admins import notion_token_for

    token = notion_token_for(admin_id)
    if not token:
        raise NotionClientError(
            f"Notion token missing for admin_id={admin_id!r} (set ADMIN_XX_NOTION_TOKEN or NOTION_TOKEN)"
        )
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _request(
    method: str,
    path: str,
    body: Optional[dict] = None,
    *,
    admin_id: Optional[str] = None,
) -> dict[str, Any]:
    url = f"https://api.notion.com/v1{path}"
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers=_headers(admin_id), method=method
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise NotionClientError(f"Notion {method} {path} failed: {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise NotionClientError(f"Notion network error: {exc}") from exc


def create_page(
    *,
    title: str,
    body: str,
    run_id: str,
    admin_id: Optional[str] = None,
) -> dict[str, Any]:
    """Create a child page under NOTION_PARENT_PAGE_ID or a DB row if DATABASE_ID set."""
    parent_page = env("NOTION_PARENT_PAGE_ID")
    database_id = env("NOTION_DATABASE_ID")

    children = [
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [{"type": "text", "text": {"content": body[:1900]}}],
            },
        },
        {
            "object": "block",
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {"type": "text", "text": {"content": f"run_id: {run_id}"}}
                ],
            },
        },
    ]

    if database_id:
        payload = {
            "parent": {"database_id": database_id},
            "properties": {
                "Name": {
                    "title": [{"type": "text", "text": {"content": title[:200]}}],
                }
            },
            "children": children,
        }
    elif parent_page:
        payload = {
            "parent": {"page_id": parent_page},
            "properties": {
                "title": {
                    "title": [{"type": "text", "text": {"content": title[:200]}}],
                }
            },
            "children": children,
        }
    else:
        raise NotionClientError("Set NOTION_PARENT_PAGE_ID or NOTION_DATABASE_ID")

    return _request("POST", "/pages", payload, admin_id=admin_id)


def healthcheck(admin_id: Optional[str] = None) -> bool:
    try:
        _request("GET", "/users/me", admin_id=admin_id)
        return True
    except NotionClientError:
        return False
