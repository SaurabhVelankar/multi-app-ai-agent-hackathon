"""Common helpers for tools — mock flag + env."""

from __future__ import annotations

import os
from typing import Optional


def use_mock_connectors() -> bool:
    """Default to mock unless explicitly disabled and credentials exist."""
    flag = os.getenv("LIFE_OS_USE_MOCK_CONNECTORS", "1").strip().lower()
    return flag in {"1", "true", "yes", "on"}


def env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name, default)
    if value is not None and value.strip() == "":
        return default
    return value
