"""In-memory idempotency store (Tier 0)."""

from __future__ import annotations

from typing import Any, Optional

_STORE: dict[tuple[str, str], Any] = {}


def _key(admin_id: Optional[str], idempotency_key: str) -> tuple[str, str]:
    return (admin_id or "", idempotency_key)


def get_cached(admin_id: Optional[str], idempotency_key: str) -> Any | None:
    return _STORE.get(_key(admin_id, idempotency_key))


def put_cached(admin_id: Optional[str], idempotency_key: str, value: Any) -> Any:
    _STORE[_key(admin_id, idempotency_key)] = value
    return value


def clear() -> None:
    """Test helper."""
    _STORE.clear()
