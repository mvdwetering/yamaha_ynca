"""Config flow for Yamaha (YNCA) integration."""
from __future__ import annotations

from typing import Any, Dict

import voluptuous as vol  # type: ignore

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult


from .const import (
    CONF_SERIAL_URL,
    CONF_HOST,
    CONF_PORT,
    DATA_MODELNAME,
    DATA_ZONES,
    DOMAIN,
    LOGGER,
)
from .options_flow import OptionsFlowHandler

import ynca


STEP_ID_SERIAL = "serial"
STEP_ID_NETWORK = "network"
STEP_ID_ADVANCED = "advanced"


def get_serial_url_schema(user_input):
    return vol.Schema(
        {
            vol.Required(
                CONF_SERIAL_URL, default=user_input.get(CONF_SERIAL_URL, vol.UNDEFINED)
            ): str
        }
    )


def get_network_schema(user_input):
    return vol.Schema(
        {
            vol.Required(
                CONF_HOST, default=user_input.get(CONF_HOST, vol.UNDEFINED)
            ): str,
            vol.Required(CONF_PORT, default=user_input.get(CONF_PORT, 50000)): int,
        }
    )


async def validate_input(
    hass: HomeAssistant, data: Dict[str, Any]
) -> ynca.YncaConnectionCheckResult:
    """
    Validate if the user input allows us to connect.
    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    def validate_connection(serial_url):
        return ynca.YncaApi(serial_url).connection_check()

    result = await hass.async_add_executor_job(
        validate_connection, data[CONF_SERIAL_URL]
    )

    return result


class YamahaYncaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Yamaha (YNCA)."""

    # When updating also update the one used in `setup_integration` for tests
    VERSION = 7
    MINOR_VERSION = 5

    reauth_entry: config_entries.ConfigEntry | None = None


    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: Dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        return self.async_show_menu(
            step_id="user",
            menu_options=[STEP_ID_SERIAL, STEP_ID_NETWORK, STEP_ID_ADVANCED],
        )

    async def async_try_connect(
        self,
        step_id: str,
        data_schema: vol.Schema,
        user_input: Dict[str, Any],
    ) -> FlowResult:

        errors = {}
        try:
            check_result = await validate_input(self.hass, user_input)
        except ynca.YncaConnectionError:
            errors["base"] = "connection_error"
        except ynca.YncaConnectionFailed:
            errors["base"] = f"connection_failed_{step_id}"
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Unhandled exception during connection.")
            errors["base"] = "unknown"
        else:
            data = {}
            data[CONF_SERIAL_URL] = user_input[CONF_SERIAL_URL]
            data[DATA_MODELNAME] = check_result.modelname
            data[DATA_ZONES] = check_result.zones

            if self.reauth_entry:
                self.hass.config_entries.async_update_entry(self.reauth_entry, data=data)
                await self.hass.config_entries.async_reload(self.reauth_entry.entry_id)
                return self.async_abort(reason="reauth_successful")            

            return self.async_create_entry(title=check_result.modelname, data=data)

        return self.async_show_form(
            step_id=step_id,
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_serial(
        self, user_input: Dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id=STEP_ID_SERIAL, data_schema=get_serial_url_schema({})
            )

        return await self.async_try_connect(
            STEP_ID_SERIAL, get_serial_url_schema(user_input), user_input
        )

    async def async_step_network(
        self, user_input: Dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id=STEP_ID_NETWORK, data_schema=get_network_schema({})
            )

        connection_data = {
            CONF_SERIAL_URL: f"socket://{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
        }
        return await self.async_try_connect(
            STEP_ID_NETWORK, get_network_schema(user_input), connection_data
        )

    async def async_step_advanced(
        self, user_input: Dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id=STEP_ID_ADVANCED, data_schema=get_serial_url_schema({})
            )

        return await self.async_try_connect(
            STEP_ID_ADVANCED, get_serial_url_schema(user_input), user_input
        )

    async def async_step_reauth(self, user_input=None):
        """Reauth is (ab)used to allow setting up connection settings again through the existing flow."""
        self.reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        return await self.async_step_user()
