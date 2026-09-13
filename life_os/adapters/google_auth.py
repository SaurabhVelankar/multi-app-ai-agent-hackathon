"""Google OAuth helpers for Calendar / Sheets / Gmail."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional, Sequence

from life_os.tools._common import env, use_mock_connectors

SCOPES_DEFAULT = (
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.compose",
)


class GoogleAuthError(RuntimeError):
    pass


def token_path() -> Path:
    return Path(env("GOOGLE_OAUTH_TOKEN_PATH", ".oauth/google_token.json") or ".oauth/google_token.json")


def credentials_available() -> bool:
    if use_mock_connectors():
        return False
    client_id = env("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = env("GOOGLE_OAUTH_CLIENT_SECRET")
    return bool(client_id and client_secret and token_path().exists())


def load_credentials(scopes: Sequence[str] = SCOPES_DEFAULT) -> Any:
    """Load/refresh OAuth credentials. Raises if live mode without a token file.

    Expects an existing token JSON produced by a one-time OAuth dance
    (installed-app or manual). Hackathon Tier 0: place token at GOOGLE_OAUTH_TOKEN_PATH.
    """
    if use_mock_connectors():
        raise GoogleAuthError("Mock connectors enabled; Google auth not used")

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError as exc:
        raise GoogleAuthError(
            "google-auth / google-auth-oauthlib not installed"
        ) from exc

    path = token_path()
    if not path.exists():
        raise GoogleAuthError(
            f"Missing Google token at {path}. Run OAuth once and save token JSON."
        )

    data = json.loads(path.read_text())
    creds = Credentials.from_authorized_user_info(data, scopes=list(scopes))
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(creds.to_json())
    if not creds or not creds.valid:
        raise GoogleAuthError("Google credentials invalid; re-run OAuth")
    return creds


def build_service(api: str, version: str, scopes: Sequence[str] = SCOPES_DEFAULT) -> Any:
    try:
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise GoogleAuthError("google-api-python-client not installed") from exc
    creds = load_credentials(scopes)
    return build(api, version, credentials=creds, cache_discovery=False)
