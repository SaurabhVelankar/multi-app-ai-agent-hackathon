"""Google OAuth helpers — per-admin token files (family shared client)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Sequence

from life_os.admins import google_token_path_for
from life_os.tools._common import env, use_mock_connectors

SCOPES_DEFAULT = (
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/gmail.compose",
)


class GoogleAuthError(RuntimeError):
    pass


def token_path(admin_id: Optional[str] = None) -> Path:
    """Return token path for admin_id, or legacy global path if admin_id is None."""
    if admin_id:
        return google_token_path_for(admin_id)
    return Path(
        env("GOOGLE_OAUTH_TOKEN_PATH", ".oauth/google_token.json")
        or ".oauth/google_token.json"
    )


def token_path_for(admin_id: str) -> Path:
    return google_token_path_for(admin_id)


def credentials_available(admin_id: Optional[str] = None) -> bool:
    if use_mock_connectors():
        return False
    client_id = env("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = env("GOOGLE_OAUTH_CLIENT_SECRET")
    return bool(client_id and client_secret and token_path(admin_id).exists())


def oauth_status(admin_id: str) -> dict[str, Any]:
    path = token_path_for(admin_id)
    email = None
    if path.exists():
        try:
            data = json.loads(path.read_text())
            email = data.get("email") or data.get("account")
        except (OSError, json.JSONDecodeError):
            pass
    return {
        "admin_id": admin_id,
        "google": "connected" if path.exists() else "missing",
        "token_path": str(path),
        "email": email,
        "mock_mode": use_mock_connectors(),
        "connected": path.exists(),
    }


def load_credentials(
    admin_id: Optional[str] = None,
    scopes: Sequence[str] = SCOPES_DEFAULT,
) -> Any:
    """Load/refresh OAuth credentials for a specific admin (or legacy global token)."""
    if use_mock_connectors():
        raise GoogleAuthError("Mock connectors enabled; Google auth not used")

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError as exc:
        raise GoogleAuthError(
            "google-auth / google-auth-oauthlib not installed"
        ) from exc

    path = token_path(admin_id)
    if not path.exists():
        hint = f" for admin_id={admin_id}" if admin_id else ""
        raise GoogleAuthError(
            f"Missing Google token at {path}{hint}. "
            "Complete OAuth (GET /admins/{id}/oauth/google/start or "
            "python -m life_os.oauth_google --admin-id …)."
        )

    data = json.loads(path.read_text())
    creds = Credentials.from_authorized_user_info(data, scopes=list(scopes))
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(creds.to_json())
    if not creds or not creds.valid:
        raise GoogleAuthError(
            f"Google credentials invalid for admin_id={admin_id}; re-run OAuth"
        )
    return creds


def save_credentials(admin_id: str, creds: Any) -> Path:
    path = token_path_for(admin_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(creds.to_json())
    return path


def build_service(
    api: str,
    version: str,
    *,
    admin_id: Optional[str] = None,
    scopes: Sequence[str] = SCOPES_DEFAULT,
) -> Any:
    try:
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise GoogleAuthError("google-api-python-client not installed") from exc
    creds = load_credentials(admin_id, scopes=scopes)
    return build(api, version, credentials=creds, cache_discovery=False)


def build_auth_url(admin_id: str, redirect_uri: Optional[str] = None) -> str:
    """Build Google consent URL; state carries admin_id."""
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError as exc:
        raise GoogleAuthError("google-auth-oauthlib not installed") from exc

    client_id = env("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = env("GOOGLE_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise GoogleAuthError("GOOGLE_OAUTH_CLIENT_ID/SECRET required")

    redirect = redirect_uri or env(
        "GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/oauth/google/callback"
    )
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect],
        }
    }
    flow = Flow.from_client_config(
        client_config, scopes=list(SCOPES_DEFAULT), state=admin_id
    )
    flow.redirect_uri = redirect
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


def exchange_code(
    admin_id: str,
    code: str,
    redirect_uri: Optional[str] = None,
) -> Path:
    """Exchange auth code and persist token for admin_id."""
    try:
        from google_auth_oauthlib.flow import Flow
    except ImportError as exc:
        raise GoogleAuthError("google-auth-oauthlib not installed") from exc

    client_id = env("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = env("GOOGLE_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise GoogleAuthError("GOOGLE_OAUTH_CLIENT_ID/SECRET required")

    redirect = redirect_uri or env(
        "GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/oauth/google/callback"
    )
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect],
        }
    }
    flow = Flow.from_client_config(
        client_config, scopes=list(SCOPES_DEFAULT), state=admin_id
    )
    flow.redirect_uri = redirect
    flow.fetch_token(code=code)
    return save_credentials(admin_id, flow.credentials)
