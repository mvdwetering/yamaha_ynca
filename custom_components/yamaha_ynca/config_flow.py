"""Config flow for Yamaha (YNCA) integration."""
from __future__ import annotations

import logging
from typing import Any, Dict

import voluptuous as vol  # type: ignore

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import (
    CONF_HIDDEN_INPUTS_FOR_ZONE,
    CONF_SERIAL_URL,
    DOMAIN,
    ZONE_SUBUNIT_IDS,
)
from .helpers import serial_url_from_user_input

import ynca

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_SERIAL_URL): str})


async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    def validate_connection(serial_url):
        try:
            return ynca.Ynca(serial_url).connection_check()
        except ynca.YncaConnectionError:
            return None

    modelname = await hass.async_add_executor_job(
        validate_connection, serial_url_from_user_input(data[CONF_SERIAL_URL])
    )

    if not modelname:
        raise CannotConnect

    # Return info that you want to store in the config entry.
    return {"title": modelname}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Yamaha (YNCA)."""

    VERSION = 3

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: Dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Create a list of inputs on the Receiver that the user can select
        ynca_receiver = self.hass.data[DOMAIN].get(self.config_entry.entry_id, None)

        inputs = {}
        for id, name in ynca.get_all_zone_inputs(ynca_receiver).items():
            inputs[id] = f"{id} ({name})" if id != name else name

        # Sorts the inputs (3.7+ dicts maintain insertion order)
        inputs = dict(sorted(inputs.items(), key=lambda tup: tup[0]))

        # Build schema based on available zones
        schema = {}
        for zone_id in ZONE_SUBUNIT_IDS:
            if getattr(ynca_receiver, zone_id, None):
                schema[
                    vol.Required(
                        CONF_HIDDEN_INPUTS_FOR_ZONE(zone_id),
                        default=self.config_entry.options.get(
                            CONF_HIDDEN_INPUTS_FOR_ZONE(zone_id), []
                        ),
                    )
                ] = cv.multi_select(inputs)

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))
