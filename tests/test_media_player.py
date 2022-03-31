"""Test the Yamaha (YNCA) config flow."""
from unittest.mock import Mock

import custom_components.yamaha_ynca as yamaha_ynca
import pytest
import ynca
from custom_components.yamaha_ynca.media_player import YamahaYncaZone
from homeassistant.components.media_player.const import (
    SUPPORT_SELECT_SOUND_MODE,
    SUPPORT_SELECT_SOURCE,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
)
from homeassistant.const import STATE_OFF, STATE_ON


@pytest.fixture
def mock_zone():
    """Create a mocked Zone instance."""
    zone = Mock(
        spec=ynca.ZoneBase,
    )

    zone.id = "ZoneId"
    zone.name = "ZoneName"
    zone.scenes = {"1234": "SceneName 1234"}
    zone.max_volume = 10
    zone.min_volume = -5
    zone.input = "INPUT_ID_1"
    zone.inputs = {"INPUT_ID_1": "Input Name 1", "INPUT_ID_2": "Input Name 2"}

    return zone


@pytest.fixture
def yamaha_ynca_zone(mock_zone, mock_receiver):
    return YamahaYncaZone("ReceiverUniqueId", mock_receiver, mock_zone)


async def test_mediaplayer_entity(mock_zone, mock_receiver):

    entity = YamahaYncaZone("ReceiverUniqueId", mock_receiver, mock_zone)

    assert entity.unique_id == "ReceiverUniqueId_ZoneId"
    assert entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId")
    }
    assert entity.name == "ZoneName"

    await entity.async_added_to_hass()
    mock_zone.register_update_callback.assert_called_once_with(
        entity.schedule_update_ha_state
    )

    await entity.async_will_remove_from_hass()
    mock_zone.unregister_update_callback.assert_called_once_with(
        mock_zone.register_update_callback.call_args.args[0]
    )


async def test_mediaplayer_entity_turn_on_off(mock_zone, mock_receiver):
    entity = YamahaYncaZone("ReceiverUniqueId", mock_receiver, mock_zone)

    entity.turn_on()
    assert mock_zone.pwr == True
    assert entity.state == STATE_ON

    entity.turn_off()
    assert mock_zone.pwr == False
    assert entity.state == STATE_OFF


async def test_mediaplayer_entity_mute_volume(mock_zone, mock_receiver):
    entity = YamahaYncaZone("ReceiverUniqueId", mock_receiver, mock_zone)

    entity.mute_volume(True)
    assert mock_zone.mute == ynca.Mute.on
    assert entity.is_volume_muted == True

    entity.mute_volume(False)
    assert mock_zone.mute == ynca.Mute.off
    assert entity.is_volume_muted == False


async def test_mediaplayer_entity_volume_set_up_down(mock_zone, mock_receiver):
    entity = YamahaYncaZone("ReceiverUniqueId", mock_receiver, mock_zone)

    entity.set_volume_level(1)
    assert mock_zone.volume == 10
    assert entity.volume_level == 1

    entity.set_volume_level(0)
    assert mock_zone.volume == -5
    assert entity.volume_level == 0

    entity.volume_up()
    assert mock_zone.volume_up.call_count == 1

    entity.volume_down()
    assert mock_zone.volume_down.call_count == 1


async def test_mediaplayer_entity_source(mock_zone, mock_receiver):
    entity = YamahaYncaZone("ReceiverUniqueId", mock_receiver, mock_zone)

    assert entity.source_list == ["Input Name 1", "Input Name 2"]

    entity.select_source("Input Name 2")
    assert mock_zone.input == "INPUT_ID_2"
    assert entity.source == "Input Name 2"


async def test_mediaplayer_entity_sound_mode(mock_zone, mock_receiver):
    entity = YamahaYncaZone("ReceiverUniqueId", mock_receiver, mock_zone)

    entity.select_sound_mode("Sound mode 2")
    assert mock_zone.soundprg == "Sound mode 2"
    assert mock_zone.straight == False
    assert entity.sound_mode == "Sound mode 2"

    # Straight is special as it is a separate setting on the Zone
    entity.select_sound_mode("Straight")
    assert mock_zone.soundprg == "Sound mode 2"
    assert mock_zone.straight == True
    assert entity.sound_mode == "Straight"


async def test_mediaplayer_entity_sound_mode_list(mock_zone, mock_receiver):
    entity = YamahaYncaZone("ReceiverUniqueId", mock_receiver, mock_zone)

    mock_zone.straight = False
    assert "Straight" in entity.sound_mode_list

    mock_zone.straight = None
    assert not "Straight" in entity.sound_mode_list

    mock_zone.soundprg = None
    assert entity.sound_mode_list is None

    mock_zone.soundprg = "DspSoundProgram"
    assert entity.sound_mode_list == sorted(ynca.SoundPrg)


async def test_mediaplayer_entity_supported_features(mock_zone, mock_receiver):
    entity = YamahaYncaZone("ReceiverUniqueId", mock_receiver, mock_zone)

    expected_supported_features = (
        SUPPORT_VOLUME_SET
        | SUPPORT_VOLUME_MUTE
        | SUPPORT_VOLUME_STEP
        | SUPPORT_TURN_ON
        | SUPPORT_TURN_OFF
        | SUPPORT_SELECT_SOURCE
    )

    mock_zone.soundprg = None
    assert entity.supported_features == expected_supported_features

    mock_zone.soundprg = "DspSoundProgram"
    expected_supported_features |= SUPPORT_SELECT_SOUND_MODE
    assert entity.supported_features == expected_supported_features
