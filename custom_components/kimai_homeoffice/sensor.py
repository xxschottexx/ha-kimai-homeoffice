"""Sensors for Kimai Homeoffice."""

from __future__ import annotations

from typing import Any, Callable

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KimaiHomeofficeCoordinator
from .kimai_api import KimaiSummary


def _seconds_to_hhmm(seconds: int | None) -> str:
    """Convert seconds to HH:MM."""
    if seconds is None:
        seconds = 0

    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    return f"{hours:02d}:{minutes:02d}"


class KimaiHomeofficeSensor(CoordinatorEntity[KimaiHomeofficeCoordinator], SensorEntity):
    """Kimai Homeoffice sensor."""

    def __init__(
        self,
        coordinator: KimaiHomeofficeCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        icon: str,
        value_fn: Callable[[KimaiSummary], Any],
    ) -> None:
        """Initialize sensor."""
        super().__init__(coordinator)

        self._key = key
        self._value_fn = value_fn

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


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kimai Homeoffice sensors."""
    coordinator: KimaiHomeofficeCoordinator = hass.data[DOMAIN][entry.entry_id]

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
            "today",
            "Heute",
            "mdi:clock-outline",
            lambda data: _seconds_to_hhmm(data.today_seconds),
        ),
        KimaiHomeofficeSensor(
            coordinator,
            entry,
            "week",
            "Woche",
            "mdi:calendar-week",
            lambda data: _seconds_to_hhmm(data.week_seconds),
        ),
        KimaiHomeofficeSensor(
            coordinator,
            entry,
            "month",
            "Monat",
            "mdi:calendar-month",
            lambda data: _seconds_to_hhmm(data.month_seconds),
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
