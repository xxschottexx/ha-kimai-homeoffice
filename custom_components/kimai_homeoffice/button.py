"""Buttons for Kimai Homeoffice."""

from __future__ import annotations

from typing import Awaitable, Callable

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KimaiHomeofficeCoordinator


class KimaiHomeofficeButton(CoordinatorEntity[KimaiHomeofficeCoordinator], ButtonEntity):
    """Kimai Homeoffice button."""

    def __init__(
        self,
        coordinator: KimaiHomeofficeCoordinator,
        entry: ConfigEntry,
        key: str,
        name: str,
        icon: str,
        action: Callable[[], Awaitable[None]],
    ) -> None:
        """Initialize button."""
        super().__init__(coordinator)

        self._action = action

        self._attr_name = f"Kimai Homeoffice {name}"
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_icon = icon
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Kimai Homeoffice",
            "manufacturer": "Kimai",
            "model": "Homeoffice Time Tracking",
        }

    async def async_press(self) -> None:
        """Handle button press."""
        await self._action()


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kimai Homeoffice buttons."""
    coordinator: KimaiHomeofficeCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            KimaiHomeofficeButton(
                coordinator,
                entry,
                "start",
                "Kommen",
                "mdi:login",
                coordinator.async_start,
            ),
            KimaiHomeofficeButton(
                coordinator,
                entry,
                "stop",
                "Gehen",
                "mdi:logout",
                coordinator.async_stop,
            ),
            KimaiHomeofficeButton(
                coordinator,
                entry,
                "toggle",
                "Toggle",
                "mdi:swap-horizontal",
                coordinator.async_toggle,
            ),
            KimaiHomeofficeButton(
                coordinator,
                entry,
                "refresh",
                "Aktualisieren",
                "mdi:refresh",
                coordinator.async_request_refresh,
            ),
        ]
    )