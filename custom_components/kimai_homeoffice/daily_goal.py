"""Daily goal helpers for Kimai Homeoffice."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

from .const import (
    DAILY_GOAL_MODE_DISABLED,
    DAILY_GOAL_MODE_MANUAL_ENTITY,
    DAILY_GOAL_MODE_WEEKLY_PLAN,
    DAILY_GOAL_MODE_WORKED_DAYS_ONLY,
)


@dataclass(frozen=True)
class DailyGoalResolution:
    """Resolved daily goal and whether balance calculations apply."""

    seconds: int
    applicable: bool
    reason: str


@dataclass(frozen=True)
class DailyGoalValues:
    """Daily sensor values derived from one goal resolution."""

    goal_seconds: int
    balance_seconds: int
    remaining_seconds: int
    applicable: bool


def manual_goal_seconds(value: Any) -> int | None:
    """Convert decimal hours to goal seconds."""
    try:
        hours = float(value)
    except (TypeError, ValueError):
        return None

    if not isfinite(hours) or hours < 0:
        return None

    return int(hours * 3600)


def resolve_daily_goal(
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
) -> DailyGoalResolution:
    """Resolve the applicable daily goal for the selected mode."""
    if not enabled or mode == DAILY_GOAL_MODE_DISABLED:
        return DailyGoalResolution(0, False, "disabled")

    if mode == DAILY_GOAL_MODE_WORKED_DAYS_ONLY:
        if today_seconds <= 0 and active_id <= 0:
            return DailyGoalResolution(0, False, "no_work_today")
        return DailyGoalResolution(fixed_seconds, True, "worked_days_only")

    if mode == DAILY_GOAL_MODE_MANUAL_ENTITY:
        manual_seconds = manual_goal_seconds(manual_state)
        if manual_seconds is None:
            return DailyGoalResolution(0, False, "invalid_manual_entity")
        return DailyGoalResolution(manual_seconds, True, "manual_entity")

    if mode == DAILY_GOAL_MODE_WEEKLY_PLAN:
        if manual_override_date and manual_override_date == current_date:
            override = manual_goal_seconds(manual_override_hours)
            if override is not None:
                return DailyGoalResolution(
                    override,
                    override > 0,
                    "manual_override" if override > 0 else "manual_no_goal",
                )
        if planned_today:
            return DailyGoalResolution(
                fixed_seconds,
                fixed_seconds > 0,
                "planned_day" if fixed_seconds > 0 else "planned_no_goal",
            )
        return DailyGoalResolution(0, False, "unplanned_day")

    return DailyGoalResolution(fixed_seconds, True, "fixed")


def resolve_daily_goal_seconds(
    mode: str,
    enabled: bool,
    fixed_seconds: int,
    today_seconds: int,
    active_id: int,
    manual_state: Any = None,
    **kwargs: Any,
) -> int | None:
    """Return goal seconds for compatibility with existing callers."""
    resolution = resolve_daily_goal(
        mode,
        enabled,
        fixed_seconds,
        today_seconds,
        active_id,
        manual_state,
        **kwargs,
    )
    if resolution.applicable or mode == DAILY_GOAL_MODE_WEEKLY_PLAN:
        return resolution.seconds

    return None


def calculate_daily_goal_values(
    worked_seconds: int,
    resolution: DailyGoalResolution,
) -> DailyGoalValues:
    """Calculate neutral or applicable daily goal sensor values."""
    if not resolution.applicable:
        return DailyGoalValues(resolution.seconds, 0, 0, False)

    return DailyGoalValues(
        resolution.seconds,
        worked_seconds - resolution.seconds,
        max(resolution.seconds - worked_seconds, 0),
        True,
    )
