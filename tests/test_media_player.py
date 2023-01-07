"""Test the Yamaha (YNCA) config flow."""
from __future__ import annotations

from unittest.mock import Mock, call, create_autospec, patch

import pytest
import ynca

import custom_components.yamaha_ynca as yamaha_ynca
from custom_components.yamaha_ynca.media_player import YamahaYncaZone, async_setup_entry
from homeassistant.components.media_player import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    RepeatMode,
)

from tests.conftest import setup_integration


@pytest.fixture
def mp_entity(mock_zone, mock_ynca) -> YamahaYncaZone:
    return YamahaYncaZone("ReceiverUniqueId", mock_ynca, mock_zone, [], [])


@patch("custom_components.yamaha_ynca.media_player.YamahaYncaZone", autospec=True)
async def test_async_setup_entry(
    yamahayncazone_mock, hass, mock_ynca, mock_zone_main, mock_zone_zone2
):

    mock_ynca.main = mock_zone_main
    mock_ynca.zone2 = mock_zone_zone2

    integration = await setup_integration(hass, mock_ynca)
    integration.entry.options = {
        "hidden_sound_modes": ["Adventure"],
        "MAIN": {"hidden_inputs": ["Airplay"]},
    }
    add_entities_mock = Mock()

    await async_setup_entry(hass, integration.entry, add_entities_mock)

    yamahayncazone_mock.assert_has_calls(
        [
            call("entry_id", mock_ynca, mock_ynca.main, ["Airplay"], ["Adventure"]),
            call("entry_id", mock_ynca, mock_ynca.zone2, [], ["Adventure"]),
        ]
    )

    add_entities_mock.assert_called_once()
    entities = add_entities_mock.call_args.args[0]
    assert len(entities) == 2


async def test_mediaplayer_entity(mp_entity, mock_zone, mock_ynca):
    mock_ynca.netradio = create_autospec(ynca.subunits.netradio.NetRadio)

    assert mp_entity.unique_id == "ReceiverUniqueId_ZoneId"
    assert mp_entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId_ZoneId")
    }

    # Name should return None since it is the main feature and will get the device name
    assert mp_entity.name is None

    await mp_entity.async_added_to_hass()
    mock_zone.register_update_callback.assert_called_once()
    mock_ynca.netradio.register_update_callback.assert_called_once()

    zone_callback = mock_zone.register_update_callback.call_args.args[0]
    netradio_callback = mock_ynca.netradio.register_update_callback.call_args.args[0]
    mp_entity.schedule_update_ha_state = Mock()

    zone_callback("FUNCTION", "VALUE")
    mp_entity.schedule_update_ha_state.call_count == 1

    netradio_callback("FUNCTION", "VALUE")
    mp_entity.schedule_update_ha_state.call_count == 2

    await mp_entity.async_will_remove_from_hass()
    mock_zone.unregister_update_callback.assert_called_once_with(zone_callback)
    mock_ynca.netradio.unregister_update_callback.assert_called_once_with(
        netradio_callback
    )


async def test_mediaplayer_entity_name(
    mp_entity,
    mock_zone,
):
    assert mp_entity.name is None
    mock_zone.zonename = None
    assert mp_entity.name is None


async def test_mediaplayer_entity_turn_on_off(
    mp_entity: YamahaYncaZone,
    mock_zone,
):
    mp_entity.turn_on()
    assert mock_zone.pwr is ynca.Pwr.ON
    assert mp_entity.state is MediaPlayerState.IDLE

    mp_entity.turn_off()
    assert mock_zone.pwr is ynca.Pwr.STANDBY
    assert mp_entity.state is MediaPlayerState.OFF


async def test_mediaplayer_entity_mute_volume(mp_entity, mock_zone):

    mp_entity.mute_volume(True)
    assert mock_zone.mute is ynca.Mute.ON
    assert mp_entity.is_volume_muted == True

    mp_entity.mute_volume(False)
    assert mock_zone.mute is ynca.Mute.OFF
    assert mp_entity.is_volume_muted == False

    # No mute support
    mock_zone.mute = None
    assert mp_entity.is_volume_muted == None


async def test_mediaplayer_entity_volume_set_up_down(mp_entity, mock_zone):

    mock_zone.maxvol = 10

    mp_entity.set_volume_level(1)
    assert mock_zone.vol == 10
    assert mp_entity.volume_level == 1

    # Check if scaling takes maxvol into account
    mock_zone.maxvol = 0
    mp_entity.set_volume_level(1)
    assert mock_zone.vol == 0
    assert mp_entity.volume_level == 1

    # Check if scaling takes max when maxvol not available
    mock_zone.maxvol = None
    mp_entity.set_volume_level(1)
    assert mock_zone.vol == 16.5
    assert mp_entity.volume_level == 1

    mp_entity.set_volume_level(0)
    assert mock_zone.vol == -80.5
    assert mp_entity.volume_level == 0

    mp_entity.volume_up()
    assert mock_zone.vol_up.call_count == 1

    mp_entity.volume_down()
    assert mock_zone.vol_down.call_count == 1

    # No vol support
    mock_zone.vol = None
    assert mp_entity.volume_level == None


async def test_mediaplayer_entity_source(mock_zone, mock_ynca):

    mock_ynca.netradio = create_autospec(ynca.subunits.netradio.NetRadio)
    mock_ynca.tun = create_autospec(ynca.subunits.tun.Tun)
    mock_ynca.sys.inpnamehdmi4 = "Input HDMI 4"

    mp_entity = YamahaYncaZone("ReceiverUniqueId", mock_ynca, mock_zone, ["TUNER"], [])

    # Select a rename-able source
    mp_entity.select_source("Input HDMI 4")
    assert mock_zone.inp is ynca.Input.HDMI4
    assert mp_entity.source == "Input HDMI 4"

    # Select a source that maps to built in subunit
    mp_entity.select_source("NET RADIO")
    assert mock_zone.inp is ynca.Input.NETRADIO
    assert mp_entity.source == "NET RADIO"

    # Invalid source does not change input
    mp_entity.select_source("invalid source")
    assert mock_zone.inp is ynca.Input.NETRADIO
    assert mp_entity.source == "NET RADIO"

    # Input without mapped name shows as Unknown
    mock_zone.inp = ynca.Input.SIRIUS
    assert mp_entity.source == "Unknown"

    # Hidden input is still shown when active input
    mock_zone.inp = ynca.Input.TUNER
    assert mp_entity.source == "TUNER"

    # Zone does not support input selection (just for robustness, not seen in the wild)
    mock_zone.inp = None
    assert mp_entity.source is None


async def test_mediaplayer_entity_source_list(mock_zone, mock_ynca):

    mock_ynca.tun = create_autospec(ynca.subunits.tun.Tun)
    mock_ynca.netradio = create_autospec(ynca.subunits.netradio.NetRadio)
    mock_ynca.sys.inpnamehdmi4 = "Input HDMI 4"

    # Tuner is hidden
    mp_entity = YamahaYncaZone("ReceiverUniqueId", mock_ynca, mock_zone, ["TUNER"], [])

    assert mp_entity.source_list == ["Input HDMI 4", "NET RADIO"]


async def test_mediaplayer_entity_sound_mode(mp_entity, mock_zone):

    mp_entity.select_sound_mode("Village Vanguard")
    assert mock_zone.soundprg is ynca.SoundPrg.VILLAGE_VANGUARD
    assert mock_zone.straight is ynca.Straight.OFF
    assert mp_entity.sound_mode == "Village Vanguard"

    # Straight is special as it is a separate setting on the Zone
    mp_entity.select_sound_mode("Straight")
    assert mock_zone.soundprg is ynca.SoundPrg.VILLAGE_VANGUARD
    assert mock_zone.straight is ynca.Straight.ON
    assert mp_entity.sound_mode == "Straight"


async def test_mediaplayer_entity_sound_mode_list(mp_entity, mock_zone):

    mock_zone.soundprg = ynca.SoundPrg.VILLAGE_VANGUARD
    mock_zone.straight = ynca.Straight.OFF
    assert "Straight" in mp_entity.sound_mode_list

    mock_zone.straight = None
    assert not "Straight" in mp_entity.sound_mode_list

    mock_zone.soundprg = None
    assert mp_entity.sound_mode_list is None

    mock_zone.soundprg = ynca.SoundPrg.CELLAR_CLUB
    assert mp_entity.sound_mode_list == sorted(
        [sp for sp in ynca.SoundPrg if sp is not ynca.SoundPrg.UNKNOWN]
    )


@patch(
    "ynca.YncaModelInfo.get",
    return_value=ynca.modelinfo.ModelInfo(soundprg=[ynca.SoundPrg.ALL_CH_STEREO]),
)
async def test_mediaplayer_entity_sound_mode_list_from_modelinfo(
    patched_YncaModelInfo_get, mp_entity, mock_zone
):

    mock_zone.soundprg = ynca.SoundPrg.MONO_MOVIE
    assert "All-Ch Stereo" in mp_entity.sound_mode_list


async def test_mediaplayer_entity_hidden_sound_mode(mock_ynca, mock_zone):

    mock_zone.soundprg = ynca.SoundPrg.VILLAGE_VANGUARD

    mp_entity = YamahaYncaZone(
        "ReceiverUniqueId", mock_ynca, mock_zone, [], ["MONO_MOVIE"]
    )

    assert "Drama" in mp_entity.sound_mode_list
    assert "Mono movie" not in mp_entity.sound_mode_list

    # Hidden soundmodes should still be shown if they are the current soundmode
    mock_zone.soundprg = ynca.SoundPrg.MONO_MOVIE
    assert mp_entity.sound_mode == "Mono Movie"


async def test_mediaplayer_entity_supported_features(mp_entity, mock_zone, mock_ynca):

    expected_supported_features = 0

    # Nothing supported
    mock_zone.pwr = None
    mock_zone.vol = None
    mock_zone.mute = None
    mock_zone.inp = None
    mock_zone.soundprg = None
    assert mp_entity.supported_features == expected_supported_features

    mock_zone.pwr = ynca.Pwr.STANDBY
    expected_supported_features |= MediaPlayerEntityFeature.TURN_ON
    expected_supported_features |= MediaPlayerEntityFeature.TURN_OFF
    assert mp_entity.supported_features == expected_supported_features

    mock_zone.vol = 12
    expected_supported_features |= MediaPlayerEntityFeature.VOLUME_SET
    expected_supported_features |= MediaPlayerEntityFeature.VOLUME_STEP
    assert mp_entity.supported_features == expected_supported_features

    mock_zone.mute = ynca.Mute.ATT_MINUS_20
    expected_supported_features |= MediaPlayerEntityFeature.VOLUME_MUTE
    assert mp_entity.supported_features == expected_supported_features

    mock_zone.inp = ynca.Input.MULTICH
    expected_supported_features |= MediaPlayerEntityFeature.SELECT_SOURCE
    assert mp_entity.supported_features == expected_supported_features

    mock_zone.soundprg = ynca.SoundPrg.ACTION_GAME
    expected_supported_features |= MediaPlayerEntityFeature.SELECT_SOUND_MODE
    assert mp_entity.supported_features == expected_supported_features

    # Sources with `playback` attribute support playback controls

    # Radio sources only support play and stop
    mock_ynca.netradio = create_autospec(ynca.subunits.netradio.NetRadio)
    mock_zone.inp = ynca.Input.NETRADIO
    expected_supported_features |= MediaPlayerEntityFeature.PLAY
    expected_supported_features |= MediaPlayerEntityFeature.STOP
    assert mp_entity.supported_features == expected_supported_features

    # Other sources support pause, previous, next
    # Repeat/shuffle capability depends on availability of repeat/shuffle attributes on YNCA subunit
    mock_ynca.spotify = create_autospec(ynca.subunits.spotify.Spotify)
    mock_ynca.spotify.repeat = None
    mock_ynca.spotify.shuffle = None
    mock_zone.inp = ynca.Input.SPOTIFY
    expected_supported_features |= MediaPlayerEntityFeature.PAUSE
    expected_supported_features |= MediaPlayerEntityFeature.PREVIOUS_TRACK
    expected_supported_features |= MediaPlayerEntityFeature.NEXT_TRACK
    assert mp_entity.supported_features == expected_supported_features

    # USB also supports repeat and shuffle
    mock_ynca.usb = create_autospec(ynca.subunits.usb.Usb)
    mock_zone.inp = ynca.Input.USB
    expected_supported_features |= MediaPlayerEntityFeature.REPEAT_SET
    expected_supported_features |= MediaPlayerEntityFeature.SHUFFLE_SET
    assert mp_entity.supported_features == expected_supported_features


async def test_mediaplayer_entity_state(mp_entity, mock_zone, mock_ynca):

    mock_zone.pwr = ynca.Pwr.STANDBY
    assert mp_entity.state is MediaPlayerState.OFF

    mock_zone.pwr = ynca.Pwr.ON
    assert mp_entity.state is MediaPlayerState.IDLE

    mock_zone.inp = ynca.Input.USB
    mock_ynca.usb = create_autospec(ynca.subunits.usb.Usb)

    mock_ynca.usb.playbackinfo = ynca.PlaybackInfo.PLAY
    assert mp_entity.state is MediaPlayerState.PLAYING

    mock_ynca.usb.playbackinfo = ynca.PlaybackInfo.PAUSE
    assert mp_entity.state is MediaPlayerState.PAUSED

    mock_ynca.usb.playbackinfo = ynca.PlaybackInfo.STOP
    assert mp_entity.state is MediaPlayerState.IDLE


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


async def test_mediaplayer_mediainfo(mp_entity, mock_zone, mock_ynca):

    assert mp_entity.media_album_name is None
    assert mp_entity.media_artist is None
    assert mp_entity.media_title is None
    assert mp_entity.media_channel is None
    assert mp_entity.media_content_type is None

    # Some subunits support Music with Artist, Album, Song
    mock_zone.inp = ynca.Input.USB
    mock_ynca.usb = create_autospec(ynca.subunits.usb.Usb)

    mock_ynca.usb.album = "AlbumName"
    mock_ynca.usb.artist = "ArtistName"
    mock_ynca.usb.song = "Title"
    assert mp_entity.media_album_name == "AlbumName"
    assert mp_entity.media_artist == "ArtistName"
    assert mp_entity.media_title == "Title"
    assert mp_entity.media_content_type is MediaType.MUSIC

    # Netradio is a "channel" which name is exposed by the "station" attribute
    mock_zone.inp = ynca.Input.NETRADIO
    mock_ynca.netradio = create_autospec(ynca.subunits.netradio.NetRadio)
    mock_ynca.netradio.station = "StationName"
    assert mp_entity.media_title is None
    assert mp_entity.media_channel == "StationName"
    assert mp_entity.media_content_type is MediaType.CHANNEL

    # Tuner (AM/FM analog radio) is a "channel"
    mock_zone.inp = ynca.Input.TUNER
    mock_ynca.tun = create_autospec(ynca.subunits.tun.Tun)

    # AM has no station name, so name is built from band and frequency
    mock_ynca.tun.band = ynca.BandTun.AM
    mock_ynca.tun.amfreq = 1234
    assert mp_entity.media_title is None
    assert mp_entity.media_channel == "AM 1234 kHz"
    assert mp_entity.media_content_type is MediaType.CHANNEL

    # FM can have name from RDS info or falls back to band and frequency
    mock_ynca.tun.band = ynca.BandTun.FM
    mock_ynca.tun.fmfreq = 123.45
    mock_ynca.tun.rdsprgservice = None
    assert mp_entity.media_title is None
    assert mp_entity.media_channel == "FM 123.45 MHz"
    assert mp_entity.media_content_type is MediaType.CHANNEL

    mock_ynca.tun.rdsprgservice = "RDS PRG SERVICE"
    assert mp_entity.media_title is None
    assert mp_entity.media_channel == "RDS PRG SERVICE"
    assert mp_entity.media_content_type is MediaType.CHANNEL

    # Tuner (DAB/FM radio) is a "channel"
    mock_zone.inp = ynca.Input.TUNER
    mock_ynca.dab = create_autospec(ynca.subunits.dab.Dab)
    mock_ynca.tun = None  # Unit has either tun or dab, not both

    # DAB FM can have name from RDS info or falls back to band and frequency
    mock_ynca.dab.band = ynca.BandDab.FM
    mock_ynca.dab.fmfreq = 123.45
    mock_ynca.dab.fmrdsprgservice = None
    assert mp_entity.media_title is None
    assert mp_entity.media_channel == "FM 123.45 MHz"
    assert mp_entity.media_content_type is MediaType.CHANNEL

    mock_ynca.dab.fmrdsprgservice = "FM RDS PRG SERVICE"
    assert mp_entity.media_title is None
    assert mp_entity.media_channel == "FM RDS PRG SERVICE"
    assert mp_entity.media_content_type is MediaType.CHANNEL

    # DAB (digital) gets name from servicelabel
    mock_ynca.dab.band = ynca.BandDab.DAB
    mock_ynca.dab.dabservicelabel = "DAB SERVICE LABEL"
    mock_ynca.dab.dabdlslabel = "DAB DLS LABEL"
    assert mp_entity.media_title == "DAB DLS LABEL"
    assert mp_entity.media_channel == "DAB SERVICE LABEL"
    assert mp_entity.media_content_type is MediaType.CHANNEL

    # Sirius subunits expose name by the "chname" attribute
    mock_zone.inp = ynca.Input.SIRIUS_IR
    mock_ynca.siriusir = create_autospec(ynca.subunits.sirius.SiriusIr)
    mock_ynca.siriusir.chname = "ChannelName"
    mock_ynca.siriusir.song = "SiriusIrSongName"
    assert mp_entity.media_title == "SiriusIrSongName"
    assert mp_entity.media_channel == "ChannelName"
    assert mp_entity.media_content_type is MediaType.CHANNEL


async def test_mediaplayer_entity_shuffle(mp_entity, mock_zone, mock_ynca):

    # Unsupported subunit selected
    assert mp_entity.shuffle is None

    # Subunit supporting shuffle
    mock_zone.inp = ynca.Input.USB
    mock_ynca.usb = create_autospec(ynca.subunits.usb.Usb)

    mp_entity.set_shuffle(True)
    assert mock_ynca.usb.shuffle is ynca.Shuffle.ON
    assert mp_entity.shuffle == True

    mp_entity.set_shuffle(False)
    assert mock_ynca.usb.shuffle is ynca.Shuffle.OFF
    assert mp_entity.shuffle == False

    # Subunit not supporting shuffle
    mock_zone.inp = ynca.Input.NETRADIO
    mock_ynca.netradio = create_autospec(ynca.subunits.netradio.NetRadio)
    assert mp_entity.shuffle is None


async def test_mediaplayer_entity_repeat(mp_entity, mock_zone, mock_ynca):

    # Unsupported subunit selected
    assert mp_entity.repeat is None

    # Subunit supporting repeat
    mock_zone.inp = ynca.Input.USB
    mock_ynca.usb = create_autospec(ynca.subunits.usb.Usb)

    mp_entity.set_repeat(RepeatMode.OFF)
    assert mock_ynca.usb.repeat is ynca.Repeat.OFF
    assert mp_entity.repeat is RepeatMode.OFF

    mp_entity.set_repeat(RepeatMode.ONE)
    assert mock_ynca.usb.repeat is ynca.Repeat.SINGLE
    assert mp_entity.repeat is RepeatMode.ONE

    mp_entity.set_repeat(RepeatMode.ALL)
    assert mock_ynca.usb.repeat is ynca.Repeat.ALL
    assert mp_entity.repeat is RepeatMode.ALL

    # Subunit not supporting repeat
    mock_zone.inp = ynca.Input.NETRADIO
    mock_ynca.NETRADIO = create_autospec(ynca.subunits.netradio.NetRadio)
    assert mp_entity.repeat is None
