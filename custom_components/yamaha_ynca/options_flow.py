"""Config flow for Yamaha (YNCA) integration."""
from __future__ import annotations

from typing import Any, Dict

import voluptuous as vol  # type: ignore

from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
import homeassistant.helpers.config_validation as cv

from custom_components.yamaha_ynca.input_helpers import InputHelper

from .const import (
    CONF_HIDDEN_INPUTS,
    CONF_HIDDEN_SOUND_MODES,
    DATA_MODELNAME,
    DATA_ZONES,
    DOMAIN,
    LOGGER,
)

import ynca


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Basic sanity checks before configuring options."""

        self.api = None

        if self.hass.data.get(DOMAIN, None) and (
            domain_entry_data := (
                self.hass.data[DOMAIN].get(self.config_entry.entry_id, None)
            )
        ):
            self.api = domain_entry_data.api
            self.options = dict(self.config_entry.options)
            return await self.async_step_general()

        return self.async_abort(reason="connection_required")

    async def async_step_general(self, user_input=None):
        """Manage general device options"""

        print("async_step_general")

        if user_input is not None:
            self.options[CONF_HIDDEN_SOUND_MODES] = user_input[CONF_HIDDEN_SOUND_MODES]
            if "MAIN" in self.config_entry.data[DATA_ZONES]:
                return await self.async_step_main()
            return await self.async_step_done(user_input)

        schema = {}
        modelinfo = ynca.YncaModelInfo.get(self.config_entry.data[DATA_MODELNAME])

        # Hiding sound modes
        sound_modes = []
        for sound_mode in ynca.SoundPrg:
            if sound_mode is ynca.SoundPrg.UNKNOWN:
                continue
            if modelinfo and not sound_mode in modelinfo.soundprg:
                continue  # Skip soundmodes not supported on the model
            sound_modes.append(sound_mode.value)
        sound_modes.sort(key=str.lower)

        # Protect against supported soundmode list updates
        stored_sound_modes = self.options.get(CONF_HIDDEN_SOUND_MODES, [])
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

        return self.async_show_form(
            step_id="general",
            data_schema=vol.Schema(schema),
            last_step="MAIN" not in self.config_entry.data[DATA_ZONES],
        )

    async def async_step_main(self, user_input=None):
        print("async_step_main")
        if user_input is not None:
            if "ZONE2" in self.config_entry.data[DATA_ZONES]:
                self.options["MAIN"] = user_input
                return await self.async_step_zone2()
            return await self.async_step_done()

        return await self.async_zone_settings_screen(
            "MAIN",
            "ZONE2" not in self.config_entry.data[DATA_ZONES],
            user_input=user_input,
        )

    async def async_step_zone2(self, user_input=None):
        print("async_step_zone2")
        if user_input is not None:
            if "ZONE3" in self.config_entry.data[DATA_ZONES]:
                self.options["ZONE2"] = user_input
                return await self.async_step_zone3()
            return await self.async_step_done()

        return await self.async_zone_settings_screen(
            "ZONE2",
            "ZONE3" not in self.config_entry.data[DATA_ZONES],
            user_input=user_input,
        )

    async def async_step_zone3(self, user_input=None):
        print("async_step_zone3")
        if user_input is not None:
            if "ZONE4" in self.config_entry.data[DATA_ZONES]:
                self.options["ZONE3"] = user_input
                return await self.async_step_zone4()
            return await self.async_step_done()

        return await self.async_zone_settings_screen(
            "ZONE3",
            "ZONE4" not in self.config_entry.data[DATA_ZONES],
            user_input=user_input,
        )

    async def async_step_zone4(self, user_input=None):
        print("async_step_zone4")
        if user_input is not None:
            self.options["ZONE4"] = user_input
            return await self.async_step_done()

        return await self.async_zone_settings_screen(
            "ZONE4", True, user_input=user_input
        )

    async def async_zone_settings_screen(self, zone_id, last_step, user_input=None):

        schema = {}

        # Hiding inputs for zone
        inputs = {}
        for input, name in InputHelper.get_source_mapping(self.api).items():
            inputs[input.value] = (
                f"{input.value} ({name})"
                if input.value.lower() != name.strip().lower()
                else name
            )

        # Sorts the inputs (3.7+ dicts maintain insertion order)
        inputs = dict(sorted(inputs.items(), key=lambda item: item[1]))

        schema[
            vol.Required(
                CONF_HIDDEN_INPUTS,
                default=self.config_entry.options.get(zone_id, {}).get(
                    CONF_HIDDEN_INPUTS, []
                ),
            )
        ] = cv.multi_select(inputs)

        print(zone_id, self.cur_step, schema)

        return self.async_show_form(
            step_id=zone_id.lower(), data_schema=vol.Schema(schema), last_step=last_step
        )

    async def async_step_done(self, user_input=None):
        return self.async_create_entry(
            title=self.config_entry.data[DATA_MODELNAME], data=self.options
        )
