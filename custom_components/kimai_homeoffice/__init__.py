"""Kimai Homeoffice integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, PLATFORMS
from .coordinator import KimaiHomeofficeCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Kimai Homeoffice services."""

    async def _get_coordinator(call: ServiceCall) -> KimaiHomeofficeCoordinator:
        """Return first configured coordinator."""
        entries = hass.config_entries.async_entries(DOMAIN)

        if not entries:
            raise HomeAssistantError("Kimai Homeoffice ist nicht eingerichtet")

        entry = entries[0]
        coordinator: KimaiHomeofficeCoordinator | None = hass.data.get(DOMAIN, {}).get(
            entry.entry_id
        )

        if coordinator is None:
            raise HomeAssistantError("Kimai Homeoffice ist nicht geladen")

        return coordinator

    async def _handle_start(call: ServiceCall) -> None:
        """Handle start service."""
        coordinator = await _get_coordinator(call)
        await coordinator.async_start()

    async def _handle_stop(call: ServiceCall) -> None:
        """Handle stop service."""
        coordinator = await _get_coordinator(call)
        await coordinator.async_stop()

    async def _handle_toggle(call: ServiceCall) -> None:
        """Handle toggle service."""
        coordinator = await _get_coordinator(call)
        await coordinator.async_toggle()

    async def _handle_refresh(call: ServiceCall) -> None:
        """Handle refresh service."""
        coordinator = await _get_coordinator(call)
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, "start", _handle_start)
    hass.services.async_register(DOMAIN, "stop", _handle_stop)
    hass.services.async_register(DOMAIN, "toggle", _handle_toggle)
    hass.services.async_register(DOMAIN, "refresh", _handle_refresh)

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Kimai Homeoffice from a config entry."""
    coordinator = KimaiHomeofficeCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok