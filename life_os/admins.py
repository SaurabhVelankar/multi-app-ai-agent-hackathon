"""Family Admin roster — load from env, hard cap ADMIN_MAX (default 10)."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

logger = logging.getLogger(__name__)

Role = Literal["owner", "operator", "viewer"]


@dataclass(frozen=True)
class Admin:
    admin_id: str
    name: str
    role: Role
    email: Optional[str] = None
    slack_user_id: Optional[str] = None
    google_token_path: str = ""
    notion_token: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.google_token_path:
            object.__setattr__(
                self,
                "google_token_path",
                f".oauth/{self.admin_id}_google.json",
            )


@dataclass
class FamilyRoster:
    family_id: str
    admins: dict[str, Admin] = field(default_factory=dict)
    hitl_policy: str = "any_of"
    admin_max: int = 10

    def get(self, admin_id: str) -> Optional[Admin]:
        return self.admins.get(admin_id)

    def require(self, admin_id: str) -> Admin:
        admin = self.get(admin_id)
        if admin is None:
            raise KeyError(f"Unknown admin_id: {admin_id}")
        return admin

    def list_admins(self) -> list[Admin]:
        return list(self.admins.values())

    def owner(self) -> Optional[Admin]:
        for a in self.admins.values():
            if a.role == "owner":
                return a
        return next(iter(self.admins.values()), None)

    def operators_and_owners(self) -> list[Admin]:
        return [a for a in self.admins.values() if a.role in {"owner", "operator"}]

    def default_shared_with(self) -> list[str]:
        return [a.admin_id for a in self.operators_and_owners()]

    def approval_targets(self) -> list[Admin]:
        """Who HITL should route an approval request to, per `hitl_policy`.

        - any_of: every owner+operator may approve (mention them all)
        - primary (default) / round_robin (documented, not yet implemented —
          falls back to primary): the single owner is the target
        """
        if self.hitl_policy == "any_of":
            return self.operators_and_owners()
        owner = self.owner()
        return [owner] if owner else self.list_admins()[:1]

    def can_approve(self, admin_id: str) -> bool:
        admin = self.get(admin_id)
        return bool(admin and admin.role in {"owner", "operator"})

    def can_manage_roster(self, admin_id: str) -> bool:
        admin = self.get(admin_id)
        return bool(admin and admin.role == "owner")


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name, default)
    if value is not None and str(value).strip() == "":
        return default
    return value


def _env_for_admin(admin_id: str, suffix: str) -> Optional[str]:
    """Resolve ADMIN_01_NAME when admin_id is admin_01 (case-insensitive)."""
    key = f"{admin_id.upper()}_{suffix}"
    return _env(key)


def _parse_role(raw: Optional[str], admin_id: str) -> Role:
    role = (raw or "operator").strip().lower()
    if role not in {"owner", "operator", "viewer"}:
        logger.warning("Invalid role %r for %s; defaulting to operator", raw, admin_id)
        return "operator"
    return role  # type: ignore[return-value]


def load_roster_from_env() -> FamilyRoster:
    """Load FAMILY_ID + ADMIN_IDS + ADMIN_XX_* from environment.

    If ADMIN_IDS is empty, returns a solo demo owner `admin_01` so local/mock still works.
    """
    admin_max = int(_env("ADMIN_MAX", "10") or "10")
    family_id = _env("FAMILY_ID", "default") or "default"
    hitl_policy = (_env("HITL_POLICY", "any_of") or "any_of").strip().lower()
    ids_raw = _env("ADMIN_IDS", "") or ""
    ids = [i.strip() for i in ids_raw.split(",") if i.strip()]

    if not ids:
        ids = ["admin_01"]
        logger.info("ADMIN_IDS unset — using solo demo roster admin_01 (owner)")

    if len(ids) > admin_max:
        raise RuntimeError(
            f"Admin roster has {len(ids)} members; ADMIN_MAX={admin_max}"
        )

    admins: dict[str, Admin] = {}
    for i, admin_id in enumerate(ids):
        name = _env_for_admin(admin_id, "NAME") or admin_id
        role_raw = _env_for_admin(admin_id, "ROLE")
        if not role_raw and i == 0 and len(ids) == 1:
            role_raw = "owner"
        role = _parse_role(role_raw, admin_id)
        email = _env_for_admin(admin_id, "EMAIL")
        slack = _env_for_admin(admin_id, "SLACK")
        token_path = (
            _env_for_admin(admin_id, "GOOGLE_TOKEN_PATH")
            or f".oauth/{admin_id}_google.json"
        )
        notion = _env_for_admin(admin_id, "NOTION_TOKEN")

        admins[admin_id] = Admin(
            admin_id=admin_id,
            name=str(name),
            role=role,
            email=email,
            slack_user_id=slack,
            google_token_path=str(token_path),
            notion_token=notion,
        )

    owners = [a for a in admins.values() if a.role == "owner"]
    if len(owners) == 0 and admins:
        first = next(iter(admins.values()))
        logger.warning("No owner in roster; treating %s as owner", first.admin_id)
        admins[first.admin_id] = Admin(
            admin_id=first.admin_id,
            name=first.name,
            role="owner",
            email=first.email,
            slack_user_id=first.slack_user_id,
            google_token_path=first.google_token_path,
            notion_token=first.notion_token,
        )
    elif len(owners) > 1:
        logger.warning(
            "Multiple owners configured (%s); first wins for defaults",
            [o.admin_id for o in owners],
        )

    return FamilyRoster(
        family_id=family_id,
        admins=admins,
        hitl_policy=hitl_policy,
        admin_max=admin_max,
    )


@lru_cache(maxsize=1)
def get_roster() -> FamilyRoster:
    return load_roster_from_env()


def reload_roster() -> FamilyRoster:
    """Test helper — clear cache and reload."""
    get_roster.cache_clear()
    return get_roster()


def google_token_path_for(admin_id: str) -> Path:
    roster = get_roster()
    admin = roster.get(admin_id)
    if admin:
        return Path(admin.google_token_path)
    return Path(f".oauth/{admin_id}_google.json")


def notion_token_for(admin_id: Optional[str]) -> Optional[str]:
    if not admin_id:
        return _env("NOTION_TOKEN")
    admin = get_roster().get(admin_id)
    if admin and admin.notion_token:
        return admin.notion_token
    return _env("NOTION_TOKEN")
