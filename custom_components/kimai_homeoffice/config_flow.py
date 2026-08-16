"""Config flow for Kimai Homeoffice."""

from __future__ import annotations

from datetime import datetime
import logging
import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACTIVITY_ID,
    CONF_API_TOKEN,
    CONF_AUTO_START,
    CONF_BASE_URL,
    CONF_BUTTON_COOLDOWN_SECONDS,
    CONF_BUTTON_ENABLED,
    CONF_BUTTON_ENTITY,
    CONF_BUTTON_MQTT_JSON_KEY,
    CONF_BUTTON_MQTT_TOPIC,
    CONF_BUTTON_TRIGGER_TYPE,
    CONF_BUTTON_VALID_STATES,
    CONF_DAILY_GOAL_ENABLED,
    CONF_DAILY_GOAL_ENTITY,
    CONF_DAILY_GOAL_HOURS,
    CONF_DAILY_GOAL_MINUTES,
    CONF_DAILY_GOAL_MODE,
    CONF_NOTIFY,
    CONF_NOTIFY_SERVICE,
    CONF_OFFLINE_MINUTES,
    CONF_OFFLINE_STOP,
    CONF_PROJECT_ID,
    CONF_ROUNDING_ENABLED,
    CONF_ROUNDING_MINUTES,
    CONF_ROUNDING_MODE,
    CONF_WORKER_SENSOR,
    CONF_SAFETY_STOP,
    CONF_SAFETY_STOP_TIME,
    CONF_START_AFTER,
    CONF_START_BEFORE,
    CONF_WEEKLY_GOAL_ENABLED,
    CONF_WEEKLY_GOAL_HOURS,
    CONF_WEEKLY_GOAL_MINUTES,
    DEFAULT_NAME,
    DEFAULT_AUTO_START,
    DEFAULT_BUTTON_COOLDOWN_SECONDS,
    DEFAULT_BUTTON_ENABLED,
    DEFAULT_BUTTON_TRIGGER_TYPE,
    DEFAULT_BUTTON_VALID_STATES,
    DEFAULT_DAILY_GOAL_ENABLED,
    DEFAULT_DAILY_GOAL_HOURS,
    DEFAULT_DAILY_GOAL_MINUTES,
    DEFAULT_DAILY_GOAL_MODE,
    DEFAULT_NOTIFY,
    DEFAULT_OFFLINE_MINUTES,
    DEFAULT_OFFLINE_STOP,
    DEFAULT_ROUNDING_ENABLED,
    DEFAULT_ROUNDING_MINUTES,
    DEFAULT_ROUNDING_MODE,
    DEFAULT_SAFETY_STOP,
    DEFAULT_START_AFTER,
    DEFAULT_START_BEFORE,
    DEFAULT_WEEKLY_GOAL_ENABLED,
    DEFAULT_WEEKLY_GOAL_HOURS,
    DEFAULT_WEEKLY_GOAL_MINUTES,
    DEFAULT_SAFETY_STOP_TIME,
    DOMAIN,
)
from .kimai_api import KimaiApi, KimaiApiError, KimaiAuthError, KimaiConnectionError

_LOGGER = logging.getLogger(__name__)

TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
NOTIFY_SERVICE_PATTERN = re.compile(r"^notify\.[a-z0-9_]+$")


def _is_hhmm(value: Any) -> bool:
    """Return true if value is a strict HH:MM time string."""
    return isinstance(value, str) and TIME_PATTERN.fullmatch(value) is not None


def _parse_hhmm(value: str):
    """Parse a strict HH:MM time string."""
    return datetime.strptime(value, "%H:%M").time()


def _normalize_notify_service(value: Any) -> str:
    """Normalize a Home Assistant notify service value."""
    notify_service = str(value or "").strip()
    while notify_service.startswith("notify_service."):
        notify_service = notify_service.removeprefix("notify_service.")
    return notify_service


class KimaiHomeofficeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Kimai Homeoffice."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""
        self._data: dict[str, Any] = {}
        self._projects: list[dict[str, Any]] = []
        self._activities: list[dict[str, Any]] = []

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Step 1: Kimai connection."""

        errors: dict[str, str] = {}

        if user_input is not None:
            base_url = str(user_input[CONF_BASE_URL]).rstrip("/")
            api_token = str(user_input[CONF_API_TOKEN]).replace("Bearer ", "").strip()

            try:
                session = async_get_clientsession(self.hass)
                api = KimaiApi(session, base_url, api_token)

                user = await api.get_user()
                projects = await api.list_projects()

                if not projects:
                    errors["base"] = "no_projects"
                else:
                    await self.async_set_unique_id(base_url)
                    self._abort_if_unique_id_configured()

                    self._data = {
                        CONF_BASE_URL: base_url,
                        CONF_API_TOKEN: api_token,
                        "username": user.get("username") or user.get("alias") or "Kimai",
                    }
                    self._projects = projects

                    return await self.async_step_project()

            except KimaiAuthError:
                errors["base"] = "auth"
            except KimaiConnectionError:
                errors["base"] = "cannot_connect"
            except KimaiApiError:
                errors["base"] = "api_error"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error during Kimai setup")
                errors["base"] = "unknown"

        schema = vol.Schema(
            {
                vol.Required(CONF_BASE_URL): str,
                vol.Required(CONF_API_TOKEN): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_project(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Step 2: Choose Kimai project."""

        errors: dict[str, str] = {}

        project_options = {
            str(project["id"]): self._project_label(project)
            for project in self._projects
            if "id" in project
        }

        if user_input is not None:
            project_id = int(user_input[CONF_PROJECT_ID])
            self._data[CONF_PROJECT_ID] = project_id

            try:
                session = async_get_clientsession(self.hass)
                api = KimaiApi(
                    session,
                    self._data[CONF_BASE_URL],
                    self._data[CONF_API_TOKEN],
                )

                activities = await api.list_activities(project_id)

                if not activities:
                    errors["base"] = "no_activities"
                else:
                    self._activities = activities
                    return await self.async_step_activity()

            except KimaiAuthError:
                errors["base"] = "auth"
            except KimaiConnectionError:
                errors["base"] = "cannot_connect"
            except KimaiApiError:
                errors["base"] = "api_error"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected error loading Kimai activities")
                errors["base"] = "unknown"

        schema = vol.Schema(
            {
                vol.Required(CONF_PROJECT_ID): vol.In(project_options),
            }
        )

        return self.async_show_form(
            step_id="project",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_activity(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Step 3: Choose Kimai activity."""

        activity_options = {
            str(activity["id"]): self._activity_label(activity)
            for activity in self._activities
            if "id" in activity
        }

        if user_input is not None:
            self._data[CONF_ACTIVITY_ID] = int(user_input[CONF_ACTIVITY_ID])

            return self.async_create_entry(
                title=DEFAULT_NAME,
                data=self._data,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_ACTIVITY_ID): vol.In(activity_options),
            }
        )

        return self.async_show_form(
            step_id="activity",
            data_schema=schema,
            errors={},
        )

    @staticmethod
    def _project_label(project: dict[str, Any]) -> str:
        """Return project label."""
        name = project.get("name", f"Projekt {project.get('id')}")
        customer = project.get("customer")

        if isinstance(customer, dict):
            customer_name = customer.get("name")
            if customer_name:
                return f"{customer_name} / {name}"

        return str(name)

    @staticmethod
    def _activity_label(activity: dict[str, Any]) -> str:
        """Return activity label."""
        return str(activity.get("name", f"Tätigkeit {activity.get('id')}"))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Return options flow handler."""
        return KimaiHomeofficeOptionsFlowHandler(config_entry)


class KimaiHomeofficeOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Kimai Homeoffice options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}
        options = self._config_entry.options

        if user_input is not None:
            notify_service = _normalize_notify_service(
                user_input.get(CONF_NOTIFY_SERVICE)
            )
            user_input[CONF_NOTIFY_SERVICE] = notify_service

            if user_input.get(CONF_NOTIFY) and not notify_service:
                errors[CONF_NOTIFY_SERVICE] = "required"
            elif notify_service and not NOTIFY_SERVICE_PATTERN.fullmatch(
                notify_service
            ):
                errors[CONF_NOTIFY_SERVICE] = "invalid_notify_service"

            if user_input.get(CONF_BUTTON_ENABLED):
                trigger_type = user_input.get(
                    CONF_BUTTON_TRIGGER_TYPE,
                    DEFAULT_BUTTON_TRIGGER_TYPE,
                )
                if trigger_type == "mqtt":
                    if not user_input.get(CONF_BUTTON_MQTT_TOPIC):
                        errors[CONF_BUTTON_MQTT_TOPIC] = "required"
                elif not user_input.get(CONF_BUTTON_ENTITY):
                    errors[CONF_BUTTON_ENTITY] = "required"

            for field in (
                CONF_START_AFTER,
                CONF_START_BEFORE,
                CONF_SAFETY_STOP_TIME,
            ):
                if user_input.get(field) and not _is_hhmm(user_input[field]):
                    errors[field] = "invalid_time"

            if (
                not errors
                and user_input.get(CONF_START_AFTER)
                and user_input.get(CONF_START_BEFORE)
            ):
                start = _parse_hhmm(user_input[CONF_START_AFTER])
                end = _parse_hhmm(user_input[CONF_START_BEFORE])
                if start == end:
                    errors["base"] = "invalid_time_range"

            if not errors:
                return self.async_create_entry(title="", data=user_input)

        form_options = user_input if user_input is not None else options
        worker_sensor = form_options.get(CONF_WORKER_SENSOR) or None
        button_entity = form_options.get(CONF_BUTTON_ENTITY) or None
        daily_goal_entity = form_options.get(CONF_DAILY_GOAL_ENTITY) or None

        worker_sensor_field = vol.Optional(CONF_WORKER_SENSOR)
        if worker_sensor:
            worker_sensor_field = vol.Optional(
                CONF_WORKER_SENSOR,
                description={"suggested_value": worker_sensor},
            )

        button_entity_field = vol.Optional(CONF_BUTTON_ENTITY)
        if button_entity:
            button_entity_field = vol.Optional(
                CONF_BUTTON_ENTITY,
                description={"suggested_value": button_entity},
            )

        daily_goal_entity_field = vol.Optional(CONF_DAILY_GOAL_ENTITY)
        if daily_goal_entity:
            daily_goal_entity_field = vol.Optional(
                CONF_DAILY_GOAL_ENTITY,
                description={"suggested_value": daily_goal_entity},
            )

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_AUTO_START,
                    default=form_options.get(CONF_AUTO_START, DEFAULT_AUTO_START),
                ): bool,
                worker_sensor_field: selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["binary_sensor", "sensor"],
                    )
                ),
                vol.Optional(
                    CONF_START_AFTER,
                    default=form_options.get(CONF_START_AFTER, DEFAULT_START_AFTER),
                ): str,
                vol.Optional(
                    CONF_START_BEFORE,
                    default=form_options.get(CONF_START_BEFORE, DEFAULT_START_BEFORE),
                ): str,
                vol.Optional(
                    CONF_OFFLINE_STOP,
                    default=form_options.get(CONF_OFFLINE_STOP, DEFAULT_OFFLINE_STOP),
                ): bool,
                vol.Optional(
                    CONF_OFFLINE_MINUTES,
                    default=form_options.get(
                        CONF_OFFLINE_MINUTES,
                        DEFAULT_OFFLINE_MINUTES,
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440)),
                vol.Optional(
                    CONF_SAFETY_STOP,
                    default=form_options.get(CONF_SAFETY_STOP, DEFAULT_SAFETY_STOP),
                ): bool,
                vol.Optional(
                    CONF_SAFETY_STOP_TIME,
                    default=form_options.get(
                        CONF_SAFETY_STOP_TIME,
                        DEFAULT_SAFETY_STOP_TIME,
                    ),
                ): str,
                vol.Optional(
                    CONF_NOTIFY,
                    default=form_options.get(CONF_NOTIFY, DEFAULT_NOTIFY),
                ): bool,
                vol.Optional(
                    CONF_NOTIFY_SERVICE,
                    default=form_options.get(CONF_NOTIFY_SERVICE, ""),
                ): str,
                vol.Optional(
                    CONF_DAILY_GOAL_ENABLED,
                    default=form_options.get(
                        CONF_DAILY_GOAL_ENABLED,
                        DEFAULT_DAILY_GOAL_ENABLED,
                    ),
                ): bool,
                vol.Optional(
                    CONF_DAILY_GOAL_MODE,
                    default=form_options.get(
                        CONF_DAILY_GOAL_MODE,
                        DEFAULT_DAILY_GOAL_MODE,
                    ),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            "disabled",
                            "fixed",
                            "worked_days_only",
                            "manual_entity",
                            "weekly_plan",
                        ],
                        translation_key="daily_goal_mode",
                    )
                ),
                daily_goal_entity_field: selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["input_number", "number", "sensor"],
                    )
                ),
                vol.Optional(
                    CONF_DAILY_GOAL_HOURS,
                    default=form_options.get(
                        CONF_DAILY_GOAL_HOURS,
                        DEFAULT_DAILY_GOAL_HOURS,
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=24)),
                vol.Optional(
                    CONF_DAILY_GOAL_MINUTES,
                    default=form_options.get(
                        CONF_DAILY_GOAL_MINUTES,
                        DEFAULT_DAILY_GOAL_MINUTES,
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=59)),
                vol.Optional(
                    CONF_WEEKLY_GOAL_ENABLED,
                    default=form_options.get(
                        CONF_WEEKLY_GOAL_ENABLED,
                        DEFAULT_WEEKLY_GOAL_ENABLED,
                    ),
                ): bool,
                vol.Optional(
                    CONF_WEEKLY_GOAL_HOURS,
                    default=form_options.get(
                        CONF_WEEKLY_GOAL_HOURS,
                        DEFAULT_WEEKLY_GOAL_HOURS,
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=80)),
                vol.Optional(
                    CONF_WEEKLY_GOAL_MINUTES,
                    default=form_options.get(
                        CONF_WEEKLY_GOAL_MINUTES,
                        DEFAULT_WEEKLY_GOAL_MINUTES,
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=59)),
                vol.Optional(
                    CONF_ROUNDING_ENABLED,
                    default=form_options.get(
                        CONF_ROUNDING_ENABLED,
                        DEFAULT_ROUNDING_ENABLED,
                    ),
                ): bool,
                vol.Optional(
                    CONF_ROUNDING_MINUTES,
                    default=form_options.get(
                        CONF_ROUNDING_MINUTES,
                        DEFAULT_ROUNDING_MINUTES,
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
                vol.Optional(
                    CONF_ROUNDING_MODE,
                    default=form_options.get(
                        CONF_ROUNDING_MODE,
                        DEFAULT_ROUNDING_MODE,
                    ),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["ceil", "floor", "nearest"],
                        translation_key="rounding_mode",
                    )
                ),
                vol.Optional(
                    CONF_BUTTON_ENABLED,
                    default=form_options.get(
                        CONF_BUTTON_ENABLED,
                        DEFAULT_BUTTON_ENABLED,
                    ),
                ): bool,
                vol.Optional(
                    CONF_BUTTON_TRIGGER_TYPE,
                    default=form_options.get(
                        CONF_BUTTON_TRIGGER_TYPE,
                        DEFAULT_BUTTON_TRIGGER_TYPE,
                    ),
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=["entity", "mqtt"],
                    )
                ),
                button_entity_field: selector.EntitySelector(
                    selector.EntitySelectorConfig(
                        domain=["sensor", "binary_sensor", "input_button"],
                    )
                ),
                vol.Optional(
                    CONF_BUTTON_MQTT_TOPIC,
                    default=form_options.get(CONF_BUTTON_MQTT_TOPIC, ""),
                ): str,
                vol.Optional(
                    CONF_BUTTON_MQTT_JSON_KEY,
                    default=form_options.get(CONF_BUTTON_MQTT_JSON_KEY, ""),
                ): str,
                vol.Optional(
                    CONF_BUTTON_VALID_STATES,
                    default=form_options.get(
                        CONF_BUTTON_VALID_STATES,
                        DEFAULT_BUTTON_VALID_STATES,
                    ),
                ): str,
                vol.Optional(
                    CONF_BUTTON_COOLDOWN_SECONDS,
                    default=form_options.get(
                        CONF_BUTTON_COOLDOWN_SECONDS,
                        DEFAULT_BUTTON_COOLDOWN_SECONDS,
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=0, max=30)),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
