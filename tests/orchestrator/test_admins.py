"""T1/T2 roster + per-admin OAuth path resolution."""

from __future__ import annotations

import os

import pytest

from life_os.admins import reload_roster
from life_os.adapters import google_auth


@pytest.fixture()
def family_env(monkeypatch):
    monkeypatch.setenv("FAMILY_ID", "test_family")
    monkeypatch.setenv("ADMIN_MAX", "10")
    monkeypatch.setenv("HITL_POLICY", "any_of")
    monkeypatch.setenv("ADMIN_IDS", "admin_01,admin_02,admin_03")
    monkeypatch.setenv("ADMIN_01_NAME", "Parent A")
    monkeypatch.setenv("ADMIN_01_ROLE", "owner")
    monkeypatch.setenv("ADMIN_01_SLACK", "U_PARENT_A")
    monkeypatch.setenv("ADMIN_01_GOOGLE_TOKEN_PATH", ".oauth/admin_01_google.json")
    monkeypatch.setenv("ADMIN_02_NAME", "Parent B")
    monkeypatch.setenv("ADMIN_02_ROLE", "operator")
    monkeypatch.setenv("ADMIN_02_SLACK", "U_PARENT_B")
    monkeypatch.setenv("ADMIN_02_GOOGLE_TOKEN_PATH", ".oauth/admin_02_google.json")
    monkeypatch.setenv("ADMIN_03_NAME", "Kid")
    monkeypatch.setenv("ADMIN_03_ROLE", "viewer")
    monkeypatch.setenv("ADMIN_03_SLACK", "U_KID")
    reload_roster()
    yield
    for key in list(os.environ):
        if key.startswith("ADMIN_") or key in {"FAMILY_ID", "HITL_POLICY"}:
            monkeypatch.delenv(key, raising=False)
    reload_roster()


def test_roster_loads_roles(family_env):
    from life_os.admins import get_roster

    roster = get_roster()
    assert roster.family_id == "test_family"
    assert len(roster.admins) == 3
    assert roster.owner().admin_id == "admin_01"
    assert roster.can_approve("admin_01")
    assert roster.can_approve("admin_02")
    assert not roster.can_approve("admin_03")
    assert roster.default_shared_with() == ["admin_01", "admin_02"]


def test_roster_rejects_over_max(monkeypatch):
    monkeypatch.setenv("ADMIN_MAX", "2")
    monkeypatch.setenv(
        "ADMIN_IDS", "admin_01,admin_02,admin_03"
    )
    monkeypatch.setenv("ADMIN_01_ROLE", "owner")
    from life_os.admins import load_roster_from_env

    with pytest.raises(RuntimeError, match="ADMIN_MAX"):
        load_roster_from_env()


def test_token_paths_differ_per_admin(family_env):
    p1 = google_auth.token_path_for("admin_01")
    p2 = google_auth.token_path_for("admin_02")
    assert str(p1) != str(p2)
    assert p1.name == "admin_01_google.json"
    assert p2.name == "admin_02_google.json"


def test_oauth_status_missing(family_env):
    status = google_auth.oauth_status("admin_01")
    assert status["admin_id"] == "admin_01"
    assert status["google"] in {"connected", "missing"}
    assert "token_path" in status


def test_unknown_admin_id_rejected(family_env):
    from life_os.admins import get_roster

    roster = get_roster()
    assert roster.get("ghost") is None
    with pytest.raises(KeyError):
        roster.require("ghost")
    assert not roster.can_approve("ghost")
    assert not roster.can_manage_roster("ghost")


def test_viewer_cannot_approve_or_manage_roster(family_env):
    from life_os.admins import get_roster

    roster = get_roster()
    assert not roster.can_approve("admin_03")
    assert not roster.can_manage_roster("admin_03")


def test_any_of_targets_all_owners_and_operators(family_env):
    from life_os.admins import get_roster

    roster = get_roster()
    assert roster.hitl_policy == "any_of"
    target_ids = {a.admin_id for a in roster.approval_targets()}
    assert target_ids == {"admin_01", "admin_02"}  # viewer excluded


def test_hitl_any_of_mentions_all_owners_and_operators(family_env):
    from life_os import hitl

    assert hitl.resolve_assignee("any_of") is None
    assert set(hitl.mention_targets("any_of")) == {"U_PARENT_A", "U_PARENT_B"}


def test_hitl_primary_targets_owner_only(family_env):
    from life_os import hitl

    assert hitl.resolve_assignee("primary") == "admin_01"
    assert hitl.mention_targets("primary") == ["U_PARENT_A"]


def test_hitl_round_robin_documented_falls_back_to_primary(family_env):
    """round_robin is documented for a future release; today it behaves like primary."""
    from life_os import hitl

    assert hitl.resolve_assignee("round_robin") == "admin_01"
    assert hitl.mention_targets("round_robin") == ["U_PARENT_A"]
