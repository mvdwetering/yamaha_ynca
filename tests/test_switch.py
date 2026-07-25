from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import ANY, Mock, call, patch

from homeassistant.helpers.entity import EntityCategory
import pytest

from custom_components import yamaha_ynca
from custom_components.yamaha_ynca.switch import (
    YamahaYncaSwitch,
    YncaSwitchEntityDescription,
    async_setup_entry,
)
from tests.conftest import setup_integration
import ynca

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

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

TEST_ENTITY_DESCRIPTION_SYS_PWR = YncaSwitchEntityDescription(
    key="pwr",
    name="Name",
    on=ynca.Pwr.ON,
    off=ynca.Pwr.STANDBY,
    associated_zone_attr="main",
    availability_check=lambda _subunit, _associated_zone: True,
)

TEST_ENTITY_DESCRIPTION_DIRMODE = YncaSwitchEntityDescription(
    key="dirmode",
    entity_category=EntityCategory.CONFIG,
    on=ynca.DirMode.ON,
    off=ynca.DirMode.OFF,
)


@patch("custom_components.yamaha_ynca.switch.YamahaYncaSwitch", autospec=True)
async def test_async_setup_entry(
    yamahayncaswitch_mock: Mock,
    hass: HomeAssistant,
    mock_ynca: Mock,
    mock_zone_main: Mock,
) -> None:
    mock_ynca.main = mock_zone_main
    mock_ynca.main.adaptivedrc = ynca.AdaptiveDrc.OFF
    mock_ynca.main.enhancer = ynca.Enhancer.OFF
    mock_ynca.main.exbass = ynca.ExBass.OFF
    mock_ynca.main.dirmode = ynca.DirMode.ON
    mock_ynca.main.hdmiout = ynca.HdmiOut.OUT
    mock_ynca.main.lipsynchdmiout2offset = None
    mock_ynca.main.puredirmode = ynca.PureDirMode.OFF
    mock_ynca.main.speakera = ynca.SpeakerA.OFF
    mock_ynca.main.speakerb = ynca.SpeakerB.ON
    mock_ynca.main.surroundai = ynca.SurroundAI.OFF
    mock_ynca.main.threedcinema = ynca.ThreeDeeCinema.AUTO

    mock_ynca.sys.hdmiout1 = ynca.HdmiOutOnOff.OFF
    mock_ynca.sys.hdmiout2 = ynca.HdmiOutOnOff.ON
    mock_ynca.sys.party = ynca.Party.OFF

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
    assert len(entities) == 14


async def test_switch_entity_fields(mock_zone: Mock) -> None:
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


async def test_switch_associated_zone_handling(
    mock_ynca: Mock, mock_zone_main: Mock
) -> None:
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

    # Default availability behavior depends on associated zone power
    mock_main.pwr = ynca.Pwr.ON
    assert entity.available is True
    mock_main.pwr = ynca.Pwr.STANDBY
    assert entity.available is False


async def test_sys_power_switch_stays_available_when_main_standby(
    mock_ynca: Mock, mock_zone_main: Mock
) -> None:
    mock_sys = mock_ynca.sys
    mock_main = mock_zone_main
    mock_main.pwr = ynca.Pwr.STANDBY
    mock_sys.pwr = ynca.Pwr.STANDBY

    entity = YamahaYncaSwitch(
        "ReceiverUniqueId", mock_sys, TEST_ENTITY_DESCRIPTION_SYS_PWR, mock_main
    )

    assert entity.available is True
    assert entity.is_on is False

    entity.turn_on()
    assert mock_sys.pwr is ynca.Pwr.ON

    entity.turn_off()
    assert mock_sys.pwr is ynca.Pwr.STANDBY


async def test_sys_power_switch_state_not_unavailable_when_main_standby(
    hass: HomeAssistant, mock_ynca: Mock, mock_zone_main: Mock
) -> None:
    mock_ynca.main = mock_zone_main
    mock_ynca.main.pwr = ynca.Pwr.STANDBY
    mock_ynca.sys.pwr = ynca.Pwr.STANDBY

    await setup_integration(hass, mock_ynca)

    all_zones_power = hass.states.get("switch.modelname_main_all_zones_power")
    assert all_zones_power is not None
    assert all_zones_power.state == "off"


async def test_hdmiout_not_supported_at_all(
    hass: HomeAssistant, mock_ynca: Mock, mock_zone_main: Mock
) -> None:
    mock_ynca.main = mock_zone_main
    mock_ynca.main.hdmiout = None
    mock_ynca.main.lipsynchdmiout2offset = None

    await setup_integration(hass, mock_ynca)

    hdmiout = hass.states.get("switch.modelname_main_hdmi_out")
    assert hdmiout is None


async def test_hdmiout_supported_with_one_hdmi_output(
    hass: HomeAssistant, mock_ynca: Mock, mock_zone_main: Mock
) -> None:
    mock_ynca.main = mock_zone_main
    mock_ynca.main.hdmiout = ynca.HdmiOut.OFF
    mock_ynca.main.lipsynchdmiout2offset = None  # This indicates no HDMI2

    await setup_integration(hass, mock_ynca)

    hdmiout = hass.states.get("switch.modelname_main_hdmi_out")
    assert hdmiout is not None


async def test_hdmiout_supported_with_two_hdmi_outputs(
    hass: HomeAssistant, mock_ynca: Mock, mock_zone_main: Mock
) -> None:
    mock_ynca.main = mock_zone_main
    mock_ynca.main.hdmiout = ynca.HdmiOut.OFF
    mock_ynca.main.lipsynchdmiout2offset = 123  # This indicates HDMI2

    await setup_integration(hass, mock_ynca)

    hdmiout = hass.states.get("switch.modelname_main_hdmi_out")
    assert hdmiout is None


# Accessing private _connection is not ideal, but not sure how I want to handle it properly yet
async def test_dirmode(mock_zone_main: Mock) -> None:
    entity = YamahaYncaSwitch(
        "ReceiverUniqueId", mock_zone_main, TEST_ENTITY_DESCRIPTION_DIRMODE
    )

    mock_zone_main._connection = Mock()  # noqa: SLF001
    mock_zone_main._connection.get = Mock()  # noqa: SLF001

    # Check handling of updates from YNCA
    await entity.async_added_to_hass()
    mock_zone_main.register_update_callback.assert_called_once()
    callback = mock_zone_main.register_update_callback.call_args.args[0]
    entity.schedule_update_ha_state = Mock()

    # Dirmode triggers update
    callback("DIRMODE", None)
    entity.schedule_update_ha_state.assert_called_once()
    mock_zone_main._connection.get.assert_not_called()  # noqa: SLF001

    # Straight does not trigger update, but requests update for DIRMODE
    entity.schedule_update_ha_state.reset_mock()

    callback("STRAIGHT", None)
    entity.schedule_update_ha_state.assert_not_called()

    mock_zone_main._connection.get.assert_called_once_with(  # noqa: SLF001
        "MAIN", "DIRMODE"
    )

    # Receiving STRAIGHT again within 500ms does not request an update
    mock_zone_main._connection.get.reset_mock()  # noqa: SLF001

    callback("STRAIGHT", None)
    entity.schedule_update_ha_state.assert_not_called()
    mock_zone_main._connection.get.assert_not_called()  # noqa: SLF001

    # But after the cooldown expires it requests again
    await asyncio.sleep(0.51)
    callback("STRAIGHT", None)
    entity.schedule_update_ha_state.assert_not_called()
    mock_zone_main._connection.get.assert_called_once_with(  # noqa: SLF001
        "MAIN", "DIRMODE"
    )

    # Cleanup on exit
    await entity.async_will_remove_from_hass()
    mock_zone_main.unregister_update_callback.assert_called_once_with(callback)


async def test_speaker_ab_switches_available_without_zone_b(
    hass: HomeAssistant,
    mock_ynca: Mock,
    mock_zone_main: Mock,
) -> None:
    mock_zone_main.speakera = ynca.SpeakerA.OFF
    mock_zone_main.speakerb = ynca.SpeakerB.ON
    mock_zone_main.zonebavail = None
    mock_ynca.main = mock_zone_main
    await setup_integration(hass, mock_ynca)

    speaker_a = hass.states.get("switch.modelname_main_zone_a_speakers")
    assert speaker_a is not None
    speaker_b = hass.states.get("switch.modelname_main_zone_b_speakers")
    assert speaker_b is not None


async def test_speaker_ab_switches_unavailable_when_zone_b_exists(
    hass: HomeAssistant,
    mock_ynca: Mock,
    mock_zone_main: Mock,
) -> None:
    mock_zone_main.speakera = ynca.SpeakerA.OFF
    mock_zone_main.speakerb = ynca.SpeakerB.ON
    mock_zone_main.zonebavail = (
        ynca.ZoneBAvail.NOT_READY
    )  # Does not need to be READY, exists is enough
    mock_ynca.main = mock_zone_main
    await setup_integration(hass, mock_ynca)

    speaker_a = hass.states.get("switch.modelname_main_zone_a_speakers")
    assert speaker_a is None
    speaker_b = hass.states.get("switch.modelname_main_zone_b_speakers")
    assert speaker_b is None


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_subwoofer_not_supported(
    hass: HomeAssistant,
    mock_ynca: Mock,
    mock_zone_main: Mock,
) -> None:
    mock_ynca.main = mock_zone_main
    mock_ynca.main.pwr = ynca.Pwr.ON

    await setup_integration(hass, mock_ynca)

    assert hass.states.get("switch.modelname_main_subwoofer") is None


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_subwoofer_single_pattern_single_sub(
    hass: HomeAssistant,
    mock_ynca: Mock,
    mock_zone_main: Mock,
) -> None:
    mock_ynca.main = mock_zone_main
    mock_ynca.main.pwr = ynca.Pwr.ON
    mock_ynca.sys.sppattern1swfr1cnfg = ynca.SpPatternSwfrCnfg.USE

    await setup_integration(hass, mock_ynca)

    subwoofer = hass.states.get("switch.modelname_main_subwoofer")
    assert subwoofer is not None
    assert subwoofer.state == "on"


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_subwoofer_single_pattern_two_subs(
    hass: HomeAssistant,
    mock_ynca: Mock,
    mock_zone_main: Mock,
) -> None:
    mock_ynca.main = mock_zone_main
    mock_ynca.main.pwr = ynca.Pwr.ON
    mock_ynca.sys.sppattern1swfr1cnfg = ynca.SpPatternSwfrCnfg.USE
    mock_ynca.sys.sppattern1swfr2cnfg = ynca.SpPatternSwfrCnfg.NONE

    await setup_integration(hass, mock_ynca)

    subwoofer_1 = hass.states.get("switch.modelname_main_subwoofer_1")
    assert subwoofer_1 is not None
    assert subwoofer_1.state == "on"
    subwoofer_2 = hass.states.get("switch.modelname_main_subwoofer_2")
    assert subwoofer_2 is not None
    assert subwoofer_2.state == "off"


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_subwoofer_two_patterns_single_sub(
    hass: HomeAssistant,
    mock_ynca: Mock,
    mock_zone_main: Mock,
) -> None:
    mock_ynca.main = mock_zone_main
    mock_ynca.main.pwr = ynca.Pwr.ON
    mock_ynca.sys.sppattern1swfr1cnfg = ynca.SpPatternSwfrCnfg.USE
    mock_ynca.sys.sppattern2swfr1cnfg = ynca.SpPatternSwfrCnfg.NONE

    await setup_integration(hass, mock_ynca)

    subwoofer_p1 = hass.states.get("switch.modelname_main_subwoofer_pattern_1")
    assert subwoofer_p1 is not None
    assert subwoofer_p1.state == "on"
    subwoofer_p2 = hass.states.get("switch.modelname_main_subwoofer_pattern_2")
    assert subwoofer_p2 is not None
    assert subwoofer_p2.state == "off"


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_subwoofer_two_patterns_two_subs(
    hass: HomeAssistant,
    mock_ynca: Mock,
    mock_zone_main: Mock,
) -> None:
    mock_ynca.main = mock_zone_main
    mock_ynca.main.pwr = ynca.Pwr.ON
    mock_ynca.sys.sppattern1swfr1cnfg = ynca.SpPatternSwfrCnfg.USE
    mock_ynca.sys.sppattern1swfr2cnfg = ynca.SpPatternSwfrCnfg.NONE
    mock_ynca.sys.sppattern2swfr1cnfg = ynca.SpPatternSwfrCnfg.USE
    mock_ynca.sys.sppattern2swfr2cnfg = ynca.SpPatternSwfrCnfg.NONE

    await setup_integration(hass, mock_ynca)

    subwoofer_1_p1 = hass.states.get("switch.modelname_main_subwoofer_1_pattern_1")
    assert subwoofer_1_p1 is not None
    assert subwoofer_1_p1.state == "on"
    subwoofer_2_p1 = hass.states.get("switch.modelname_main_subwoofer_2_pattern_1")
    assert subwoofer_2_p1 is not None
    assert subwoofer_2_p1.state == "off"
    subwoofer_1_p2 = hass.states.get("switch.modelname_main_subwoofer_1_pattern_2")
    assert subwoofer_1_p2 is not None
    assert subwoofer_1_p2.state == "on"
    subwoofer_2_p2 = hass.states.get("switch.modelname_main_subwoofer_2_pattern_2")
    assert subwoofer_2_p2 is not None
    assert subwoofer_2_p2.state == "off"
