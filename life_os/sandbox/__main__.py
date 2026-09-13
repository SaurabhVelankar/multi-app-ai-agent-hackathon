"""CLI: python -m life_os.sandbox [reset|list|scenario <id>]"""

from __future__ import annotations

import json
import sys

from life_os.sandbox import (
    get_scenario_message,
    list_events,
    list_inbox,
    load_manifest,
    reset_all,
    resolve_user_id,
)


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    if not args or args[0] in {"-h", "--help", "help"}:
        print("Usage: python -m life_os.sandbox <reset|list|scenario <id>>")
        return 0

    cmd = args[0]
    if cmd == "reset":
        users = reset_all()
        print(f"Sandbox runtime reset for users: {', '.join(users)}")
        return 0

    if cmd == "list":
        manifest = load_manifest()
        print(json.dumps(manifest, indent=2))
        for u in manifest.get("users", []):
            uid = u["user_id"]
            inbox = list_inbox(uid)
            events = list_events(uid)
            print(f"\n## {uid} ({u.get('email')})")
            print(f"  inbox messages: {len(inbox)}")
            print(f"  calendar events: {len(events)}")
            for m in inbox:
                print(f"  - [{m['id']}] {m.get('subject')}")
        return 0

    if cmd == "scenario" and len(args) >= 2:
        user_id, msg = get_scenario_message(args[1])
        print(json.dumps({"user_id": user_id, "message": msg}, indent=2))
        return 0

    print(f"Unknown command: {cmd}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
