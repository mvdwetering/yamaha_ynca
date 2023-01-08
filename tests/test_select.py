from __future__ import annotations

from unittest.mock import ANY, Mock, call, patch

import pytest
import ynca

import custom_components.yamaha_ynca as yamaha_ynca
from custom_components.yamaha_ynca.select import (
    PowerOnVolumeModeEntityDescription,
    YamahaYncaSelect,
    YamahaYncaSelectPowerOnVolume,
    YncaSelectEntityDescription,
    async_setup_entry,
    build_enum_options_list,
)
from homeassistant.helpers.entity import EntityCategory

from tests.conftest import setup_integration


TEST_ENTITY_DESCRIPTION = YncaSelectEntityDescription(  # type: ignore
    key="hdmiout",
    entity_category=EntityCategory.CONFIG,
    enum=ynca.HdmiOut,
    icon="mdi:hdmi-port",
    name="HDMI Out",
    options=build_enum_options_list(ynca.HdmiOut),
)


@patch("custom_components.yamaha_ynca.select.YamahaYncaSelect", autospec=True)
@patch(
    "custom_components.yamaha_ynca.select.YamahaYncaSelectPowerOnVolume", autospec=True
)
async def test_async_setup_entry(
    yamahayncaselectpoweronvolume_mock,
    yamahayncaselect_mock,
    hass,
    mock_ynca,
    mock_zone_main,
):
    mock_ynca.main = mock_zone_main
    mock_ynca.main.hdmiout = ynca.HdmiOut.OFF
    mock_ynca.main.sleep = ynca.Sleep.THIRTY_MIN
    mock_ynca.main.initvollvl = ynca.InitVolLvl.MUTE

    integration = await setup_integration(hass, mock_ynca)
    add_entities_mock = Mock()

    await async_setup_entry(hass, integration.entry, add_entities_mock)

    yamahayncaselect_mock.assert_has_calls(
        [
            # TODO: improve checks to see if expected entity descriptions are used
            #       but just want to check for key, not the whole (internal) configuration
            call("entry_id", mock_ynca.main, ANY),
            call("entry_id", mock_ynca.main, ANY),
        ]
    )
    yamahayncaselectpoweronvolume_mock.assert_has_calls(
        [
            # TODO: improve checks to see if expected entity descriptions are used
            #       but just want to check for key, not the whole (internal) configuration
            call("entry_id", mock_ynca.main, ANY),
        ]
    )

    add_entities_mock.assert_called_once()
    entities = add_entities_mock.call_args.args[0]
    assert len(entities) == 3


async def test_select_entity_fields(mock_zone):

    entity = YamahaYncaSelect("ReceiverUniqueId", mock_zone, TEST_ENTITY_DESCRIPTION)

    assert entity.name == "HDMI Out"
    assert entity.unique_id == "ReceiverUniqueId_ZoneId_hdmiout"
    assert entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId_ZoneId")
    }

    # Setting value
    entity.select_option("off")
    assert mock_zone.hdmiout is ynca.HdmiOut.OFF
    entity.select_option("out1_2")
    assert mock_zone.hdmiout is ynca.HdmiOut.OUT1_PLUS_2

    # Reading state
    mock_zone.hdmiout = ynca.HdmiOut.OUT1
    assert entity.current_option == "out1"
    mock_zone.hdmiout = ynca.HdmiOut.OUT2
    assert entity.current_option == "out2"


async def test_select_power_on_volume_entity_select_option(mock_zone):

    entity = YamahaYncaSelectPowerOnVolume(
        "ReceiverUniqueId", mock_zone, PowerOnVolumeModeEntityDescription
    )

    assert entity.name == "Power on volume mode"
    assert entity.unique_id == "ReceiverUniqueId_ZoneId_power_on_volume_mode"
    assert entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId_ZoneId")
    }

    # Setting value, receiver without initvolmode
    mock_zone.initvolmode = None
    mock_zone.vol = 1.5

    entity.select_option("last_value")
    assert mock_zone.initvolmode is None
    assert mock_zone.initvollvl is ynca.InitVolLvl.OFF

    entity.select_option("mute")
    assert mock_zone.initvolmode is None
    assert mock_zone.initvollvl is ynca.InitVolLvl.MUTE

    entity.select_option("configured_volume")
    assert mock_zone.initvolmode is None
    assert mock_zone.initvollvl == mock_zone.vol

    # Setting value, receiver with initvolmode
    mock_zone.initvolmode = ynca.InitVolMode.ON
    mock_zone.vol = -1.5

    entity.select_option("last_value")
    assert mock_zone.initvolmode is ynca.InitVolMode.OFF
    assert mock_zone.initvollvl == 1.5  # Value did not change

    entity.select_option("configured_volume")
    assert mock_zone.initvolmode is ynca.InitVolMode.ON
    assert mock_zone.initvollvl == 1.5

    entity.select_option("mute")
    assert mock_zone.initvolmode is ynca.InitVolMode.ON
    assert mock_zone.initvollvl is ynca.InitVolLvl.MUTE

    entity.select_option("configured_volume")
    assert mock_zone.initvolmode is ynca.InitVolMode.ON
    assert (
        mock_zone.initvollvl == -1.5
    )  # Copied value from vol as there was no previous value


async def test_select_power_on_volume_entity_current_option(mock_zone):

    entity = YamahaYncaSelectPowerOnVolume(
        "ReceiverUniqueId", mock_zone, PowerOnVolumeModeEntityDescription
    )

    assert entity.name == "Power on volume mode"
    assert entity.unique_id == "ReceiverUniqueId_ZoneId_power_on_volume_mode"
    assert entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId_ZoneId")
    }

    # Current value, receiver without initvolmode
    mock_zone.initvolmode = None
    mock_zone.initvollvl = -12.0
    assert entity.current_option == "configured_volume"

    mock_zone.initvollvl = ynca.InitVolLvl.OFF
    assert entity.current_option == "last_value"

    mock_zone.initvollvl = ynca.InitVolLvl.MUTE
    assert entity.current_option == "mute"

    # Current value, receiver with initvolmode
    mock_zone.initvolmode = ynca.InitVolMode.OFF
    assert entity.current_option == "last_value"

    mock_zone.initvolmode = ynca.InitVolMode.ON
    assert entity.current_option == "mute"  # Lvl value was still mute

    mock_zone.initvollvl = -12.0
    assert entity.current_option == "configured_volume"
