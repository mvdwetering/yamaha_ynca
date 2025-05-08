"""Options flow for Yamaha (YNCA) integration."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any

from homeassistant import config_entries
import homeassistant.helpers.config_validation as cv
import voluptuous as vol

import ynca

from .const import (
    CONF_HIDDEN_INPUTS,
    CONF_HIDDEN_SOUND_MODES,
    CONF_NUMBER_OF_SCENES,
    CONF_SELECTED_INPUTS,
    CONF_SELECTED_SOUND_MODES,
    CONF_SELECTED_SURROUND_DECODERS,
    DATA_MODELNAME,
    DATA_ZONES,
    MAX_NUMBER_OF_SCENES,
    NUMBER_OF_SCENES_AUTODETECT,
    TWOCHDECODER_STRINGS,
)
from .input_helpers import InputHelper

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigFlowResult

    from . import YamahaYncaConfigEntry

STEP_ID_INIT = "init"
STEP_ID_NO_CONNECTION = "no_connection"
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


def get_next_step_id(flow: OptionsFlowHandler, current_step: str) -> str:
    index = STEP_SEQUENCE.index(current_step)
    next_step = STEP_SEQUENCE[index + 1]

    while next_step in ZONE_STEPS:
        if next_step.upper() in flow.config_entry.data[DATA_ZONES]:
            return next_step
        index += 1
        next_step = STEP_SEQUENCE[index + 1]

    return next_step


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: YamahaYncaConfigEntry) -> None:
        self.options = deepcopy(dict(config_entry.options))

    async def do_next_step(self, current_step_id: str) -> ConfigFlowResult:
        next_step_id = get_next_step_id(self, current_step_id)
        return await getattr(self, f"async_step_{next_step_id}")()  # type: ignore[no-any-return]

    async def async_step_init(
        self, _user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Perform basic sanity checks before configuring options."""
        # The configentry in the optionsflow is _only_ a YamahaYncaConfigEntry when there is a connection
        # Otherwise it is a "plain" ConfigEntry, so without runtime_data
        # A normal isinstance check does not seem to work with type alias, to check for runtime_data attribute
        if getattr(self.config_entry, "runtime_data", None):
            self.api = self.config_entry.runtime_data.api
            return await self.async_step_general()

        return await self.async_step_no_connection()

    async def async_step_no_connection(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """No connection dialog."""
        if user_input is not None:
            # Strangely enough there is no title on the abort box
            # I guess because optionflows are not expected to be aborted
            # So exit with "success" instead through the done step and it will rewrite current settings
            # return self.async_abort(reason="no_connection")  # noqa: ERA001
            return await self.async_step_done()

        return self.async_show_form(step_id=STEP_ID_NO_CONNECTION)

    async def async_step_general(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """General device options."""
        modelinfo = ynca.YncaModelInfo.get(self.config_entry.data[DATA_MODELNAME])

        # Note that hidden modes are stored, but selected modes are shown in UI
        # It makes selecting easier for the user (if selected then it is used)
        # Storing hidden so that when adding support for new soundmodes/sources they will show up automatically
        # Not sure if it is the best way, but lets see feedback in the (expected rare) case this will happen.

        # List all sound modes for this model
        sound_modes = []
        for sound_mode in ynca.SoundPrg:
            if sound_mode is ynca.SoundPrg.UNKNOWN:
                continue
            if modelinfo and sound_mode not in modelinfo.soundprg:
                continue  # Skip soundmodes not supported on the model
            sound_modes.append(sound_mode.value)
        sound_modes.sort(key=str.lower)

        if user_input is not None:
            hidden_sound_modes = list(
                set(sound_modes) - set(user_input[CONF_SELECTED_SOUND_MODES])
            )
            self.options[CONF_HIDDEN_SOUND_MODES] = hidden_sound_modes

            if CONF_SELECTED_SURROUND_DECODERS in user_input:
                self.options[CONF_SELECTED_SURROUND_DECODERS] = user_input[
                    CONF_SELECTED_SURROUND_DECODERS
                ]

            return await self.do_next_step(STEP_ID_GENERAL)

        # List all hidden modes
        hidden_sound_modes = self.options.get(CONF_HIDDEN_SOUND_MODES, [])
        hidden_sound_modes = [
            stored_sound_mode
            for stored_sound_mode in hidden_sound_modes
            # Protect against supported soundmode list updates
            if stored_sound_mode in sound_modes
        ]

        selected_sound_modes = list(set(sound_modes) - set(hidden_sound_modes))

        schema = {}
        schema[
            vol.Required(
                CONF_SELECTED_SOUND_MODES,
                default=selected_sound_modes,
            )
        ] = cv.multi_select(sound_modes)

        # Select supported Surround Decoders
        # Technically twochdecoder could have different values per zone, but that seems unlikely
        # It "feels" better to have it as a receiver wide configuration
        if (zone := self.api.main) and zone.twochdecoder is not None:
            stored_selected_surround_decoders_ids = self.options.get(
                CONF_SELECTED_SURROUND_DECODERS, []
            )
            all_surround_decoders = dict(
                sorted(TWOCHDECODER_STRINGS.items(), key=lambda item: item[1].lower())
            )

            if not stored_selected_surround_decoders_ids:
                stored_selected_surround_decoders_ids = list(
                    all_surround_decoders.keys()
                )

            # Could technically use translation for this in Options flow, but only by using SelectorSelect
            # but the multiselect UI it creates is a hassle to use and since there are no translations yet
            # lets keep using cv.multiselect with hardcoded English translation
            schema[
                vol.Required(
                    CONF_SELECTED_SURROUND_DECODERS,
                    default=stored_selected_surround_decoders_ids,
                )
            ] = cv.multi_select(all_surround_decoders)

        return self.async_show_form(
            step_id=STEP_ID_GENERAL,
            data_schema=vol.Schema(schema),
            last_step=get_next_step_id(self, STEP_ID_GENERAL) == STEP_ID_DONE,
        )

    async def async_step_main(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self.async_zone_settings_screen(
            STEP_ID_MAIN, user_input=user_input
        )

    async def async_step_zone2(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self.async_zone_settings_screen(
            STEP_ID_ZONE2, user_input=user_input
        )

    async def async_step_zone3(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self.async_zone_settings_screen(
            STEP_ID_ZONE3, user_input=user_input
        )

    async def async_step_zone4(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return await self.async_zone_settings_screen(
            STEP_ID_ZONE4, user_input=user_input
        )

    async def async_zone_settings_screen(
        self, step_id: str, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        zone_id = step_id.upper()

        all_inputs = {}
        for input_, name in InputHelper.get_source_mapping(self.api).items():
            all_inputs[input_.value] = (
                f"{input_.value} ({name})"
                if input_.value.lower() != name.strip().lower()
                else name
            )
        all_inputs = dict(sorted(all_inputs.items(), key=lambda item: item[1].lower()))
        all_input_ids = list(all_inputs.keys())

        if user_input is not None:
            hidden_input_ids = list(
                set(all_input_ids) - set(user_input[CONF_SELECTED_INPUTS])
            )

            self.options.setdefault(zone_id, {})
            self.options[zone_id][CONF_HIDDEN_INPUTS] = hidden_input_ids
            self.options[zone_id][CONF_NUMBER_OF_SCENES] = user_input[
                CONF_NUMBER_OF_SCENES
            ]
            return await self.do_next_step(step_id)

        schema: dict[Any, Any] = {}

        # Select inputs for zone
        stored_hidden_input_ids = self.options.get(zone_id, {}).get(
            CONF_HIDDEN_INPUTS, []
        )
        selected_inputs = list(set(all_input_ids) - set(stored_hidden_input_ids))

        schema[
            vol.Required(
                CONF_SELECTED_INPUTS,
                default=selected_inputs,
            )
        ] = cv.multi_select(all_inputs)

        # Number of scenes for zone
        # Use a select so we can have nice distinct values presented with Autodetect and 0-12
        number_of_scenes_list = {NUMBER_OF_SCENES_AUTODETECT: "Auto detect"}
        for scene_id in range(MAX_NUMBER_OF_SCENES + 1):
            number_of_scenes_list[scene_id] = str(scene_id)

        schema[
            vol.Required(
                CONF_NUMBER_OF_SCENES,
                default=self.options.get(zone_id, {}).get(
                    CONF_NUMBER_OF_SCENES, NUMBER_OF_SCENES_AUTODETECT
                ),
            )
        ] = vol.In(number_of_scenes_list)

        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema(schema),
            last_step=get_next_step_id(self, step_id) == STEP_ID_DONE,
        )

    async def async_step_done(
        self, _user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_create_entry(
            title=self.config_entry.data[DATA_MODELNAME], data=self.options
        )
