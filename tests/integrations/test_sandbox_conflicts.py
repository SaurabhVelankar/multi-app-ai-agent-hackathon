"""Sandbox integration smoke — isolation + conflict detection."""

from __future__ import annotations

import os

import pytest

os.environ["LIFE_OS_USE_MOCK_CONNECTORS"] = "1"
os.environ["LIFE_OS_USE_SANDBOX"] = "1"

from life_os import idempotency
from life_os.sandbox import create_event, list_busy, list_events, reset_all, resolve_user_id
from life_os.tools.calendar import create_calendar_event
from life_os.tools.gmail import draft_gmail_reply


@pytest.fixture(autouse=True)
def _fresh_sandbox(monkeypatch):
    monkeypatch.setenv("LIFE_OS_USE_MOCK_CONNECTORS", "1")
    monkeypatch.setenv("LIFE_OS_USE_SANDBOX", "1")
    idempotency.clear()
    reset_all()
    yield
    idempotency.clear()


def test_admin_maps_cover_ten_users():
    expected = {
        "admin_01": "alex",
        "admin_02": "jordan",
        "admin_03": "sam",
        "admin_04": "riley",
        "admin_05": "morgan",
        "admin_06": "casey",
        "admin_07": "avery",
        "admin_08": "quinn",
        "admin_09": "cameron",
        "admin_10": "taylor",
    }
    for admin_id, user_id in expected.items():
        assert resolve_user_id(admin_id=admin_id) == user_id


def test_list_busy_detects_zulu_vs_offset_overlap():
    """Jordan Mon 2pm PT seed must conflict with a Zulu query for the same window."""
    uid = resolve_user_id(admin_id="admin_02")
    busy = list_busy(uid, "2026-09-15T21:00:00Z", "2026-09-15T21:45:00Z")
    assert len(busy) >= 1
    assert any(e.get("id") == "evt-jordan-conflict" for e in busy)


def test_create_on_conflict_proposes_only_for_jordan():
    result = create_calendar_event(
        "run-conflict-j",
        "Design review with Sam",
        "2026-09-15T21:00:00Z",
        "2026-09-15T21:45:00Z",
        "idem-jordan-conflict",
        admin_id="admin_02",
        create=True,
    )
    assert result["ok"] is True
    assert result.get("proposed_only") is True
    assert result.get("external_id") is None
    assert result["action"] == "propose_event"
    assert result["raw"].get("conflicts")
    # Seed event still only — no write
    events = list_events("jordan")
    assert not any(e.get("idempotency_key") == "idem-jordan-conflict" for e in events)


def test_create_on_conflict_proposes_only_for_taylor():
    result = create_calendar_event(
        "run-conflict-t",
        "Client decision call",
        "2026-09-15T17:00:00Z",  # 10:00 PT
        "2026-09-15T18:00:00Z",
        "idem-taylor-conflict",
        admin_id="admin_10",
        create=True,
    )
    assert result["proposed_only"] is True
    assert len(result["raw"].get("conflicts") or []) >= 1


def test_writes_are_isolated_per_admin():
    draft_gmail_reply("run-a", None, "hello from alex", admin_id="admin_01")
    draft_gmail_reply("run-b", None, "hello from jordan", admin_id="admin_02")
    from life_os.sandbox.store import _read_json

    alex_drafts = _read_json("alex", "gmail.json").get("drafts") or []
    jordan_drafts = _read_json("jordan", "gmail.json").get("drafts") or []
    assert any("alex" in (d.get("body") or "") for d in alex_drafts)
    assert any("jordan" in (d.get("body") or "") for d in jordan_drafts)
    assert not any("jordan" in (d.get("body") or "") for d in alex_drafts)


def test_free_slot_creates_for_cameron_cold_start():
    result = create_calendar_event(
        "run-cold",
        "HR onboarding",
        "2026-09-16T16:00:00Z",
        "2026-09-16T16:45:00Z",
        "idem-cameron-onboard",
        admin_id="admin_09",
        create=True,
    )
    assert result["ok"] is True
    assert result.get("proposed_only") is False
    assert result.get("external_id")
    assert any(e.get("idempotency_key") == "idem-cameron-onboard" for e in list_events("cameron"))
