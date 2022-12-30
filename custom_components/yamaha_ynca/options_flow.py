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

STEP_ID_INIT = "init"
STEP_ID_GENERAL = "general"
STEP_ID_MAIN = "main"
STEP_ID_ZONE2 = "zone2"
STEP_ID_ZONE3 = "zone3"
STEP_ID_ZONE4 = "zone4"
STEP_ID_DONE = "done"

STEP_SEQUENCE = [
    STEP_ID_INIT,
    STEP_ID_GENERAL,
    STEP_ID_MAIN,
    STEP_ID_ZONE2,
    STEP_ID_ZONE3,
    STEP_ID_ZONE4,
    STEP_ID_DONE,
]

ZONE_STEPS = [
    STEP_ID_MAIN,
    STEP_ID_ZONE2,
    STEP_ID_ZONE3,
    STEP_ID_ZONE4,
]


def get_next_step_id(flow: config_entries.OptionsFlowHandler, current_step: str) -> str:
    index = STEP_SEQUENCE.index(current_step)
    next_step = STEP_SEQUENCE[index + 1]

    while next_step in ZONE_STEPS:
        if next_step.upper() in flow.config_entry.data[DATA_ZONES]:
            return next_step
        index += 1
        next_step = STEP_SEQUENCE[index + 1]

    return next_step


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Basic sanity checks before configuring options."""

        if (
            DOMAIN in self.hass.data
            and self.config_entry.entry_id in self.hass.data[DOMAIN]
        ):
            self.api: ynca.YncaApi = self.hass.data[DOMAIN][
                self.config_entry.entry_id
            ].api
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
            step_id=STEP_ID_GENERAL,
            data_schema=vol.Schema(schema),
            last_step=get_next_step_id(self, STEP_ID_GENERAL) == STEP_ID_DONE,
        )

    async def async_step_main(self, user_input=None):
        print("async_step_main")
        return await self.async_zone_settings_screen(
            STEP_ID_MAIN, user_input=user_input
        )

    async def async_step_zone2(self, user_input=None):
        print("async_step_zone2")
        return await self.async_zone_settings_screen(
            STEP_ID_ZONE2, user_input=user_input
        )

    async def async_step_zone3(self, user_input=None):
        print("async_step_zone3")
        return await self.async_zone_settings_screen(
            STEP_ID_ZONE3, user_input=user_input
        )

    async def async_step_zone4(self, user_input=None):
        return await self.async_zone_settings_screen(
            STEP_ID_ZONE4, user_input=user_input
        )

    async def async_zone_settings_screen(self, step_id, user_input=None):
        print(step_id)

        zone_id = step_id.upper()

        if user_input is not None:
            self.options[zone_id] = user_input
            next_step_id = get_next_step_id(self, step_id)
            return await getattr(self, f"async_step_{next_step_id}")()

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

        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(schema),
            last_step=get_next_step_id(self, step_id) == STEP_ID_DONE,
        )

    async def async_step_done(self, user_input=None):
        return self.async_create_entry(
            title=self.config_entry.data[DATA_MODELNAME], data=self.options
        )
