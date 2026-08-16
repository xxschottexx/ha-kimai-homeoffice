"""Daily goal helpers for Kimai Homeoffice."""

from __future__ import annotations

from math import isfinite
from typing import Any

from .const import (
    DAILY_GOAL_MODE_DISABLED,
    DAILY_GOAL_MODE_MANUAL_ENTITY,
    DAILY_GOAL_MODE_WEEKLY_PLAN,
    DAILY_GOAL_MODE_WORKED_DAYS_ONLY,
)


def manual_goal_seconds(value: Any) -> int | None:
    """Convert decimal hours to goal seconds."""
    try:
        hours = float(value)
    except (TypeError, ValueError):
        return None

    if not isfinite(hours) or hours < 0:
        return None

    return int(hours * 3600)


def resolve_daily_goal_seconds(
    mode: str,
    enabled: bool,
    fixed_seconds: int,
    today_seconds: int,
    active_id: int,
    manual_state: Any = None,
    *,
    planned_today: bool = False,
    manual_override_hours: Any = None,
    manual_override_date: str | None = None,
    current_date: str | None = None,
) -> int | None:
    """Resolve the applicable daily goal for the selected mode."""
    if not enabled or mode == DAILY_GOAL_MODE_DISABLED:
        return None

    if mode == DAILY_GOAL_MODE_WORKED_DAYS_ONLY:
        if today_seconds <= 0 and active_id <= 0:
            return None
        return fixed_seconds

    if mode == DAILY_GOAL_MODE_MANUAL_ENTITY:
        return manual_goal_seconds(manual_state)

    if mode == DAILY_GOAL_MODE_WEEKLY_PLAN:
        if manual_override_date and manual_override_date == current_date:
            override = manual_goal_seconds(manual_override_hours)
            if override is not None:
                return override
        return fixed_seconds if planned_today else 0

    return fixed_seconds
