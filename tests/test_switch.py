from __future__ import annotations

from unittest.mock import ANY, Mock, call, patch

import ynca

import custom_components.yamaha_ynca as yamaha_ynca
from custom_components.yamaha_ynca.switch import (
    YamahaYncaSwitch,
    YncaSwitchEntityDescription,
    async_setup_entry,
)
from homeassistant.helpers.entity import EntityCategory

from tests.conftest import setup_integration

TEST_ENTITY_DESCRIPTION = YncaSwitchEntityDescription(
    key="enhancer",
    entity_category=EntityCategory.CONFIG,
    name="Name",
    on=ynca.Enhancer.ON,
    off=ynca.Enhancer.OFF,
)

TEST_ENTITY_DESCRIPTION_ASSOCIATED_ZONE = YncaSwitchEntityDescription(
    key="hdmiout1",
    name="Name",
    on=ynca.HdmiOutOnOff.ON,
    off=ynca.HdmiOutOnOff.OFF,
    associated_zone_attr="main",
)


@patch("custom_components.yamaha_ynca.switch.YamahaYncaSwitch", autospec=True)
async def test_async_setup_entry(
    yamahayncaswitch_mock, hass, mock_ynca, mock_zone_main
):
    mock_ynca.main = mock_zone_main
    mock_ynca.main.adaptivedrc = ynca.AdaptiveDrc.OFF
    mock_ynca.main.enhancer = ynca.Enhancer.OFF
    mock_ynca.main.threedcinema = ynca.ThreeDeeCinema.AUTO
    mock_ynca.main.puredirmode = ynca.PureDirMode.OFF
    mock_ynca.main.hdmiout = ynca.HdmiOut.OUT
    mock_ynca.main.lipsynchdmiout2offset = None
    mock_ynca.main.speakera = ynca.SpeakerA.OFF
    mock_ynca.main.speakerb = ynca.SpeakerB.ON
    mock_ynca.sys.hdmiout1 = ynca.HdmiOutOnOff.OFF
    mock_ynca.sys.hdmiout2 = ynca.HdmiOutOnOff.ON

    integration = await setup_integration(hass, mock_ynca)
    add_entities_mock = Mock()

    await async_setup_entry(hass, integration.entry, add_entities_mock)

    yamahayncaswitch_mock.assert_has_calls(
        [
            # TODO: improve checks to see if expected entity descriptions are used
            #       but just want to check for key, not the whole (internal) configuration
            call("entry_id", mock_ynca.main, ANY),
            call("entry_id", mock_ynca.main, ANY),
            call("entry_id", mock_ynca.main, ANY),
            call("entry_id", mock_ynca.main, ANY),
        ]
    )

    add_entities_mock.assert_called_once()
    entities = add_entities_mock.call_args.args[0]
    assert len(entities) == 9


async def test_switch_entity_fields(mock_zone):

    entity = YamahaYncaSwitch("ReceiverUniqueId", mock_zone, TEST_ENTITY_DESCRIPTION)

    assert entity.unique_id == "ReceiverUniqueId_ZoneId_enhancer"
    assert entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId_ZoneId")
    }

    # Setting value
    entity.turn_on()
    assert mock_zone.enhancer is ynca.Enhancer.ON
    entity.turn_off()
    assert mock_zone.enhancer is ynca.Enhancer.OFF

    # Reading state
    mock_zone.enhancer = ynca.Enhancer.ON
    assert entity.is_on is True
    mock_zone.enhancer = ynca.Enhancer.OFF
    assert entity.is_on is False


async def test_switch_associated_zone_handling(mock_ynca, mock_zone_main):

    mock_sys = mock_ynca.sys
    mock_main = mock_zone_main

    entity = YamahaYncaSwitch(
        "ReceiverUniqueId", mock_sys, TEST_ENTITY_DESCRIPTION_ASSOCIATED_ZONE, mock_main
    )

    assert entity.unique_id == "ReceiverUniqueId_SYS_hdmiout1"
    assert entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId_MAIN")
    }

    # Setting value
    entity.turn_on()
    assert mock_sys.hdmiout1 is ynca.HdmiOutOnOff.ON
    entity.turn_off()
    assert mock_sys.hdmiout1 is ynca.HdmiOutOnOff.OFF

    # Reading state
    mock_sys.hdmiout1 = ynca.HdmiOutOnOff.ON
    assert entity.is_on is True
    mock_sys.hdmiout1 = ynca.HdmiOutOnOff.OFF
    assert entity.is_on is False


async def test_hdmiout_not_supported_at_all(hass, mock_ynca, mock_zone_main):
    mock_ynca.main = mock_zone_main
    mock_ynca.main.hdmiout = None
    mock_ynca.main.lipsynchdmiout2offset = None

    await setup_integration(hass, mock_ynca)

    hdmiout = hass.states.get("switch.modelname_main_hdmi_out")
    assert hdmiout is None


async def test_hdmiout_supported_with_one_hdmi_output(hass, mock_ynca, mock_zone_main):
    mock_ynca.main = mock_zone_main
    mock_ynca.main.hdmiout = ynca.HdmiOut.OFF
    mock_ynca.main.lipsynchdmiout2offset = None  # This indicates no HDMI2

    await setup_integration(hass, mock_ynca)

    hdmiout = hass.states.get("switch.modelname_main_hdmi_out")
    assert hdmiout is not None


async def test_hdmiout_supported_but_with_two_hdmi_outputs(
    hass, mock_ynca, mock_zone_main
):
    mock_ynca.main = mock_zone_main
    mock_ynca.main.hdmiout = ynca.HdmiOut.OFF
    mock_ynca.main.lipsynchdmiout2offset = 123  # This indicates HDMI2

    await setup_integration(hass, mock_ynca)

    hdmiout = hass.states.get("switch.modelname_main_hdmi_out")
    assert hdmiout is None
