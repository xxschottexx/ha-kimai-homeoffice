"""Daily goal number entity for Kimai Homeoffice."""

from __future__ import annotations

from datetime import date
import logging

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
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
    DEFAULT_DAILY_GOAL_HOURS,
    DEFAULT_DAILY_GOAL_MINUTES,
    DEFAULT_DAILY_GOAL_MODE,
    DAILY_GOAL_MODE_WEEKLY_PLAN,
    DOMAIN,
)
from .coordinator import KimaiHomeofficeCoordinator
from .daily_goal import resolve_daily_goal_seconds

_LOGGER = logging.getLogger(__name__)

PLANNED_DAY_OPTIONS = (
    CONF_PLANNED_MONDAY,
    CONF_PLANNED_TUESDAY,
    CONF_PLANNED_WEDNESDAY,
    CONF_PLANNED_THURSDAY,
    CONF_PLANNED_FRIDAY,
)


class KimaiHomeofficeDailyGoalNumber(
    CoordinatorEntity[KimaiHomeofficeCoordinator],
    NumberEntity,
):
    """Number entity for today's manual daily goal override."""

    _attr_has_entity_name = True
    _attr_translation_key = "daily_goal_today"
    _attr_icon = "mdi:target-account"
    _attr_native_min_value = 0
    _attr_native_max_value = 12
    _attr_native_step = 0.25
    _attr_native_unit_of_measurement = UnitOfTime.HOURS

    def __init__(
        self,
        coordinator: KimaiHomeofficeCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the daily goal number."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_daily_goal_today"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Kimai Homeoffice",
            "manufacturer": "Kimai",
            "model": "Homeoffice Time Tracking",
        }

    @property
    def native_value(self) -> float:
        """Return today's effective weekly-plan goal in hours."""
        today = dt_util.now().date()
        fixed_seconds = (
            int(
                self._entry.options.get(
                    CONF_DAILY_GOAL_HOURS,
                    DEFAULT_DAILY_GOAL_HOURS,
                )
            )
            * 3600
            + int(
                self._entry.options.get(
                    CONF_DAILY_GOAL_MINUTES,
                    DEFAULT_DAILY_GOAL_MINUTES,
                )
            )
            * 60
        )
        goal = resolve_daily_goal_seconds(
            "weekly_plan",
            True,
            fixed_seconds,
            0,
            0,
            planned_today=self._planned_today(today),
            manual_override_hours=self._entry.options.get(
                CONF_MANUAL_DAILY_GOAL_HOURS
            ),
            manual_override_date=self._entry.options.get(
                CONF_MANUAL_DAILY_GOAL_DATE
            ),
            current_date=today.isoformat(),
        )
        return (goal or 0) / 3600

    @property
    def available(self) -> bool:
        """Return whether weekly planning is active."""
        return super().available and self._entry.options.get(
            CONF_DAILY_GOAL_MODE,
            DEFAULT_DAILY_GOAL_MODE,
        ) == DAILY_GOAL_MODE_WEEKLY_PLAN

    async def async_set_native_value(self, value: float) -> None:
        """Persist a manual goal override for today."""
        today = dt_util.now().date().isoformat()
        options = {
            **self._entry.options,
            CONF_MANUAL_DAILY_GOAL_HOURS: float(value),
            CONF_MANUAL_DAILY_GOAL_DATE: today,
        }
        _LOGGER.debug("Manual daily goal changed: %s hours for %s", value, today)
        self.hass.config_entries.async_update_entry(self._entry, options=options)

    def _planned_today(self, today: date) -> bool:
        """Return whether today's weekday is planned."""
        if today.weekday() >= len(PLANNED_DAY_OPTIONS):
            return False
        return bool(
            self._entry.options.get(PLANNED_DAY_OPTIONS[today.weekday()], False)
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the daily goal number entity."""
    coordinator: KimaiHomeofficeCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([KimaiHomeofficeDailyGoalNumber(coordinator, entry)])
