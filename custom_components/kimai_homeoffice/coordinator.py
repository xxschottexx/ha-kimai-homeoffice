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
    CONF_NOTIFY,
    CONF_NOTIFY_SERVICE,
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

    async def async_stop(self) -> bool:
        """Stop an active Kimai timesheet and report whether it was stopped."""
        stopped = await self.api.stop_timesheet()
        if not stopped:
            return False

        try:
            await self.async_request_refresh()
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Kimai data refresh after clock-out failed: %s", err)

        if self._should_send_notification():
            await self._async_send_stop_notification()

        return True

    def _should_send_notification(self) -> bool:
        return bool(
            self.entry.options.get(CONF_NOTIFY, False)
            and self._notify_service
        )

    @property
    def _notify_service(self) -> str:
        notify_service = str(
            self.entry.options.get(CONF_NOTIFY_SERVICE, "")
        ).strip()
        while notify_service.startswith("notify_service."):
            notify_service = notify_service.removeprefix("notify_service.")
        return notify_service

    async def _async_send_stop_notification(self) -> None:
        notify_service = self._notify_service
        if not notify_service.startswith("notify."):
            _LOGGER.warning(
                "Notify service ist ungültig oder fehlt: %s",
                notify_service,
            )
            return

        domain, service = notify_service.split(".", 1)
        message = "Ausgestempelt."
        today_seconds = getattr(self.data, "today_seconds", None)
        if today_seconds is not None:
            today = self.format_seconds(today_seconds)
            message = f"Ausgestempelt. Heute gearbeitet: {today}"

        try:
            await self.hass.services.async_call(
                domain,
                service,
                {
                    "title": "Daimler Homeoffice",
                    "message": message,
                },
                blocking=False,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Benachrichtigung konnte nicht gesendet werden: %s", err)

    @staticmethod
    def format_seconds(seconds: int) -> str:
        """Return seconds formatted as HH:MM."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"

    async def async_toggle(self) -> None:
        """Toggle Kimai timesheet."""
        active_id = 0

        if self.data is not None:
            active_id = self.data.active_id

        if active_id > 0:
            await self.async_stop()
            return

        await self.async_start()
