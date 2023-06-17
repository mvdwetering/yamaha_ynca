"""Test the Yamaha (YNCA) config flow."""
from __future__ import annotations

from unittest.mock import create_autospec

import ynca
from flaky import flaky

import custom_components.yamaha_ynca as yamaha_ynca
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from tests.conftest import setup_integration


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
    integration.entry.options = dict(integration.entry.options)

    result = await hass.config_entries.options.async_init(integration.entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "general"
    assert result["last_step"] is False

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={yamaha_ynca.const.CONF_HIDDEN_SOUND_MODES: []}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "main"
    assert result["last_step"] is False

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            yamaha_ynca.const.CONF_HIDDEN_INPUTS: [],
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: yamaha_ynca.const.NUMBER_OF_SCENES_AUTODETECT,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "zone2"
    assert result["last_step"] is False

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            yamaha_ynca.const.CONF_HIDDEN_INPUTS: [],
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: yamaha_ynca.const.NUMBER_OF_SCENES_AUTODETECT,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "zone3"
    assert result["last_step"] is False

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            yamaha_ynca.const.CONF_HIDDEN_INPUTS: [],
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: yamaha_ynca.const.NUMBER_OF_SCENES_AUTODETECT,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "zone4"
    assert result["last_step"] is True

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            yamaha_ynca.const.CONF_HIDDEN_INPUTS: [],
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: yamaha_ynca.const.NUMBER_OF_SCENES_AUTODETECT,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        yamaha_ynca.const.CONF_HIDDEN_SOUND_MODES: [],
        "MAIN": {
            yamaha_ynca.const.CONF_HIDDEN_INPUTS: [],
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: yamaha_ynca.const.NUMBER_OF_SCENES_AUTODETECT,
        },
        "ZONE2": {
            yamaha_ynca.const.CONF_HIDDEN_INPUTS: [],
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: yamaha_ynca.const.NUMBER_OF_SCENES_AUTODETECT,
        },
        "ZONE3": {
            yamaha_ynca.const.CONF_HIDDEN_INPUTS: [],
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: yamaha_ynca.const.NUMBER_OF_SCENES_AUTODETECT,
        },
        "ZONE4": {
            yamaha_ynca.const.CONF_HIDDEN_INPUTS: [],
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: yamaha_ynca.const.NUMBER_OF_SCENES_AUTODETECT,
        },
    }


async def test_options_flow_no_connection(hass: HomeAssistant, mock_ynca) -> None:
    """Test optionsflow when there is no connection"""

    integration = await setup_integration(hass, mock_ynca)
    hass.data[yamaha_ynca.DOMAIN] = {}  # Pretend connection failed

    result = await hass.config_entries.options.async_init(integration.entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "no_connection"

    # Press Submit
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={},
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "marked_for_reconfiguring"

# Not sure why it became flaky, just disable it for now :(
# @flaky(max_runs=5)
# async def test_options_flow_soundmodes(hass: HomeAssistant, mock_ynca) -> None:

#     # Set a modelname that is in the modelinfo, but does not support all SoundPrg values
#     mock_ynca.sys.modelname = "RX-A810"

#     integration = await setup_integration(hass, mock_ynca)

#     options = dict(integration.entry.options)
#     options[yamaha_ynca.const.CONF_HIDDEN_SOUND_MODES] = [
#         "Obsolete",  # Obsolete values should not break the schema
#     ]
#     integration.entry.options = options

#     result = await hass.config_entries.options.async_init(integration.entry.entry_id)

#     assert result["type"] == FlowResultType.FORM
#     assert result["step_id"] == "general"

#     result = await hass.config_entries.options.async_configure(
#         result["flow_id"],
#         user_input={
#             yamaha_ynca.const.CONF_HIDDEN_SOUND_MODES: [
#                 "Hall in Vienna",
#             ],
#         },
#     )

#     assert result["type"] == "create_entry"
#     assert result["data"] == {
#         yamaha_ynca.const.CONF_HIDDEN_SOUND_MODES: ["Hall in Vienna"],
#     }


async def test_options_flow_zone_inputs(
    hass: HomeAssistant, mock_ynca, mock_zone_main
) -> None:

    mock_ynca.main = mock_zone_main
    mock_ynca.sys.inpnamehdmi4 = "_INPNAMEHDMI4_"
    mock_ynca.netradio = create_autospec(ynca.subunits.netradio.NetRadio)

    integration = await setup_integration(hass, mock_ynca)
    options = dict(integration.entry.options)
    options["MAIN"] = {"hidden_inputs": ["AV5"]}
    integration.entry.options = options

    result = await hass.config_entries.options.async_init(integration.entry.entry_id)
    assert result["step_id"] == "general"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={yamaha_ynca.const.CONF_HIDDEN_SOUND_MODES: []},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "main"
    assert result["last_step"] is True

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            yamaha_ynca.const.CONF_HIDDEN_INPUTS: ["HDMI4"],
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: yamaha_ynca.const.NUMBER_OF_SCENES_AUTODETECT,
        },
    )

    assert result["type"] == "create_entry"
    assert result["data"] == {
        yamaha_ynca.const.CONF_HIDDEN_SOUND_MODES: [],
        "MAIN": {
            yamaha_ynca.const.CONF_HIDDEN_INPUTS: ["HDMI4"],
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
    integration.entry.options = options

    result = await hass.config_entries.options.async_init(integration.entry.entry_id)
    assert result["step_id"] == "general"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={yamaha_ynca.const.CONF_HIDDEN_SOUND_MODES: []},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "main"
    assert result["last_step"] is True

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            yamaha_ynca.const.CONF_HIDDEN_INPUTS: [],
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: 8,
        },
    )

    assert result["type"] == "create_entry"
    assert result["data"] == {
        yamaha_ynca.const.CONF_HIDDEN_SOUND_MODES: [],
        "MAIN": {
            yamaha_ynca.const.CONF_HIDDEN_INPUTS: [],
            yamaha_ynca.const.CONF_NUMBER_OF_SCENES: 8,
        },
    }
