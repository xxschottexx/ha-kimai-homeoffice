"""Binary sensors for Kimai Homeoffice."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KimaiHomeofficeCoordinator


class KimaiHomeofficeRunningBinarySensor(
    CoordinatorEntity[KimaiHomeofficeCoordinator],
    BinarySensorEntity,
):
    """Kimai Homeoffice running binary sensor."""

    def __init__(
        self,
        coordinator: KimaiHomeofficeCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize binary sensor."""
        super().__init__(coordinator)

        self._attr_name = "Kimai Homeoffice Eingestempelt"
        self._attr_unique_id = f"{entry.entry_id}_running"
        self._attr_icon = "mdi:home-clock"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Kimai Homeoffice",
            "manufacturer": "Kimai",
            "model": "Homeoffice Time Tracking",
        }

    @property
    def is_on(self) -> bool:
        """Return true if Kimai has an active timesheet."""
        if self.coordinator.data is None:
            return False

        return self.coordinator.data.active_id > 0

    @property
    def icon(self) -> str:
        """Return dynamic icon."""
        if self.is_on:
            return "mdi:timer-play"

        return "mdi:timer-stop"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kimai Homeoffice binary sensors."""
    coordinator: KimaiHomeofficeCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            KimaiHomeofficeRunningBinarySensor(coordinator, entry),
        ]
    )