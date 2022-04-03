"""Test the Yamaha (YNCA) config flow."""
from unittest.mock import Mock, PropertyMock, create_autospec, patch

import custom_components.yamaha_ynca as yamaha_ynca
import pytest
import ynca
from custom_components.yamaha_ynca.media_player import YamahaYncaZone
from homeassistant.components.media_player.const import (
    SUPPORT_SELECT_SOUND_MODE,
    SUPPORT_SELECT_SOURCE,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_PLAY,
    SUPPORT_PAUSE,
    SUPPORT_STOP,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_SHUFFLE_SET,
    SUPPORT_REPEAT_SET,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
    MEDIA_TYPE_MUSIC,
    MEDIA_TYPE_CHANNEL,
    REPEAT_MODE_ALL,
    REPEAT_MODE_OFF,
    REPEAT_MODE_ONE,
)
from homeassistant.const import (
    STATE_OFF,
    STATE_ON,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_IDLE,
)


@pytest.fixture
def mock_zone():
    """Create a mocked Zone instance."""
    zone = Mock(
        spec=ynca.zone.ZoneBase,
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
    mock_zone.register_update_callback.assert_called_once()

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

    # Sources with `playback` attribute support playback controls

    # Radio sources only support play and stop
    mock_receiver.NETRADIO = create_autospec(
        ynca.netradio.NetRadio, id=ynca.Subunit.NETRADIO
    )
    mock_zone.input = "NET RADIO"
    expected_supported_features |= SUPPORT_PLAY
    expected_supported_features |= SUPPORT_STOP
    assert entity.supported_features == expected_supported_features

    # Other sources also support pausem previous, next
    mock_receiver.USB = create_autospec(
        ynca.mediaplayback_subunits.Usb, id=ynca.Subunit.USB
    )
    mock_zone.input = "USB"
    expected_supported_features |= SUPPORT_PAUSE
    expected_supported_features |= SUPPORT_PREVIOUS_TRACK
    expected_supported_features |= SUPPORT_NEXT_TRACK
    # USB also supports repeat and shuffle
    expected_supported_features |= SUPPORT_REPEAT_SET
    expected_supported_features |= SUPPORT_SHUFFLE_SET

    assert entity.supported_features == expected_supported_features


async def test_mediaplayer_entity_state(mock_zone, mock_receiver):
    entity = YamahaYncaZone("ReceiverUniqueId", mock_receiver, mock_zone)

    mock_zone.pwr = False
    assert entity.state == STATE_OFF

    mock_zone.pwr = True
    assert entity.state == STATE_ON

    mock_zone.input = "USB"
    mock_receiver.USB = create_autospec(
        ynca.mediaplayback_subunits.Usb, id=ynca.Subunit.USB
    )

    mock_receiver.USB.playbackinfo = ynca.PlaybackInfo.PLAY
    assert entity.state == STATE_PLAYING

    mock_receiver.USB.playbackinfo = ynca.PlaybackInfo.PAUSE
    assert entity.state == STATE_PAUSED

    mock_receiver.USB.playbackinfo = ynca.PlaybackInfo.STOP
    assert entity.state == STATE_IDLE


async def test_mediaplayer_playback_controls(mock_zone, mock_receiver):
    entity = YamahaYncaZone("ReceiverUniqueId", mock_receiver, mock_zone)

    entity.media_play()
    mock_zone.playback.assert_called_with(ynca.Playback.PLAY)
    entity.media_pause()
    mock_zone.playback.assert_called_with(ynca.Playback.PAUSE)
    entity.media_stop()
    mock_zone.playback.assert_called_with(ynca.Playback.STOP)
    entity.media_next_track()
    mock_zone.playback.assert_called_with(ynca.Playback.SKIP_FWD)
    entity.media_previous_track()
    mock_zone.playback.assert_called_with(ynca.Playback.SKIP_REV)


async def test_mediaplayer_mediainfo(mock_zone, mock_receiver):
    entity = YamahaYncaZone("ReceiverUniqueId", mock_receiver, mock_zone)

    assert entity.media_album_name is None
    assert entity.media_artist is None
    assert entity.media_title is None
    assert entity.media_channel is None
    assert entity.media_content_type is None

    # Some subunits support Music with Artist, Album, Song
    mock_zone.input = "USB"
    mock_receiver.USB = create_autospec(
        ynca.mediaplayback_subunits.Usb, id=ynca.Subunit.USB
    )

    mock_receiver.USB.album = "AlbumName"
    mock_receiver.USB.artist = "ArtistName"
    mock_receiver.USB.song = "Title"
    assert entity.media_album_name == "AlbumName"
    assert entity.media_artist == "ArtistName"
    assert entity.media_title == "Title"
    assert entity.media_content_type is MEDIA_TYPE_MUSIC

    # Netradio is a "channel" which name is exposed by the "station" attribute
    mock_zone.input = "NET RADIO"
    mock_receiver.NETRADIO = create_autospec(
        ynca.netradio.NetRadio, id=ynca.Subunit.NETRADIO
    )
    mock_receiver.NETRADIO.station = "StationName"
    assert entity.media_channel == "StationName"
    assert entity.media_content_type is MEDIA_TYPE_CHANNEL

    # Tuner (analog radio) is a "channel"
    # There is no station name, so build name from band and frequency
    mock_zone.input = "TUNER"
    mock_receiver.TUN = create_autospec(ynca.tun.Tun, id=ynca.Subunit.TUN)
    mock_receiver.TUN.band = ynca.Band.FM
    mock_receiver.TUN.fmfreq = 123.45
    assert entity.media_channel == "FM 123.45 MHz"
    assert entity.media_content_type is MEDIA_TYPE_CHANNEL

    mock_receiver.TUN.band = ynca.Band.AM
    mock_receiver.TUN.amfreq = 1234
    assert entity.media_channel == "AM 1234 kHz"
    assert entity.media_content_type is MEDIA_TYPE_CHANNEL

    # Sirius subunits expose name by the "chname" attribute
    mock_zone.input = "SIRIUS InternetRadio"
    mock_receiver.SIRIUSIR = create_autospec(
        ynca.sirius.SiriusIr, id=ynca.Subunit.SIRIUSIR
    )
    mock_receiver.SIRIUSIR.chname = "ChannelName"
    assert entity.media_channel == "ChannelName"
    assert entity.media_content_type is MEDIA_TYPE_CHANNEL


async def test_mediaplayer_entity_shuffle(mock_zone, mock_receiver):
    entity = YamahaYncaZone("ReceiverUniqueId", mock_receiver, mock_zone)

    # Unsupported subunit selected
    assert entity.shuffle == None

    # Subunit supporting shuffle
    mock_zone.input = "USB"
    mock_receiver.USB = create_autospec(
        ynca.mediaplayback_subunits.Usb, id=ynca.Subunit.USB
    )

    entity.set_shuffle(True)
    assert mock_receiver.USB.shuffle == True
    assert entity.shuffle == True

    entity.set_shuffle(False)
    assert mock_receiver.USB.shuffle == False
    assert entity.shuffle == False

    # Subunit not supporting shuffle
    mock_zone.input = "NET RADIO"
    mock_receiver.NETRADIO = create_autospec(
        ynca.netradio.NetRadio, id=ynca.Subunit.NETRADIO
    )
    assert entity.shuffle == None


async def test_mediaplayer_entity_repeat(mock_zone, mock_receiver):
    entity = YamahaYncaZone("ReceiverUniqueId", mock_receiver, mock_zone)

    # Unsupported subunit selected
    assert entity.repeat == None

    # Subunit supporting repeat
    mock_zone.input = "USB"
    mock_receiver.USB = create_autospec(
        ynca.mediaplayback_subunits.Usb, id=ynca.Subunit.USB
    )

    entity.set_repeat(REPEAT_MODE_OFF)
    assert mock_receiver.USB.repeat == ynca.Repeat.OFF
    assert entity.repeat == REPEAT_MODE_OFF

    entity.set_repeat(REPEAT_MODE_ONE)
    assert mock_receiver.USB.repeat == ynca.Repeat.SINGLE
    assert entity.repeat == REPEAT_MODE_ONE

    entity.set_repeat(REPEAT_MODE_ALL)
    assert mock_receiver.USB.repeat == ynca.Repeat.ALL
    assert entity.repeat == REPEAT_MODE_ALL

    # Subunit not supporting shuffle
    mock_zone.input = "NET RADIO"
    mock_receiver.NETRADIO = create_autospec(
        ynca.netradio.NetRadio, id=ynca.Subunit.NETRADIO
    )
    assert entity.repeat == None
