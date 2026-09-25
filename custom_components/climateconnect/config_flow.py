"""Config flow for the ClimateConnect (Itho Daalderop) integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult

from .api import ClimateConnectAuthError, login
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class ClimateConnectConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the login step for ClimateConnect."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]

            try:
                creds = await self.hass.async_add_executor_job(login, email, password)
            except ClimateConnectAuthError:
                _LOGGER.warning("ClimateConnect login failed for %s", email)
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001 - surface anything unexpected as a generic error
                _LOGGER.exception("Unexpected error logging into ClimateConnect")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(email.lower())
                self._abort_if_unique_id_configured()

                user_name = creds.get("user", {}).get("name") or email
                return self.async_create_entry(
                    title=user_name,
                    data={CONF_EMAIL: email, CONF_PASSWORD: password},
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
