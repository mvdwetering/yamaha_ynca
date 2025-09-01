"""Test the Yamaha (YNCA) config flow."""

from __future__ import annotations

from unittest.mock import create_autospec

from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components import yamaha_ynca
from tests.conftest import setup_integration
import ynca

ALL_SOUND_MODES = [
    soundprg.value
    for soundprg in [
        ynca.SoundPrg.HALL_IN_MUNICH,
        ynca.SoundPrg.HALL_IN_VIENNA,
        ynca.SoundPrg.CHAMBER,
        ynca.SoundPrg.CELLAR_CLUB,
        ynca.SoundPrg.THE_ROXY_THEATRE,
        ynca.SoundPrg.THE_BOTTOM_LINE,
        ynca.SoundPrg.SPORTS,
        ynca.SoundPrg.ACTION_GAME,
        ynca.SoundPrg.ROLEPLAYING_GAME,
        ynca.SoundPrg.MUSIC_VIDEO,
        ynca.SoundPrg.STANDARD,
        ynca.SoundPrg.SPECTACLE,
        ynca.SoundPrg.SCI_FI,
        ynca.SoundPrg.ADVENTURE,
        ynca.SoundPrg.DRAMA,
        ynca.SoundPrg.MONO_MOVIE,
        ynca.SoundPrg.TWO_CH_STEREO,
        ynca.SoundPrg.SURROUND_DECODER,
        ynca.SoundPrg.HALL_IN_AMSTERDAM,
        ynca.SoundPrg.CHURCH_IN_FREIBURG,
        ynca.SoundPrg.CHURCH_IN_ROYAUMONT,
        ynca.SoundPrg.VILLAGE_VANGUARD,
        ynca.SoundPrg.WAREHOUSE_LOFT,
        ynca.SoundPrg.RECITAL_OPERA,
        ynca.SoundPrg.FIVE_CH_STEREO,
        ynca.SoundPrg.SEVEN_CH_STEREO,
        ynca.SoundPrg.NINE_CH_STEREO,
        ynca.SoundPrg.ALL_CH_STEREO,
        ynca.SoundPrg.ENHANCED,
    ]
]

ALL_INPUTS = [
    "AUDIO",
    "AUDIO1",
    "AUDIO2",
    "AUDIO3",
    "AUDIO4",
    "AUDIO5",
    "AV1",
    "AV2",
    "AV3",
    "AV4",
    "AV5",
    "AV6",
    "AV7",
    "DOCK",
    "HDMI1",
    "HDMI2",
    "HDMI3",
    "HDMI4",
    "HDMI5",
    "HDMI6",
    "HDMI7",
    "MULTI CH",
    "OPTICAL1",
    "OPTICAL2",
    "PHONO",
    "TV",
    "USB",
    "V-AUX",
]


async def test_options_flow_navigate_all_screens(
    hass: HomeAssistant,
    mock_ynca,
    mock_zone_main,
    mock_zone_zone2,
    mock_zone_zone3,
    mock_zone_zone4,
) -> None:
    mock_ynca.main = mock_zone_main
    mock_ynca.zone2 = mock_zone_zone2
    mock_ynca.zone3 = mock_zone_zone3
    mock_ynca.zone4 = mock_zone_zone4

    integration = await setup_integration(hass, mock_ynca)

    result = await hass.config_entries.options.async_init(integration.entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "general"
    assert result["last_step"] is False

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={yamaha_ynca.const.CONF_SELECTED_SOUND_MODES: ALL_SOUND_MODES},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "main"
    assert result["last_step"] is False

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            yamaha_ynca.const.CONF_SELECTED_INPUTS: ALL_INPUTS,
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: yamaha_ynca.const.NUMBER_OF_SCENES_AUTODETECT,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "zone2"
    assert result["last_step"] is False

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            yamaha_ynca.const.CONF_SELECTED_INPUTS: ALL_INPUTS,
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: yamaha_ynca.const.NUMBER_OF_SCENES_AUTODETECT,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "zone3"
    assert result["last_step"] is False

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            yamaha_ynca.const.CONF_SELECTED_INPUTS: ALL_INPUTS,
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: yamaha_ynca.const.NUMBER_OF_SCENES_AUTODETECT,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "zone4"
    assert result["last_step"] is True

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            yamaha_ynca.const.CONF_SELECTED_INPUTS: ALL_INPUTS,
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: yamaha_ynca.const.NUMBER_OF_SCENES_AUTODETECT,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        yamaha_ynca.const.CONF_SELECTED_SOUND_MODES: ALL_SOUND_MODES,
        "MAIN": {
            yamaha_ynca.const.CONF_SELECTED_INPUTS: ALL_INPUTS,
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: yamaha_ynca.const.NUMBER_OF_SCENES_AUTODETECT,
        },
        "ZONE2": {
            yamaha_ynca.const.CONF_SELECTED_INPUTS: ALL_INPUTS,
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: yamaha_ynca.const.NUMBER_OF_SCENES_AUTODETECT,
        },
        "ZONE3": {
            yamaha_ynca.const.CONF_SELECTED_INPUTS: ALL_INPUTS,
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: yamaha_ynca.const.NUMBER_OF_SCENES_AUTODETECT,
        },
        "ZONE4": {
            yamaha_ynca.const.CONF_SELECTED_INPUTS: ALL_INPUTS,
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: yamaha_ynca.const.NUMBER_OF_SCENES_AUTODETECT,
        },
    }


async def test_options_flow_no_connection(hass: HomeAssistant, mock_ynca) -> None:
    """Test optionsflow when there is no connection"""
    integration = await setup_integration(hass, mock_ynca)
    integration.entry.runtime_data = None  # Pretend connection failed

    result = await hass.config_entries.options.async_init(integration.entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "no_connection"

    # Press Submit
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_options_flow_soundmodes(hass: HomeAssistant, mock_ynca) -> None:
    # Set a modelname that is in the modelinfo that does not support all SoundPrg values
    mock_ynca.sys.modelname = "RX-A810"

    integration = await setup_integration(hass, mock_ynca)

    options = dict(integration.entry.options)
    options[yamaha_ynca.const.CONF_SELECTED_SOUND_MODES] = [
        "Obsolete",  # Obsolete values should not break the schema
    ]
    hass.config_entries.async_update_entry(integration.entry, options=options)

    result = await hass.config_entries.options.async_init(integration.entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "general"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            yamaha_ynca.const.CONF_SELECTED_SOUND_MODES: [
                ynca.SoundPrg.HALL_IN_VIENNA,
            ],
        },
    )

    assert result["type"] == "create_entry"
    assert result["data"] == {
        yamaha_ynca.const.CONF_SELECTED_SOUND_MODES: ["Hall in Vienna"]
    }

    # Make sure HA finishes creating entry completely
    # or it will result in errors when tearing down the test
    await hass.async_block_till_done()


async def test_options_flow_surrounddecoders(
    hass: HomeAssistant, mock_ynca, mock_zone_main
) -> None:
    mock_zone_main.twochdecoder = ynca.TwoChDecoder.Auro3d
    mock_ynca.main = mock_zone_main
    integration = await setup_integration(hass, mock_ynca)

    options = dict(integration.entry.options)
    # Do _not_ set options[yamaha_ynca.const.CONF_SELECTED_SURROUND_DECODERS] to test handling of absent options
    hass.config_entries.async_update_entry(integration.entry, options=options)

    result = await hass.config_entries.options.async_init(integration.entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "general"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            yamaha_ynca.const.CONF_SELECTED_SOUND_MODES: [],
            yamaha_ynca.const.CONF_SELECTED_SURROUND_DECODERS: [
                "dolby_plii_movie",
                "auto",
                "dts_neural_x",
            ],
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "main"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            yamaha_ynca.const.CONF_SELECTED_INPUTS: [],
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: yamaha_ynca.const.NUMBER_OF_SCENES_AUTODETECT,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][yamaha_ynca.const.CONF_SELECTED_SURROUND_DECODERS] == [
        "dolby_plii_movie",
        "auto",
        "dts_neural_x",
    ]

    # Make sure HA finishes creating entry completely
    # or it will result in errors when tearing down the test
    await hass.async_block_till_done()


async def test_options_flow_zone_inputs(
    hass: HomeAssistant, mock_ynca, mock_zone_main
) -> None:
    mock_ynca.main = mock_zone_main
    mock_ynca.sys.inpnamehdmi4 = "_INPNAMEHDMI4_"
    mock_ynca.netradio = create_autospec(ynca.subunits.netradio.NetRadio)

    integration = await setup_integration(hass, mock_ynca)
    options = dict(integration.entry.options)
    options["MAIN"] = {"selected_inputs": ["AV5"]}
    hass.config_entries.async_update_entry(integration.entry, options=options)

    result = await hass.config_entries.options.async_init(integration.entry.entry_id)
    assert result["step_id"] == "general"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={yamaha_ynca.const.CONF_SELECTED_SOUND_MODES: ALL_SOUND_MODES},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "main"
    assert result["last_step"] is True

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            yamaha_ynca.const.CONF_SELECTED_INPUTS: ["NET RADIO"],
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: yamaha_ynca.const.NUMBER_OF_SCENES_AUTODETECT,
        },
    )

    assert result["type"] == "create_entry"
    assert result["data"] == {
        yamaha_ynca.const.CONF_SELECTED_SOUND_MODES: ALL_SOUND_MODES,
        "MAIN": {
            yamaha_ynca.const.CONF_SELECTED_INPUTS: ["NET RADIO"],
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: yamaha_ynca.const.NUMBER_OF_SCENES_AUTODETECT,
        },
    }


async def test_options_flow_configure_nof_scenes(
    hass: HomeAssistant, mock_ynca, mock_zone_main
) -> None:
    mock_ynca.main = mock_zone_main

    integration = await setup_integration(hass, mock_ynca)
    options = dict(integration.entry.options)
    options["MAIN"] = {"number_of_scenes": 5}
    hass.config_entries.async_update_entry(integration.entry, options=options)

    result = await hass.config_entries.options.async_init(integration.entry.entry_id)
    assert result["step_id"] == "general"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={yamaha_ynca.const.CONF_SELECTED_SOUND_MODES: ALL_SOUND_MODES},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "main"
    assert result["last_step"] is True

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            yamaha_ynca.const.CONF_SELECTED_INPUTS: ALL_INPUTS,
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: 8,
        },
    )

    assert result["type"] == "create_entry"
    assert result["data"] == {
        yamaha_ynca.const.CONF_SELECTED_SOUND_MODES: ALL_SOUND_MODES,
        "MAIN": {
            yamaha_ynca.const.CONF_SELECTED_INPUTS: ALL_INPUTS,
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: 8,
        },
    }
