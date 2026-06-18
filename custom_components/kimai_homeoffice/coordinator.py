"""Data coordinator for Kimai Homeoffice."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_ACTIVITY_ID,
    CONF_API_TOKEN,
    CONF_BASE_URL,
    CONF_PROJECT_ID,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .kimai_api import KimaiApi, KimaiApiError, KimaiSummary

_LOGGER = logging.getLogger(__name__)


class KimaiHomeofficeCoordinator(DataUpdateCoordinator[KimaiSummary]):
    """Kimai Homeoffice data coordinator."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
    ) -> None:
        """Initialize coordinator."""
        self.entry = entry

        session = async_get_clientsession(hass)
        self.api = KimaiApi(
            session,
            entry.data[CONF_BASE_URL],
            entry.data[CONF_API_TOKEN],
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> KimaiSummary:
        """Fetch data from Kimai."""
        try:
            return await self.api.get_summary()
        except KimaiApiError as err:
            raise UpdateFailed(str(err)) from err

    async def async_start(self) -> None:
        """Start Kimai timesheet."""
        await self.api.start_timesheet(
            self.entry.data[CONF_PROJECT_ID],
            self.entry.data[CONF_ACTIVITY_ID],
        )
        await self.async_request_refresh()

    async def async_stop(self) -> None:
        """Stop active Kimai timesheet."""
        await self.api.stop_timesheet()
        await self.async_request_refresh()

    async def async_toggle(self) -> None:
        """Toggle Kimai timesheet."""
        active_id = 0

        if self.data is not None:
            active_id = self.data.active_id

        if active_id > 0:
            await self.async_stop()
            return

        await self.async_start()