from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from custom_components import yamaha_ynca
from custom_components.yamaha_ynca.const import CONF_SELECTED_SURROUND_DECODERS
from custom_components.yamaha_ynca.select import (
    ENTITY_DESCRIPTIONS,
    YamahaYncaSelect,
    YamahaYncaSelectInitialVolumeMode,
    YamahaYncaSelectSurroundDecoder,
    YncaSelectEntityDescription,
    async_setup_entry,
)
from tests.conftest import setup_integration
import ynca

if TYPE_CHECKING:  # pragma: no cover
    from ynca.subunits.zone import ZoneBase


TEST_ENTITY_DESCRIPTION = YncaSelectEntityDescription(  # type: ignore
    key="hdmiout",
    entity_category=EntityCategory.CONFIG,
    enum=ynca.HdmiOut,
    icon="mdi:hdmi-port",
    name="HDMI Out",
)


def get_entity_description_by_key(key: str):
    return [e for e in ENTITY_DESCRIPTIONS if e.key == key][0]


async def test_async_setup_entry(
    hass,
    mock_ynca: ynca.YncaApi,
    mock_zone_main: ZoneBase,
):
    mock_ynca.main = mock_zone_main
    mock_ynca.main.hdmiout = ynca.HdmiOut.OUT1_PLUS_2
    mock_ynca.main.lipsynchdmiout2offset = 123
    mock_ynca.main.sleep = ynca.Sleep.THIRTY_MIN
    mock_ynca.main.initvollvl = ynca.InitVolLvl.MUTE
    mock_ynca.main.twochdecoder = ynca.TwoChDecoder.DolbyPl2Music

    mock_ynca.sys.sppattern = ynca.SpPattern.PATTERN_1

    integration = await setup_integration(hass, mock_ynca)
    add_entities_mock = Mock()

    await async_setup_entry(hass, integration.entry, add_entities_mock)

    add_entities_mock.assert_called_once()
    entities = add_entities_mock.call_args.args[0]
    assert len(entities) == 5


async def test_select_entity_fields(mock_zone: ZoneBase, mock_config_entry):
    entity = YamahaYncaSelect(
        mock_config_entry, "ReceiverUniqueId", mock_zone, TEST_ENTITY_DESCRIPTION
    )

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


async def test_select_initial_volume_mode_entity_select_option(
    mock_zone: ZoneBase, mock_config_entry
):
    entity = YamahaYncaSelectInitialVolumeMode(
        mock_config_entry,
        "ReceiverUniqueId",
        mock_zone,
        get_entity_description_by_key("initial_volume_mode"),
    )

    assert entity.unique_id == "ReceiverUniqueId_ZoneId_initial_volume_mode"
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

    entity.select_option("configured_initial_volume")
    assert mock_zone.initvolmode is None
    assert mock_zone.initvollvl == mock_zone.vol

    # Setting value, receiver with initvolmode
    mock_zone.initvolmode = ynca.InitVolMode.ON
    mock_zone.vol = -1.5

    entity.select_option("last_value")
    assert mock_zone.initvolmode is ynca.InitVolMode.OFF
    assert mock_zone.initvollvl == 1.5  # Value did not change

    entity.select_option("configured_initial_volume")
    assert mock_zone.initvolmode is ynca.InitVolMode.ON
    assert mock_zone.initvollvl == 1.5

    entity.select_option("mute")
    assert mock_zone.initvolmode is ynca.InitVolMode.ON
    assert mock_zone.initvollvl is ynca.InitVolLvl.MUTE

    entity.select_option("configured_initial_volume")
    assert mock_zone.initvolmode is ynca.InitVolMode.ON
    assert (
        mock_zone.initvollvl == -1.5
    )  # Copied value from vol as there was no previous value


async def test_select_initial_volume_mode_entity_current_option(
    mock_zone: ZoneBase, mock_config_entry
):
    entity = YamahaYncaSelectInitialVolumeMode(
        mock_config_entry,
        "ReceiverUniqueId",
        mock_zone,
        get_entity_description_by_key("initial_volume_mode"),
    )

    assert entity.unique_id == "ReceiverUniqueId_ZoneId_initial_volume_mode"
    assert entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId_ZoneId")
    }

    # Current value, receiver without initvolmode
    mock_zone.initvolmode = None
    mock_zone.initvollvl = -12.0
    assert entity.current_option == "configured_initial_volume"

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
    assert entity.current_option == "configured_initial_volume"


async def test_select_surrounddecoder_entity_current_option(
    mock_zone: ZoneBase, mock_config_entry
):
    entity = YamahaYncaSelectSurroundDecoder(
        mock_config_entry,
        "ReceiverUniqueId",
        mock_zone,
        get_entity_description_by_key("twochdecoder"),
    )

    assert entity.unique_id == "ReceiverUniqueId_ZoneId_twochdecoder"
    assert entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId_ZoneId")
    }

    # Current value, normal value
    mock_zone.twochdecoder = ynca.TwoChDecoder.DolbyPl
    assert entity.current_option == "dolby_pl"

    # Current value, PLII value
    mock_zone.twochdecoder = ynca.TwoChDecoder.DolbyPl2Game
    assert entity.current_option == "dolby_plii_game"

    # Current value, PLIIx value
    mock_zone.twochdecoder = ynca.TwoChDecoder.DolbyPl2xMovie
    assert entity.current_option == "dolby_plii_movie"

    # Current value, not supported (should not happen)
    mock_zone.twochdecoder = None
    assert entity.current_option is None


async def test_select_surrounddecoder_entity_options_nothing_selection_in_configentry(
    mock_zone: ZoneBase, mock_config_entry
):
    entity = YamahaYncaSelectSurroundDecoder(
        mock_config_entry,
        "ReceiverUniqueId",
        mock_zone,
        get_entity_description_by_key("twochdecoder"),
    )

    assert entity.options == [
        "auro_3d",
        "auto",
        "dolby_pl",
        "dolby_plii_game",
        "dolby_plii_movie",
        "dolby_plii_music",
        "dolby_surround",
        "dts_neo_6_cinema",
        "dts_neo_6_music",
        "dts_neural_x",
    ]


async def test_select_surrounddecoder_entity_options_some_selected_in_configentry(
    hass: HomeAssistant, mock_zone: ZoneBase, mock_config_entry
):
    await hass.config_entries.async_add(mock_config_entry)
    hass.config_entries.async_update_entry(
        mock_config_entry,
        options={
            CONF_SELECTED_SURROUND_DECODERS: ["dolby_pl", "auto", "dolby_plii_movie"]
        },
    )

    entity = YamahaYncaSelectSurroundDecoder(
        mock_config_entry,
        "ReceiverUniqueId",
        mock_zone,
        get_entity_description_by_key("twochdecoder"),
    )

    assert entity.options == ["auto", "dolby_pl", "dolby_plii_movie"]


async def test_hdmiout_not_supported_at_all(hass, mock_ynca, mock_zone_main):
    mock_ynca.main = mock_zone_main
    mock_ynca.main.hdmiout = None
    mock_ynca.main.lipsynchdmiout2offset = None

    await setup_integration(hass, mock_ynca)

    hdmiout = hass.states.get("select.modelname_main_hdmi_out")
    assert hdmiout is None


async def test_hdmiout_supported_with_one_hdmi_output(hass, mock_ynca, mock_zone_main):
    mock_ynca.main = mock_zone_main
    mock_ynca.main.hdmiout = ynca.HdmiOut.OFF
    mock_ynca.main.lipsynchdmiout2offset = None  # This indicates no HDMI2

    await setup_integration(hass, mock_ynca)

    hdmiout = hass.states.get("select.modelname_main_hdmi_out")
    assert hdmiout is None


async def test_hdmiout_supported_but_with_two_hdmi_outputs(
    hass, mock_ynca, mock_zone_main
):
    mock_ynca.main = mock_zone_main
    mock_ynca.main.hdmiout = ynca.HdmiOut.OFF
    mock_ynca.main.lipsynchdmiout2offset = 123  # This indicates HDMI2

    await setup_integration(hass, mock_ynca)

    hdmiout = hass.states.get("select.modelname_main_hdmi_out")
    assert hdmiout is not None
