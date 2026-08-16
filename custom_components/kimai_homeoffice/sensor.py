"""Sensors for Kimai Homeoffice."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any, Callable

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DAILY_GOAL_ENABLED,
    CONF_DAILY_GOAL_ENTITY,
    CONF_DAILY_GOAL_HOURS,
    CONF_DAILY_GOAL_MINUTES,
    CONF_DAILY_GOAL_MODE,
    CONF_MANUAL_DAILY_GOAL_DATE,
    CONF_MANUAL_DAILY_GOAL_HOURS,
    CONF_PLANNED_FRIDAY,
    CONF_PLANNED_MONDAY,
    CONF_PLANNED_THURSDAY,
    CONF_PLANNED_TUESDAY,
    CONF_PLANNED_WEDNESDAY,
    CONF_ROUNDING_ENABLED,
    CONF_ROUNDING_MINUTES,
    CONF_ROUNDING_MODE,
    CONF_WEEKLY_GOAL_ENABLED,
    CONF_WEEKLY_GOAL_HOURS,
    CONF_WEEKLY_GOAL_MINUTES,
    DEFAULT_DAILY_GOAL_ENABLED,
    DEFAULT_DAILY_GOAL_HOURS,
    DEFAULT_DAILY_GOAL_MINUTES,
    DEFAULT_DAILY_GOAL_MODE,
    DEFAULT_ROUNDING_ENABLED,
    DEFAULT_ROUNDING_MINUTES,
    DEFAULT_ROUNDING_MODE,
    DEFAULT_WEEKLY_GOAL_ENABLED,
    DEFAULT_WEEKLY_GOAL_HOURS,
    DEFAULT_WEEKLY_GOAL_MINUTES,
    DAILY_GOAL_MODE_MANUAL_ENTITY,
    DAILY_GOAL_MODE_WEEKLY_PLAN,
    DOMAIN,
)
from .coordinator import KimaiHomeofficeCoordinator
from .daily_goal import resolve_daily_goal_seconds
from .kimai_api import KimaiSummary

_LOGGER = logging.getLogger(__name__)


def _seconds_to_hhmm(seconds: int | None) -> str:
    """Convert seconds to HH:MM."""
    if seconds is None:
        seconds = 0

    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    return f"{hours:02d}:{minutes:02d}"


def _seconds_to_signed_hhmm(seconds: int) -> str:
    """Convert seconds to signed HH:MM."""
    seconds = int(seconds)
    if seconds == 0:
        return "±00:00"

    sign = "+" if seconds > 0 else "-"
    return f"{sign}{_seconds_to_hhmm(abs(seconds))}"


def _remaining_seconds(worked_seconds: int, goal_seconds: int) -> int:
    """Return remaining work time without negative values."""
    return max(goal_seconds - worked_seconds, 0)


def _goal_seconds(hours: int, minutes: int) -> int:
    """Convert goal hours and minutes to seconds."""
    return (int(hours) * 60 + int(minutes)) * 60


def _round_seconds(seconds: int, rounding_minutes: int, mode: str) -> int:
    """Round positive seconds to the configured minute interval."""
    seconds = int(seconds)
    rounding_minutes = int(rounding_minutes)
    if seconds <= 0:
        return 0
    if rounding_minutes <= 0:
        return seconds

    step = rounding_minutes * 60
    if mode == "floor":
        return seconds // step * step
    if mode == "nearest":
        return (seconds + step // 2) // step * step

    return (seconds + step - 1) // step * step


def _daily_goal_reached_at(
    data: KimaiSummary,
    goal_seconds: int | None,
    worked_seconds: int,
) -> str | None:
    """Return the current or estimated daily goal time."""
    if goal_seconds is None:
        return None

    remaining = _remaining_seconds(worked_seconds, goal_seconds)
    now = dt_util.now()

    if remaining == 0:
        return now.strftime("%H:%M")

    if data.active_id <= 0:
        return None

    return (now + timedelta(seconds=remaining)).strftime("%H:%M")


class KimaiHomeofficeSensor(CoordinatorEntity[KimaiHomeofficeCoordinator], SensorEntity):
    """Kimai Homeoffice sensor."""

    def __init__(
        self,
        coordinator: KimaiHomeofficeCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str | None,
        icon: str,
        value_fn: Callable[[KimaiSummary], Any],
        *,
        translation_key: str | None = None,
        available_fn: Callable[[KimaiSummary], bool] | None = None,
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)

        self._key = key
        self._value_fn = value_fn
        self._available_fn = available_fn

        if translation_key:
            self._attr_has_entity_name = True
            self._attr_translation_key = translation_key
        else:
            self._attr_name = f"Kimai Homeoffice {name}"
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_icon = icon
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Kimai Homeoffice",
            "manufacturer": "Kimai",
            "model": "Homeoffice Time Tracking",
        }

    @property
    def native_value(self) -> Any:
        """Return sensor value."""
        if self.coordinator.data is None:
            return None

        return self._value_fn(self.coordinator.data)

    @property
    def available(self) -> bool:
        """Return whether the sensor is available."""
        if not super().available or self.coordinator.data is None:
            return False

        if self._available_fn is None:
            return True

        return self._available_fn(self.coordinator.data)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kimai Homeoffice sensors."""
    coordinator: KimaiHomeofficeCoordinator = hass.data[DOMAIN][entry.entry_id]
    daily_goal_enabled = bool(
        entry.options.get(CONF_DAILY_GOAL_ENABLED, DEFAULT_DAILY_GOAL_ENABLED)
    )
    fixed_daily_goal_seconds = _goal_seconds(
        entry.options.get(CONF_DAILY_GOAL_HOURS, DEFAULT_DAILY_GOAL_HOURS),
        entry.options.get(CONF_DAILY_GOAL_MINUTES, DEFAULT_DAILY_GOAL_MINUTES),
    )
    daily_goal_mode = str(
        entry.options.get(CONF_DAILY_GOAL_MODE, DEFAULT_DAILY_GOAL_MODE)
    )
    daily_goal_entity = entry.options.get(CONF_DAILY_GOAL_ENTITY) or None
    if daily_goal_mode == DAILY_GOAL_MODE_MANUAL_ENTITY and not daily_goal_entity:
        _LOGGER.warning("Manual daily goal entity is not configured")
    weekly_goal_enabled = bool(
        entry.options.get(CONF_WEEKLY_GOAL_ENABLED, DEFAULT_WEEKLY_GOAL_ENABLED)
    )
    weekly_goal_seconds = _goal_seconds(
        entry.options.get(CONF_WEEKLY_GOAL_HOURS, DEFAULT_WEEKLY_GOAL_HOURS),
        entry.options.get(CONF_WEEKLY_GOAL_MINUTES, DEFAULT_WEEKLY_GOAL_MINUTES),
    )
    rounding_enabled = bool(
        entry.options.get(CONF_ROUNDING_ENABLED, DEFAULT_ROUNDING_ENABLED)
    )
    rounding_minutes = int(
        entry.options.get(CONF_ROUNDING_MINUTES, DEFAULT_ROUNDING_MINUTES)
    )
    rounding_mode = str(
        entry.options.get(CONF_ROUNDING_MODE, DEFAULT_ROUNDING_MODE)
    )
    planned_day_options = (
        CONF_PLANNED_MONDAY,
        CONF_PLANNED_TUESDAY,
        CONF_PLANNED_WEDNESDAY,
        CONF_PLANNED_THURSDAY,
        CONF_PLANNED_FRIDAY,
    )

    def displayed_seconds(seconds: int) -> int:
        """Return raw or configured rounded seconds for display."""
        if not rounding_enabled:
            return seconds
        return _round_seconds(seconds, rounding_minutes, rounding_mode)

    def daily_goal_seconds(data: KimaiSummary) -> int | None:
        """Return the currently applicable daily goal."""
        manual_state: Any = None
        if daily_goal_mode == DAILY_GOAL_MODE_MANUAL_ENTITY:
            if daily_goal_entity:
                state = hass.states.get(daily_goal_entity)
                if state is None or state.state in {
                    STATE_UNKNOWN,
                    STATE_UNAVAILABLE,
                    "",
                }:
                    _LOGGER.debug(
                        "Manual daily goal entity %s has no valid state",
                        daily_goal_entity,
                    )
                else:
                    manual_state = state.state

        today = dt_util.now().date()
        planned_today = today.weekday() < len(planned_day_options) and bool(
            entry.options.get(planned_day_options[today.weekday()], False)
        )
        manual_override_date = entry.options.get(CONF_MANUAL_DAILY_GOAL_DATE)
        if (
            daily_goal_mode == DAILY_GOAL_MODE_WEEKLY_PLAN
            and manual_override_date
            and manual_override_date != today.isoformat()
        ):
            _LOGGER.debug("Stale manual daily goal ignored")

        goal = resolve_daily_goal_seconds(
            daily_goal_mode,
            daily_goal_enabled,
            fixed_daily_goal_seconds,
            data.today_seconds,
            data.active_id,
            manual_state=manual_state,
            planned_today=planned_today,
            manual_override_hours=entry.options.get(
                CONF_MANUAL_DAILY_GOAL_HOURS
            ),
            manual_override_date=manual_override_date,
            current_date=today.isoformat(),
        )
        if (
            daily_goal_mode == DAILY_GOAL_MODE_MANUAL_ENTITY
            and goal is None
            and manual_state is not None
        ):
            _LOGGER.debug(
                "Manual daily goal entity %s is not numeric",
                daily_goal_entity,
            )
        if daily_goal_mode == DAILY_GOAL_MODE_WEEKLY_PLAN:
            _LOGGER.debug(
                "Weekly plan daily goal resolved: %s",
                _seconds_to_hhmm(goal),
            )
        return goal
    _LOGGER.debug(
        "Goal sensors updated with daily goal %s and weekly goal %s",
        _seconds_to_hhmm(fixed_daily_goal_seconds),
        _seconds_to_hhmm(weekly_goal_seconds),
    )

    sensors = [
        KimaiHomeofficeSensor(
            coordinator,
            entry,
            "runtime",
            "Laufzeit",
            "mdi:timer-outline",
            lambda data: _seconds_to_hhmm(data.active_seconds),
        ),
        KimaiHomeofficeSensor(
            coordinator,
            entry,
            "daily_goal",
            None,
            "mdi:target",
            lambda data: _seconds_to_hhmm(daily_goal_seconds(data)),
            translation_key="daily_goal",
            available_fn=lambda data: daily_goal_seconds(data) is not None,
        ),
        KimaiHomeofficeSensor(
            coordinator,
            entry,
            "daily_balance",
            None,
            "mdi:scale-balance",
            lambda data: _seconds_to_signed_hhmm(
                displayed_seconds(data.today_seconds)
                - (daily_goal_seconds(data) or 0)
            ),
            translation_key="daily_balance",
            available_fn=lambda data: daily_goal_seconds(data) is not None,
        ),
        KimaiHomeofficeSensor(
            coordinator,
            entry,
            "daily_remaining",
            None,
            "mdi:timer-sand",
            lambda data: _seconds_to_hhmm(
                _remaining_seconds(
                    displayed_seconds(data.today_seconds),
                    daily_goal_seconds(data) or 0,
                )
            ),
            translation_key="daily_remaining",
            available_fn=lambda data: daily_goal_seconds(data) is not None,
        ),
        KimaiHomeofficeSensor(
            coordinator,
            entry,
            "daily_goal_reached_at",
            None,
            "mdi:clock-check-outline",
            lambda data: _daily_goal_reached_at(
                data,
                daily_goal_seconds(data),
                displayed_seconds(data.today_seconds),
            ),
            translation_key="daily_goal_reached_at",
            available_fn=lambda data: (daily_goal_seconds(data) or 0) > 0
            and (
                displayed_seconds(data.today_seconds)
                >= (daily_goal_seconds(data) or 0)
                or data.active_id > 0
            ),
        ),
        KimaiHomeofficeSensor(
            coordinator,
            entry,
            "weekly_goal",
            None,
            "mdi:calendar-week",
            lambda data: _seconds_to_hhmm(weekly_goal_seconds),
            translation_key="weekly_goal",
            available_fn=lambda data: weekly_goal_enabled,
        ),
        KimaiHomeofficeSensor(
            coordinator,
            entry,
            "weekly_balance",
            None,
            "mdi:calendar-clock",
            lambda data: _seconds_to_signed_hhmm(
                displayed_seconds(data.week_seconds) - weekly_goal_seconds
            ),
            translation_key="weekly_balance",
            available_fn=lambda data: weekly_goal_enabled,
        ),
        KimaiHomeofficeSensor(
            coordinator,
            entry,
            "today",
            "Heute",
            "mdi:clock-outline",
            lambda data: _seconds_to_hhmm(displayed_seconds(data.today_seconds)),
        ),
        KimaiHomeofficeSensor(
            coordinator,
            entry,
            "week",
            "Woche",
            "mdi:calendar-week",
            lambda data: _seconds_to_hhmm(displayed_seconds(data.week_seconds)),
        ),
        KimaiHomeofficeSensor(
            coordinator,
            entry,
            "month",
            "Monat",
            "mdi:calendar-month",
            lambda data: _seconds_to_hhmm(displayed_seconds(data.month_seconds)),
        ),
        KimaiHomeofficeSensor(
            coordinator,
            entry,
            "active_id",
            "Aktive ID",
            "mdi:identifier",
            lambda data: data.active_id,
        ),
        KimaiHomeofficeSensor(
            coordinator,
            entry,
            "begin",
            "Beginn",
            "mdi:clock-start",
            lambda data: data.active_begin or "",
        ),
    ]

    async_add_entities(sensors)
