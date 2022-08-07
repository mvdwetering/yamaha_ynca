"""Test the Yamaha (YNCA) config flow."""
from unittest.mock import Mock, create_autospec, patch

import pytest
from homeassistant.components.media_player import MediaPlayerEntityFeature
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_CHANNEL,
    MEDIA_TYPE_MUSIC,
    REPEAT_MODE_ALL,
    REPEAT_MODE_OFF,
    REPEAT_MODE_ONE,
)
from homeassistant.const import (
    STATE_IDLE,
    STATE_OFF,
    STATE_ON,
    STATE_PAUSED,
    STATE_PLAYING,
)

import ynca
import custom_components.yamaha_ynca as yamaha_ynca
from custom_components.yamaha_ynca.media_player import YamahaYncaZone


@pytest.fixture
def mock_zone():
    """Create a mocked YNCA Zone instance."""
    zone = Mock(
        spec=ynca.zone.ZoneBase,
    )

    zone.id = "ZoneId"
    zone.zonename = "ZoneName"
    zone.scene_names = {"1234": "SceneName 1234"}
    zone.max_volume = 10
    zone.min_volume = -5
    zone.input = "INPUT_ID_1"

    return zone


@pytest.fixture
def mp_entity(mock_zone, mock_ynca):
    return YamahaYncaZone("ReceiverUniqueId", mock_ynca, mock_zone, [])


@patch("ynca.get_inputinfo_list", return_value=[])
async def test_mediaplayer_entity(patched_get_inputinfo_list, mp_entity, mock_zone):
    assert mp_entity.unique_id == "ReceiverUniqueId_ZoneId"
    assert mp_entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId")
    }
    assert mp_entity.name == "ZoneName"

    await mp_entity.async_added_to_hass()
    mock_zone.register_update_callback.assert_called_once()

    await mp_entity.async_will_remove_from_hass()
    mock_zone.unregister_update_callback.assert_called_once_with(
        mock_zone.register_update_callback.call_args.args[0]
    )


async def test_mediaplayer_entity_name(
    mp_entity,
    mock_zone,
):
    assert mp_entity.name == "ZoneName"

    mock_zone.zonename = None
    assert mp_entity.name == "ZoneId"


@patch("ynca.get_inputinfo_list", return_value=[])
async def test_mediaplayer_entity_turn_on_off(
    patched_get_inputinfo_list,
    mp_entity,
    mock_zone,
):
    mp_entity.turn_on()
    assert mock_zone.pwr == True
    assert mp_entity.state == STATE_ON

    mp_entity.turn_off()
    assert mock_zone.pwr == False
    assert mp_entity.state == STATE_OFF


async def test_mediaplayer_entity_mute_volume(mp_entity, mock_zone):

    mp_entity.mute_volume(True)
    assert mock_zone.mute == ynca.Mute.on
    assert mp_entity.is_volume_muted == True

    mp_entity.mute_volume(False)
    assert mock_zone.mute == ynca.Mute.off
    assert mp_entity.is_volume_muted == False


async def test_mediaplayer_entity_volume_set_up_down(mp_entity, mock_zone):

    mp_entity.set_volume_level(1)
    assert mock_zone.volume == 10
    assert mp_entity.volume_level == 1

    mp_entity.set_volume_level(0)
    assert mock_zone.volume == -5
    assert mp_entity.volume_level == 0

    mp_entity.volume_up()
    assert mock_zone.volume_up.call_count == 1

    mp_entity.volume_down()
    assert mock_zone.volume_down.call_count == 1


async def test_mediaplayer_entity_source(mock_zone, mock_ynca):
    with patch(
        "ynca.get_inputinfo_list",
        return_value=[
            ynca.InputInfo(None, "INPUT_ID_1", "Input Name 1"),
            ynca.InputInfo(None, "INPUT_ID_2", "Input Name 2"),
        ],
    ):
        mp_entity = YamahaYncaZone(
            "ReceiverUniqueId", mock_ynca, mock_zone, ["INPUT_ID_1"]
        )

        assert mp_entity.source_list == ["Input Name 2"]

        mp_entity.select_source("Input Name 2")
        assert mock_zone.input == "INPUT_ID_2"
        assert mp_entity.source == "Input Name 2"

        mp_entity.select_source("invalid source")  # does not change current source
        assert mock_zone.input == "INPUT_ID_2"
        assert mp_entity.source == "Input Name 2"

        # Input without mapped name shows as ID
        mock_zone.input = "INPUT_ID_WITHOUT_NAME"
        assert mp_entity.source == "INPUT_ID_WITHOUT_NAME"


async def test_mediaplayer_entity_sound_mode(mp_entity, mock_zone):

    mp_entity.select_sound_mode("Sound mode 2")
    assert mock_zone.soundprg == "Sound mode 2"
    assert mock_zone.straight == False
    assert mp_entity.sound_mode == "Sound mode 2"

    # Straight is special as it is a separate setting on the Zone
    mp_entity.select_sound_mode("Straight")
    assert mock_zone.soundprg == "Sound mode 2"
    assert mock_zone.straight == True
    assert mp_entity.sound_mode == "Straight"


async def test_mediaplayer_entity_sound_mode_list(mp_entity, mock_zone):

    mock_zone.straight = False
    assert "Straight" in mp_entity.sound_mode_list

    mock_zone.straight = None
    assert not "Straight" in mp_entity.sound_mode_list

    mock_zone.soundprg = None
    assert mp_entity.sound_mode_list is None

    mock_zone.soundprg = "DspSoundProgram"
    assert mp_entity.sound_mode_list == sorted(ynca.SoundPrg)


@patch(
    "ynca.get_modelinfo",
    return_value=ynca.modelinfo.ModelInfo(soundprg=[ynca.SoundPrg.ALL_CH_STEREO]),
)
async def test_mediaplayer_entity_sound_mode_list_from_modelinfo(
    patched_get_modelinfo, mp_entity, mock_zone
):

    mock_zone.soundprg = "DspSoundProgram"
    assert "All-Ch Stereo" in mp_entity.sound_mode_list


@patch(
    "ynca.get_inputinfo_list",
    return_value=[
        ynca.InputInfo(ynca.Subunit.USB, "USB", "USB"),
        ynca.InputInfo(ynca.Subunit.NETRADIO, "NET RADIO", "NET RADIO"),
    ],
)
async def test_mediaplayer_entity_supported_features(
    patched_get_inputinfo_list, mp_entity, mock_zone, mock_ynca
):

    expected_supported_features = (
        MediaPlayerEntityFeature.VOLUME_SET
        | MediaPlayerEntityFeature.VOLUME_MUTE
        | MediaPlayerEntityFeature.VOLUME_STEP
        | MediaPlayerEntityFeature.TURN_ON
        | MediaPlayerEntityFeature.TURN_OFF
        | MediaPlayerEntityFeature.SELECT_SOURCE
    )

    mock_zone.soundprg = None
    assert mp_entity.supported_features == expected_supported_features

    mock_zone.soundprg = "DspSoundProgram"
    expected_supported_features |= MediaPlayerEntityFeature.SELECT_SOUND_MODE
    assert mp_entity.supported_features == expected_supported_features

    # Sources with `playback` attribute support playback controls

    # Radio sources only support play and stop
    mock_ynca.NETRADIO = create_autospec(
        ynca.netradio.NetRadio, id=ynca.Subunit.NETRADIO
    )
    mock_zone.input = "NET RADIO"
    expected_supported_features |= MediaPlayerEntityFeature.PLAY
    expected_supported_features |= MediaPlayerEntityFeature.STOP
    assert mp_entity.supported_features == expected_supported_features

    # Other sources also support pausem previous, next
    mock_ynca.USB = create_autospec(
        ynca.mediaplayback_subunits.Usb, id=ynca.Subunit.USB
    )
    mock_zone.input = "USB"
    expected_supported_features |= MediaPlayerEntityFeature.PAUSE
    expected_supported_features |= MediaPlayerEntityFeature.PREVIOUS_TRACK
    expected_supported_features |= MediaPlayerEntityFeature.NEXT_TRACK
    # USB also supports repeat and shuffle
    expected_supported_features |= MediaPlayerEntityFeature.REPEAT_SET
    expected_supported_features |= MediaPlayerEntityFeature.SHUFFLE_SET

    assert mp_entity.supported_features == expected_supported_features


@patch(
    "ynca.get_inputinfo_list",
    return_value=[
        ynca.InputInfo(ynca.Subunit.USB, "USB", "USB"),
    ],
)
async def test_mediaplayer_entity_state(
    patched_get_inputinfo_list, mp_entity, mock_zone, mock_ynca
):

    mock_zone.pwr = False
    assert mp_entity.state == STATE_OFF

    mock_zone.pwr = True
    assert mp_entity.state == STATE_ON

    mock_zone.input = "USB"
    mock_ynca.USB = create_autospec(
        ynca.mediaplayback_subunits.Usb, id=ynca.Subunit.USB
    )

    mock_ynca.USB.playbackinfo = ynca.PlaybackInfo.PLAY
    assert mp_entity.state == STATE_PLAYING

    mock_ynca.USB.playbackinfo = ynca.PlaybackInfo.PAUSE
    assert mp_entity.state == STATE_PAUSED

    mock_ynca.USB.playbackinfo = ynca.PlaybackInfo.STOP
    assert mp_entity.state == STATE_IDLE


async def test_mediaplayer_playback_controls(mp_entity, mock_zone):
    mp_entity.media_play()
    mock_zone.playback.assert_called_with(ynca.Playback.PLAY)
    mp_entity.media_pause()
    mock_zone.playback.assert_called_with(ynca.Playback.PAUSE)
    mp_entity.media_stop()
    mock_zone.playback.assert_called_with(ynca.Playback.STOP)
    mp_entity.media_next_track()
    mock_zone.playback.assert_called_with(ynca.Playback.SKIP_FWD)
    mp_entity.media_previous_track()
    mock_zone.playback.assert_called_with(ynca.Playback.SKIP_REV)


@patch(
    "ynca.get_inputinfo_list",
    return_value=[
        ynca.InputInfo(ynca.Subunit.USB, "USB", "USB"),
        ynca.InputInfo(ynca.Subunit.NETRADIO, "NET RADIO", "NET RADIO"),
        ynca.InputInfo(ynca.Subunit.TUN, "TUNER", "TUNER"),
        ynca.InputInfo(
            ynca.Subunit.SIRIUSIR, "SIRIUS InternetRadio", "SIRIUS InternetRadio"
        ),
    ],
)
async def test_mediaplayer_mediainfo(
    patched_get_inputinfo_list, mp_entity, mock_zone, mock_ynca
):

    assert mp_entity.media_album_name is None
    assert mp_entity.media_artist is None
    assert mp_entity.media_title is None
    assert mp_entity.media_channel is None
    assert mp_entity.media_content_type is None

    # Some subunits support Music with Artist, Album, Song
    mock_zone.input = "USB"
    mock_ynca.USB = create_autospec(
        ynca.mediaplayback_subunits.Usb, id=ynca.Subunit.USB
    )

    mock_ynca.USB.album = "AlbumName"
    mock_ynca.USB.artist = "ArtistName"
    mock_ynca.USB.song = "Title"
    assert mp_entity.media_album_name == "AlbumName"
    assert mp_entity.media_artist == "ArtistName"
    assert mp_entity.media_title == "Title"
    assert mp_entity.media_content_type is MEDIA_TYPE_MUSIC

    # Netradio is a "channel" which name is exposed by the "station" attribute
    mock_zone.input = "NET RADIO"
    mock_ynca.NETRADIO = create_autospec(
        ynca.netradio.NetRadio, id=ynca.Subunit.NETRADIO
    )
    mock_ynca.NETRADIO.station = "StationName"
    assert mp_entity.media_channel == "StationName"
    assert mp_entity.media_content_type is MEDIA_TYPE_CHANNEL

    # Tuner (analog radio) is a "channel"
    # There is no station name, so build name from band and frequency
    mock_zone.input = "TUNER"
    mock_ynca.TUN = create_autospec(ynca.tun.Tun, id=ynca.Subunit.TUN)
    mock_ynca.TUN.band = ynca.Band.FM
    mock_ynca.TUN.fmfreq = 123.45
    assert mp_entity.media_channel == "FM 123.45 MHz"
    assert mp_entity.media_content_type is MEDIA_TYPE_CHANNEL

    mock_ynca.TUN.band = ynca.Band.AM
    mock_ynca.TUN.amfreq = 1234
    assert mp_entity.media_channel == "AM 1234 kHz"
    assert mp_entity.media_content_type is MEDIA_TYPE_CHANNEL

    # Sirius subunits expose name by the "chname" attribute
    mock_zone.input = "SIRIUS InternetRadio"
    mock_ynca.SIRIUSIR = create_autospec(ynca.sirius.SiriusIr, id=ynca.Subunit.SIRIUSIR)
    mock_ynca.SIRIUSIR.chname = "ChannelName"
    assert mp_entity.media_channel == "ChannelName"
    assert mp_entity.media_content_type is MEDIA_TYPE_CHANNEL


@patch(
    "ynca.get_inputinfo_list",
    return_value=[
        ynca.InputInfo(ynca.Subunit.USB, "USB", "USB"),
        ynca.InputInfo(ynca.Subunit.NETRADIO, "NET RADIO", "NET RADIO"),
    ],
)
async def test_mediaplayer_entity_shuffle(
    patched_get_inputinfo_list, mp_entity, mock_zone, mock_ynca
):

    # Unsupported subunit selected
    assert mp_entity.shuffle == None

    # Subunit supporting shuffle
    mock_zone.input = "USB"
    mock_ynca.USB = create_autospec(
        ynca.mediaplayback_subunits.Usb, id=ynca.Subunit.USB
    )

    mp_entity.set_shuffle(True)
    assert mock_ynca.USB.shuffle == True
    assert mp_entity.shuffle == True

    mp_entity.set_shuffle(False)
    assert mock_ynca.USB.shuffle == False
    assert mp_entity.shuffle == False

    # Subunit not supporting shuffle
    mock_zone.input = "NET RADIO"
    mock_ynca.NETRADIO = create_autospec(
        ynca.netradio.NetRadio, id=ynca.Subunit.NETRADIO
    )
    assert mp_entity.shuffle == None


@patch(
    "ynca.get_inputinfo_list",
    return_value=[
        ynca.InputInfo(ynca.Subunit.USB, "USB", "USB"),
        ynca.InputInfo(ynca.Subunit.NETRADIO, "NET RADIO", "NET RADIO"),
    ],
)
async def test_mediaplayer_entity_repeat(
    patched_get_inputinfo_list, mp_entity, mock_zone, mock_ynca
):

    # Unsupported subunit selected
    assert mp_entity.repeat == None

    # Subunit supporting repeat
    mock_zone.input = "USB"
    mock_ynca.USB = create_autospec(
        ynca.mediaplayback_subunits.Usb, id=ynca.Subunit.USB
    )

    mp_entity.set_repeat(REPEAT_MODE_OFF)
    assert mock_ynca.USB.repeat == ynca.Repeat.OFF
    assert mp_entity.repeat == REPEAT_MODE_OFF

    mp_entity.set_repeat(REPEAT_MODE_ONE)
    assert mock_ynca.USB.repeat == ynca.Repeat.SINGLE
    assert mp_entity.repeat == REPEAT_MODE_ONE

    mp_entity.set_repeat(REPEAT_MODE_ALL)
    assert mock_ynca.USB.repeat == ynca.Repeat.ALL
    assert mp_entity.repeat == REPEAT_MODE_ALL

    # Subunit not supporting shuffle
    mock_zone.input = "NET RADIO"
    mock_ynca.NETRADIO = create_autospec(
        ynca.netradio.NetRadio, id=ynca.Subunit.NETRADIO
    )
    assert mp_entity.repeat == None
