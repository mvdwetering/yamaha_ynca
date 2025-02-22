"""Config flow for Yamaha (YNCA) integration."""

from __future__ import annotations

from typing import Any, Dict
import re

import voluptuous as vol  # type: ignore
import ynca

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, SOURCE_RECONFIGURE
from homeassistant.core import HomeAssistant, callback

from .const import (
    CONF_HOST,
    CONF_PORT,
    CONF_SERIAL_URL,
    DATA_MODELNAME,
    DATA_ZONES,
    DOMAIN,
    LOGGER,
)
from .options_flow import OptionsFlowHandler

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


class YamahaYncaConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Yamaha (YNCA)."""

    # When updating also update the one used in `setup_integration` for tests
    VERSION = 7
    MINOR_VERSION = 6

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: Dict[str, Any] | None = None
    ) -> ConfigFlowResult:
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
    ) -> ConfigFlowResult:

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
            data = {
                CONF_SERIAL_URL: user_input[CONF_SERIAL_URL],
                DATA_MODELNAME: check_result.modelname,
                DATA_ZONES: check_result.zones,
            }

            if self.source == SOURCE_RECONFIGURE :
                reconfigure_entry = self._get_reconfigure_entry()
                self.hass.config_entries.async_update_entry(
                    reconfigure_entry, data=data
                )
                await self.hass.config_entries.async_reload(
                    reconfigure_entry.entry_id
                )
                return self.async_abort(reason="reconfigure_successful")

            return self.async_create_entry(title=check_result.modelname, data=data)

        return self.async_show_form(
            step_id=step_id,
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_serial(
        self, user_input: Dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is None:

            serial_url = None
            if self.source == SOURCE_RECONFIGURE :
                reconfigure_entry = self._get_reconfigure_entry()
                serial_url = reconfigure_entry.data.get(CONF_SERIAL_URL)

            return self.async_show_form(
                step_id=STEP_ID_SERIAL,
                data_schema=get_serial_url_schema(
                    {CONF_SERIAL_URL: serial_url}
                    if serial_url and not serial_url.startswith(
                        "socket://"
                    )
                    else {}
                ),
            )

        return await self.async_try_connect(
            STEP_ID_SERIAL, get_serial_url_schema(user_input), user_input
        )

    async def async_step_network(
        self, user_input: Dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is None:
            data = {}
            if self.source == SOURCE_RECONFIGURE :
                reconfigure_entry = self._get_reconfigure_entry()
                # Get HOST and PORT from socket://HOST:PORT
                if m := re.match(
                    r"socket://(?P<host>.+):(?P<port>\d+)",
                    reconfigure_entry.data[CONF_SERIAL_URL],
                ):
                    data[CONF_HOST] = m.group("host")
                    data[CONF_PORT] = int(m.group("port"))

            return self.async_show_form(
                step_id=STEP_ID_NETWORK, data_schema=get_network_schema(data)
            )

        connection_data = {
            CONF_SERIAL_URL: f"socket://{user_input[CONF_HOST]}:{user_input[CONF_PORT]}"
        }
        return await self.async_try_connect(
            STEP_ID_NETWORK, get_network_schema(user_input), connection_data
        )

    async def async_step_advanced(
        self, user_input: Dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is None:
            return self.async_show_form(
                step_id=STEP_ID_ADVANCED,
                data_schema=get_serial_url_schema(
                    {CONF_SERIAL_URL: self._get_reconfigure_entry().data.get(CONF_SERIAL_URL)}
                    if self.source == SOURCE_RECONFIGURE
                    else {}
                ),
            )

        return await self.async_try_connect(
            STEP_ID_ADVANCED, get_serial_url_schema(user_input), user_input
        )

    async def async_step_reconfigure(self, user_input=None):
        return await self.async_step_user()
