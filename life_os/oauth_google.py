"""CLI: python -m life_os.oauth_google --admin-id admin_01

Runs an installed-app OAuth dance and writes `.oauth/{admin_id}_google.json`.
"""

from __future__ import annotations

import argparse
import sys

from life_os.adapters import google_auth
from life_os.admins import get_roster
from life_os.adapters.google_auth import SCOPES_DEFAULT


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Per-admin Google OAuth login")
    parser.add_argument("--admin-id", required=True, help="Roster admin_id (e.g. admin_01)")
    args = parser.parse_args(argv)

    roster = get_roster()
    if args.admin_id not in roster.admins:
        print(f"Unknown admin_id={args.admin_id}. Known: {list(roster.admins)}", file=sys.stderr)
        return 1

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Install google-auth-oauthlib", file=sys.stderr)
        return 1

    client_id = __import__("os").getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = __import__("os").getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET", file=sys.stderr)
        return 1

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, scopes=list(SCOPES_DEFAULT))
    creds = flow.run_local_server(port=0)
    path = google_auth.save_credentials(args.admin_id, creds)
    print(f"Saved Google token for {args.admin_id} → {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
