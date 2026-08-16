"""Weekly planning switches for Kimai Homeoffice."""

from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_PLANNED_FRIDAY,
    CONF_PLANNED_MONDAY,
    CONF_PLANNED_THURSDAY,
    CONF_PLANNED_TUESDAY,
    CONF_PLANNED_WEDNESDAY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLANNED_DAYS = (
    (CONF_PLANNED_MONDAY, "planned_monday"),
    (CONF_PLANNED_TUESDAY, "planned_tuesday"),
    (CONF_PLANNED_WEDNESDAY, "planned_wednesday"),
    (CONF_PLANNED_THURSDAY, "planned_thursday"),
    (CONF_PLANNED_FRIDAY, "planned_friday"),
)


class KimaiHomeofficePlannedDaySwitch(SwitchEntity):
    """Switch controlling whether a weekday is planned for homeoffice."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-check"

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        option_key: str,
        translation_key: str,
    ) -> None:
        """Initialize a planned weekday switch."""
        self.hass = hass
        self._entry = entry
        self._option_key = option_key
        self._attr_translation_key = translation_key
        self._attr_unique_id = f"{entry.entry_id}_{option_key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Kimai Homeoffice",
            "manufacturer": "Kimai",
            "model": "Homeoffice Time Tracking",
        }

    @property
    def is_on(self) -> bool:
        """Return whether this weekday is planned."""
        return bool(self._entry.options.get(self._option_key, False))

    async def async_turn_on(self, **kwargs) -> None:
        """Plan this weekday."""
        self._update_option(True)

    async def async_turn_off(self, **kwargs) -> None:
        """Unplan this weekday."""
        self._update_option(False)

    def _update_option(self, value: bool) -> None:
        """Persist a planned weekday option."""
        options = {**self._entry.options, self._option_key: value}
        _LOGGER.debug("Planned day changed: %s=%s", self._option_key, value)
        self.hass.config_entries.async_update_entry(self._entry, options=options)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up weekly planning switches."""
    async_add_entities(
        KimaiHomeofficePlannedDaySwitch(hass, entry, option_key, translation_key)
        for option_key, translation_key in PLANNED_DAYS
    )
