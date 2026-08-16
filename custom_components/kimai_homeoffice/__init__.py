"""Kimai Homeoffice integration."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from time import monotonic

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_OFF, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import (
    async_call_later,
    async_track_point_in_time,
    async_track_state_change_event,
)
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_AUTO_START,
    CONF_BUTTON_COOLDOWN_SECONDS,
    CONF_BUTTON_ENABLED,
    CONF_BUTTON_ENTITY,
    CONF_BUTTON_MQTT_JSON_KEY,
    CONF_BUTTON_MQTT_TOPIC,
    CONF_BUTTON_TRIGGER_TYPE,
    CONF_BUTTON_VALID_STATES,
    CONF_OFFLINE_MINUTES,
    CONF_OFFLINE_STOP,
    CONF_SAFETY_STOP,
    CONF_SAFETY_STOP_TIME,
    CONF_START_AFTER,
    CONF_START_BEFORE,
    CONF_WORKER_SENSOR,
    DEFAULT_BUTTON_COOLDOWN_SECONDS,
    DEFAULT_BUTTON_TRIGGER_TYPE,
    DEFAULT_BUTTON_VALID_STATES,
)
from .coordinator import KimaiHomeofficeCoordinator

_LOGGER = logging.getLogger(__name__)


def _parse_mqtt_button_payload(payload, json_key: str | None) -> str | None:
    """Extract a button value from a plain or JSON MQTT payload."""
    text = payload.decode() if isinstance(payload, bytes) else str(payload)
    if not json_key:
        return text

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict) or json_key not in data:
        return None

    return str(data[json_key])


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


class KimaiHomeofficeAutomation:
    """Automation helper for Kimai Homeoffice."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, coordinator: KimaiHomeofficeCoordinator) -> None:
        self.hass = hass
        self.entry = entry
        self.coordinator = coordinator
        self._state_unsub: CALLBACK_TYPE | None = None
        self._button_unsub: CALLBACK_TYPE | None = None
        self._button_listener_type: str | None = None
        self._offline_unsub: CALLBACK_TYPE | None = None
        self._safety_unsub: CALLBACK_TYPE | None = None
        self._last_button_press = 0.0

    async def async_initialize(self) -> None:
        self._setup_worker_sensor_listener()
        await self._async_setup_button_listener()
        await self._async_schedule_safety_stop()

    def async_remove(self) -> None:
        self._cancel_offline_timer()
        self._cancel_safety_stop()
        if self._state_unsub:
            self._state_unsub()
            self._state_unsub = None
        self._remove_button_listener()

    def _remove_button_listener(self) -> None:
        """Remove the active button listener, if any."""
        if self._button_unsub is None:
            return

        self._button_unsub()
        self._button_unsub = None

        if self._button_listener_type == "mqtt":
            _LOGGER.info("MQTT button listener removed")
        elif self._button_listener_type == "entity":
            _LOGGER.info("Entity button listener removed")

        self._button_listener_type = None

    def _setup_worker_sensor_listener(self) -> None:
        worker_sensor = self._worker_sensor
        if not worker_sensor:
            return

        self._state_unsub = async_track_state_change_event(
            self.hass,
            [worker_sensor],
            self._async_worker_state_changed,
        )

    async def _async_setup_button_listener(self) -> None:
        self._remove_button_listener()

        if not self._button_enabled:
            return

        if self._button_trigger_type == "mqtt":
            await self._async_setup_mqtt_button_listener()
            return

        self._setup_entity_button_listener()

    def _setup_entity_button_listener(self) -> None:
        button_entity = self._button_entity
        if not button_entity:
            _LOGGER.warning(
                "Button entity missing while entity button mode is enabled"
            )
            return

        self._button_unsub = async_track_state_change_event(
            self.hass,
            [button_entity],
            self._async_button_state_changed,
        )
        self._button_listener_type = "entity"
        _LOGGER.info(
            "Entity button listener registered for entity %s",
            button_entity,
        )

    async def _async_setup_mqtt_button_listener(self) -> None:
        topic = self._button_mqtt_topic
        if not topic:
            _LOGGER.warning(
                "MQTT topic missing while MQTT button mode is enabled"
            )
            return

        try:
            from homeassistant.components import mqtt

            self._button_unsub = await mqtt.async_subscribe(
                self.hass,
                topic,
                self._mqtt_button_message,
            )
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("MQTT unavailable: %s", err)
            return

        self._button_listener_type = "mqtt"
        _LOGGER.info("MQTT button listener registered for topic %s", topic)

    def _cancel_offline_timer(self) -> None:
        if self._offline_unsub:
            self._offline_unsub()
            self._offline_unsub = None

    def _cancel_safety_stop(self) -> None:
        if self._safety_unsub:
            self._safety_unsub()
            self._safety_unsub = None

    @property
    def _worker_sensor(self) -> str | None:
        return self.entry.options.get(CONF_WORKER_SENSOR) or None

    @property
    def _auto_start_enabled(self) -> bool:
        return bool(self.entry.options.get(CONF_AUTO_START, False))

    @property
    def _offline_stop_enabled(self) -> bool:
        return bool(self.entry.options.get(CONF_OFFLINE_STOP, False))

    @property
    def _offline_minutes(self) -> int:
        return int(self.entry.options.get(CONF_OFFLINE_MINUTES, 5))

    @property
    def _safety_stop_enabled(self) -> bool:
        return bool(self.entry.options.get(CONF_SAFETY_STOP, False))

    @property
    def _safety_stop_time(self) -> str:
        return str(self.entry.options.get(CONF_SAFETY_STOP_TIME, "17:15"))

    @property
    def _start_after(self) -> str:
        return str(self.entry.options.get(CONF_START_AFTER, "05:00"))

    @property
    def _start_before(self) -> str:
        return str(self.entry.options.get(CONF_START_BEFORE, "17:00"))

    @property
    def _button_enabled(self) -> bool:
        return bool(self.entry.options.get(CONF_BUTTON_ENABLED, False))

    @property
    def _button_entity(self) -> str | None:
        return self.entry.options.get(CONF_BUTTON_ENTITY) or None

    @property
    def _button_trigger_type(self) -> str:
        return str(
            self.entry.options.get(
                CONF_BUTTON_TRIGGER_TYPE,
                DEFAULT_BUTTON_TRIGGER_TYPE,
            )
        )

    @property
    def _button_mqtt_topic(self) -> str | None:
        return self.entry.options.get(CONF_BUTTON_MQTT_TOPIC) or None

    @property
    def _button_mqtt_json_key(self) -> str | None:
        return self.entry.options.get(CONF_BUTTON_MQTT_JSON_KEY) or None

    @property
    def _button_valid_states(self) -> set[str]:
        raw_states = str(
            self.entry.options.get(
                CONF_BUTTON_VALID_STATES,
                DEFAULT_BUTTON_VALID_STATES,
            )
        )
        return {
            state.strip().lower()
            for state in raw_states.split(",")
            if state.strip()
        }

    @property
    def _button_cooldown_seconds(self) -> int:
        try:
            return max(
                0,
                min(
                    30,
                    int(
                        self.entry.options.get(
                            CONF_BUTTON_COOLDOWN_SECONDS,
                            DEFAULT_BUTTON_COOLDOWN_SECONDS,
                        )
                    ),
                ),
            )
        except (TypeError, ValueError):
            return DEFAULT_BUTTON_COOLDOWN_SECONDS

    def _active_id(self) -> int:
        if self.coordinator.data is None:
            return 0
        return self.coordinator.data.active_id

    async def _async_worker_state_changed(self, event) -> None:
        new_state = event.data.get("new_state")
        if new_state is None:
            return

        if new_state.state == STATE_ON:
            self._cancel_offline_timer()
            await self._async_handle_auto_start()
            return

        if new_state.state == STATE_OFF:
            await self._async_schedule_offline_stop()

    async def _async_button_state_changed(self, event) -> None:
        new_state = event.data.get("new_state")
        if new_state is None:
            _LOGGER.debug("Button state ignored: new state is missing")
            return

        await self._async_handle_button_value(new_state.state)

    @callback
    def _mqtt_button_message(self, message) -> None:
        self.hass.async_create_task(self._async_handle_mqtt_button_message(message))

    async def _async_handle_mqtt_button_message(self, message) -> None:
        value = self._mqtt_button_value(message.payload)
        await self._async_handle_button_value(value)

    def _mqtt_button_value(self, payload) -> str | None:
        value = _parse_mqtt_button_payload(payload, self._button_mqtt_json_key)
        if value is None:
            _LOGGER.debug("Button payload ignored because value is not valid")
        return value

    async def _async_handle_button_value(self, value) -> None:
        if value is None:
            _LOGGER.debug("Button payload ignored because value is not valid")
            return

        state = str(value).strip()
        normalized_state = state.lower()
        if normalized_state in {STATE_UNKNOWN, STATE_UNAVAILABLE, "none", ""}:
            _LOGGER.debug("Button payload ignored because value is not valid")
            return

        if normalized_state not in self._button_valid_states:
            _LOGGER.debug("Button payload ignored because value is not valid")
            return

        now = monotonic()
        cooldown_seconds = self._button_cooldown_seconds
        if (
            cooldown_seconds > 0
            and now - self._last_button_press < cooldown_seconds
        ):
            _LOGGER.debug("Button press ignored because cooldown is active")
            return

        self._last_button_press = now

        try:
            await self.coordinator.async_toggle()
            _LOGGER.debug("Button toggle executed")
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Button toggle failed: %s", err)

    async def _async_handle_auto_start(self) -> None:
        if not self._auto_start_enabled:
            return

        if self._active_id() > 0:
            return

        if not self._is_within_start_window():
            return

        try:
            await self.coordinator.async_start()
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Auto-Start fehlgeschlagen: %s", err)

    async def _async_schedule_offline_stop(self) -> None:
        self._cancel_offline_timer()

        if not self._offline_stop_enabled:
            return

        if self._active_id() <= 0:
            return

        self._offline_unsub = async_call_later(
            self.hass,
            self._offline_minutes * 60,
            self._async_handle_offline_stop,
        )

    async def _async_handle_offline_stop(self, _now) -> None:
        if not self._offline_stop_enabled:
            return

        worker_sensor = self._worker_sensor
        if not worker_sensor:
            return

        state = self.hass.states.get(worker_sensor)
        if state is None or state.state != STATE_OFF:
            return

        if self._active_id() <= 0:
            return

        try:
            await self.coordinator.async_stop()
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Offline-Stopp fehlgeschlagen: %s", err)

    async def _async_schedule_safety_stop(self) -> None:
        self._cancel_safety_stop()

        if not self._safety_stop_enabled:
            return

        fire_time = self._async_next_safety_stop_time()
        if fire_time is None:
            return

        self._safety_unsub = async_track_point_in_time(
            self.hass,
            self._async_handle_safety_stop,
            fire_time,
        )

    async def _async_handle_safety_stop(self, _now) -> None:
        if not self._safety_stop_enabled:
            return

        if self._active_id() <= 0:
            await self._async_schedule_safety_stop()
            return

        try:
            await self.coordinator.async_stop()
        except Exception as err:  # noqa: BLE001
            _LOGGER.error("Sicherheits-Stopp fehlgeschlagen: %s", err)
        finally:
            await self._async_schedule_safety_stop()

    def _async_next_safety_stop_time(self) -> datetime | None:
        try:
            stop_time = datetime.strptime(self._safety_stop_time, "%H:%M").time()
        except ValueError:
            _LOGGER.error("Ungültige Sicherheits-Stopp-Zeit: %s", self._safety_stop_time)
            return None

        now = dt_util.now()
        fire_time = datetime.combine(now.date(), stop_time, tzinfo=now.tzinfo)
        if fire_time <= now:
            fire_time = fire_time + timedelta(days=1)

        return fire_time

    def _is_within_start_window(self) -> bool:
        try:
            start_time = datetime.strptime(self._start_after, "%H:%M").time()
            end_time = datetime.strptime(self._start_before, "%H:%M").time()
            now_time = dt_util.now().time()
        except ValueError:
            _LOGGER.warning("Ungültiges Startzeitfenster: %s - %s", self._start_after, self._start_before)
            return False

        if start_time <= end_time:
            return start_time <= now_time <= end_time

        return now_time >= start_time or now_time <= end_time


async def _async_update_listener(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Reload the config entry after options are updated."""
    _LOGGER.info("Options updated, reloading Kimai Homeoffice entry")
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Kimai Homeoffice from a config entry."""
    coordinator = KimaiHomeofficeCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    automation = KimaiHomeofficeAutomation(hass, entry, coordinator)
    await automation.async_initialize()
    entry.async_on_unload(automation.async_remove)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

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
