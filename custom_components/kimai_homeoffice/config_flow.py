"""Config flow for Kimai Homeoffice."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ACTIVITY_ID,
    CONF_API_TOKEN,
    CONF_BASE_URL,
    CONF_PROJECT_ID,
    DEFAULT_NAME,
    DOMAIN,
)
from .kimai_api import KimaiApi, KimaiApiError, KimaiAuthError, KimaiConnectionError

_LOGGER = logging.getLogger(__name__)


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
                vol.Required(CONF_BASE_URL, default="http://192.168.178.172"): str,
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