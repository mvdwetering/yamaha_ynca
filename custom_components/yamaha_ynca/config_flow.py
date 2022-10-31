"""Config flow for Yamaha (YNCA) integration."""
from __future__ import annotations

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
    CONF_HIDDEN_SOUND_MODES,
    CONF_SERIAL_URL,
    CONF_HOST,
    CONF_PORT,
    DOMAIN,
    ZONE_SUBUNIT_IDS,
    LOGGER,
)
from .helpers import DomainEntryData

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


async def validate_input(hass: HomeAssistant, data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

    def validate_connection(serial_url):
        return ynca.Ynca(serial_url).connection_check()

    modelname = await hass.async_add_executor_job(
        validate_connection, data[CONF_SERIAL_URL]
    )

    # Return info that you want to store in the config entry.
    return {"title": modelname}


class YamahaYncaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Yamaha (YNCA)."""

    VERSION = 5

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
            info = await validate_input(self.hass, user_input)
        except ynca.YncaConnectionError:
            errors["base"] = "connection_error"
        except ynca.YncaConnectionFailed:
            errors["base"] = f"connection_failed_{step_id}"
        except Exception:  # pylint: disable=broad-except
            LOGGER.exception("Unhandled exception during connection.")
            errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

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


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = {}

        domain_entry_data: DomainEntryData = self.hass.data[DOMAIN].get(
            self.config_entry.entry_id, None
        )
        api = domain_entry_data.api
        modelinfo = ynca.get_modelinfo(api.SYS.modelname)

        # Hiding sound modes
        sound_modes = []
        for sound_mode in ynca.SoundPrg:
            if modelinfo and not sound_mode in modelinfo.soundprg:
                continue  # Skip soundmodes not supported on the model
            sound_modes.append(sound_mode.value)
        sound_modes.sort(key=str.lower)

        # Protect against supported soundmode list updates
        stored_sound_modes = self.config_entry.options.get(CONF_HIDDEN_SOUND_MODES, [])
        stored_sound_modes = [
            stored_sound_mode
            for stored_sound_mode in stored_sound_modes
            if stored_sound_mode in sound_modes
        ]

        schema[
            vol.Required(
                CONF_HIDDEN_SOUND_MODES,
                default=stored_sound_modes,
            )
        ] = cv.multi_select(sound_modes)

        # Hiding inputs per zone
        inputs = {}
        for inputinfo in ynca.get_inputinfo_list(api):
            inputs[inputinfo.input] = (
                f"{inputinfo.input} ({inputinfo.name})"
                if inputinfo.input != inputinfo.name
                else inputinfo.name
            )
        # Sorts the inputs (3.7+ dicts maintain insertion order)
        inputs = dict(sorted(inputs.items(), key=lambda tup: tup[0]))

        for zone_id in ZONE_SUBUNIT_IDS:
            if getattr(api, zone_id, None):
                schema[
                    vol.Required(
                        CONF_HIDDEN_INPUTS_FOR_ZONE(zone_id),
                        default=self.config_entry.options.get(
                            CONF_HIDDEN_INPUTS_FOR_ZONE(zone_id), []
                        ),
                    )
                ] = cv.multi_select(inputs)

        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema))
