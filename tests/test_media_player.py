"""Test the Yamaha (YNCA) media_player entitity."""

from __future__ import annotations

import logging
from unittest.mock import Mock, create_autospec, patch

from homeassistant.components.media_player import (
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    RepeatMode,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_unordered import unordered

from custom_components import yamaha_ynca
from custom_components.yamaha_ynca.media_player import (
    YamahaYncaZone,
    YamahaYncaZoneB,
)
from tests.conftest import setup_integration
import ynca


@pytest.fixture
def mp_entity(mock_zone, mock_ynca) -> YamahaYncaZone:
    return YamahaYncaZone("ReceiverUniqueId", mock_ynca, mock_zone, [], [])


@pytest.fixture
def mp_entity_zoneb(mock_ynca, mock_zone_main_with_zoneb) -> YamahaYncaZoneB:
    mock_ynca.main = mock_zone_main_with_zoneb
    return YamahaYncaZoneB("ReceiverUniqueId", mock_ynca, [])


async def test_mediaplayer_entity(mp_entity: YamahaYncaZone, mock_zone, mock_ynca):
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


async def test_mediaplayer_entity_default_entity_name(
    mock_zone_main_with_zoneb, mock_ynca, hass, device_reg
):
    # Setup integration, device registry and entity
    mock_ynca.main = mock_zone_main_with_zoneb
    await setup_integration(hass, mock_ynca)
    reg = er.async_get(hass)

    entity_id = reg.async_get_entity_id(
        "media_player", yamaha_ynca.DOMAIN, "entry_id_MAIN"
    )
    assert entity_id == "media_player.modelname_main"

    entity_id = reg.async_get_entity_id(
        "media_player", yamaha_ynca.DOMAIN, "entry_id_ZONEB"
    )
    assert entity_id == "media_player.modelname_zoneb"


async def test_mediaplayer_entity_update_callback_zonename(
    mock_zone, mock_ynca, hass, device_reg
):
    # Setup integration, device registry and entity
    mock_ynca.main = mock_zone
    integration = await setup_integration(hass, mock_ynca)

    device_reg.async_get_or_create(
        config_entry_id=integration.entry.entry_id,
        identifiers={(yamaha_ynca.DOMAIN, "ReceiverUniqueId_ZoneId")},
        name="Old Zonename",
    )

    zone_entity = YamahaYncaZone("ReceiverUniqueId", mock_ynca, mock_zone, [], [])
    assert zone_entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId_ZoneId")
    }

    zone_entity.hass = hass  # In a real system this is done by HA
    await zone_entity.async_added_to_hass()

    zone_callback = mock_zone.register_update_callback.call_args.args[0]
    zone_entity.schedule_update_ha_state = Mock()

    # Zonename update
    mock_zone.zonename = "New Zonename"
    zone_callback("ZONENAME", "VALUE")  # Note VALUE is not used it is read from API
    assert zone_entity.schedule_update_ha_state.call_count == 1

    # Check for name change
    device_entry = device_reg.async_get_or_create(
        config_entry_id=integration.entry.entry_id,
        identifiers={(yamaha_ynca.DOMAIN, "ReceiverUniqueId_ZoneId")},
    )
    assert device_entry.name == "New Zonename"


async def test_mediaplayer_entity_update_callback_zonebname(
    mock_zone_main_with_zoneb, mock_ynca, hass, device_reg
):
    # Setup integration, device registry and entity
    mock_ynca.main = mock_zone_main_with_zoneb
    integration = await setup_integration(hass, mock_ynca)

    device_reg.async_get_or_create(
        config_entry_id=integration.entry.entry_id,
        identifiers={(yamaha_ynca.DOMAIN, "ReceiverUniqueId_ZONEB")},
        name="Old ZoneBname",
    )

    zoneb_entity = YamahaYncaZoneB("ReceiverUniqueId", mock_ynca, [])
    assert zoneb_entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId_ZONEB")
    }

    zoneb_entity.hass = hass  # In a real system this is done by HA
    await zoneb_entity.async_added_to_hass()

    zone_callback = mock_zone_main_with_zoneb.register_update_callback.call_args.args[0]
    zoneb_entity.schedule_update_ha_state = Mock()

    # Zonename update
    mock_zone_main_with_zoneb.zonebname = "New ZoneBname"
    zone_callback("ZONEBNAME", "VALUE")  # Note VALUE is not used it is read from API
    assert zoneb_entity.schedule_update_ha_state.call_count == 1

    # Check for name change
    device_entry = device_reg.async_get_or_create(
        config_entry_id=integration.entry.entry_id,
        identifiers={(yamaha_ynca.DOMAIN, "ReceiverUniqueId_ZONEB")},
    )
    assert device_entry.name == "New ZoneBname"


async def test_mediaplayer_entity_turn_on_off(
    mp_entity,
    mock_zone,
):
    mp_entity.turn_on()
    assert mock_zone.pwr is ynca.Pwr.ON
    assert mp_entity.state is MediaPlayerState.IDLE

    mp_entity.turn_off()
    assert mock_zone.pwr is ynca.Pwr.STANDBY
    assert mp_entity.state is MediaPlayerState.OFF


async def test_mediaplayer_entity_zoneb_turn_on_off(
    mp_entity_zoneb,
    mock_zone_main_with_zoneb,
):
    mp_entity_zoneb.turn_on()
    assert mock_zone_main_with_zoneb.pwrb is ynca.PwrB.ON
    assert mp_entity_zoneb.state is MediaPlayerState.IDLE

    mp_entity_zoneb.turn_off()
    assert mock_zone_main_with_zoneb.pwrb is ynca.PwrB.STANDBY
    assert mp_entity_zoneb.state is MediaPlayerState.OFF


async def test_mediaplayer_entity_mute_volume(mp_entity, mock_zone):
    mp_entity.mute_volume(True)
    assert mock_zone.mute is ynca.Mute.ON
    assert mp_entity.is_volume_muted is True

    mp_entity.mute_volume(False)
    assert mock_zone.mute is ynca.Mute.OFF
    assert mp_entity.is_volume_muted is False

    # No mute support
    mock_zone.mute = None
    assert mp_entity.is_volume_muted is None


async def test_mediaplayer_entity_zoneb_mute_volume(
    mp_entity_zoneb, mock_zone_main_with_zoneb
):
    mp_entity_zoneb.mute_volume(True)
    assert mock_zone_main_with_zoneb.zonebmute is ynca.ZoneBMute.ON
    assert mp_entity_zoneb.is_volume_muted is True

    mp_entity_zoneb.mute_volume(False)
    assert mock_zone_main_with_zoneb.zonebmute is ynca.ZoneBMute.OFF
    assert mp_entity_zoneb.is_volume_muted is False

    # No mute support
    mock_zone_main_with_zoneb.zonebmute = None
    assert mp_entity_zoneb.is_volume_muted is None


async def test_mediaplayer_entity_volume_set_up_down(
    mp_entity: YamahaYncaZone, mock_zone
):
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
    assert mp_entity.volume_level is None


async def test_mediaplayer_entity_zoneb_volume_set_up_down(
    mp_entity_zoneb, mock_zone_main_with_zoneb
):
    mp_entity_zoneb.set_volume_level(1)
    assert mock_zone_main_with_zoneb.zonebvol == 16.5
    assert mp_entity_zoneb.volume_level == 1

    mp_entity_zoneb.set_volume_level(0)
    assert mock_zone_main_with_zoneb.zonebvol == -80.5
    assert mp_entity_zoneb.volume_level == 0

    mp_entity_zoneb.volume_up()
    assert mock_zone_main_with_zoneb.zonebvol_up.call_count == 1

    mp_entity_zoneb.volume_down()
    assert mock_zone_main_with_zoneb.zonebvol_down.call_count == 1

    # No vol support
    mock_zone_main_with_zoneb.zonebvol = None
    assert mp_entity_zoneb.volume_level is None


async def test_mediaplayer_entity_source(hass, mock_zone, mock_ynca):
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


async def test_mediaplayer_entity_source_list(hass, mock_zone, mock_ynca):
    mock_ynca.tun = create_autospec(ynca.subunits.tun.Tun)
    mock_ynca.netradio = create_autospec(ynca.subunits.netradio.NetRadio)
    mock_ynca.sys.inpnamehdmi4 = "Input HDMI 4"

    # Tuner is hidden
    mp_entity = YamahaYncaZone("ReceiverUniqueId", mock_ynca, mock_zone, ["TUNER"], [])

    assert mp_entity.source_list == ["Input HDMI 4", "NET RADIO"]


async def test_mediaplayer_entity_source_whitespace_handling(
    hass, mock_zone, mock_ynca
):
    mock_ynca.sys.inpnamehdmi1 = "No spaces"
    mock_ynca.sys.inpnamehdmi2 = "   Leading spaces"
    mock_ynca.sys.inpnamehdmi3 = "Trailing spaces   "
    mock_ynca.sys.inpnamehdmi4 = "   Leading and trailing spaces   "

    mp_entity = YamahaYncaZone("ReceiverUniqueId", mock_ynca, mock_zone, [], [])

    assert mp_entity.source_list == unordered(
        [
            "No spaces",
            "Leading spaces",
            "Trailing spaces",
            "Leading and trailing spaces",
        ]
    )

    # Trim whitespaces when setting source
    mp_entity.select_source("  No spaces   ")
    assert mock_zone.inp is ynca.Input.HDMI1
    assert mp_entity.source == "No spaces"

    # Source with whitespace are trimmed
    mock_zone.inp = ynca.Input.HDMI2
    assert mp_entity.source == "Leading spaces"

    mock_zone.inp = ynca.Input.HDMI3
    assert mp_entity.source == "Trailing spaces"

    mock_zone.inp = ynca.Input.HDMI4
    assert mp_entity.source == "Leading and trailing spaces"


async def test_mediaplayer_entity_sound_mode(mp_entity: YamahaYncaZone, mock_zone):
    mock_zone.straight = ynca.Straight.OFF
    mock_zone.puredirmode = ynca.PureDirMode.OFF

    mp_entity.select_sound_mode("Village Vanguard")
    assert mock_zone.soundprg is ynca.SoundPrg.VILLAGE_VANGUARD
    assert mock_zone.straight is ynca.Straight.OFF
    assert mock_zone.puredirmode is ynca.PureDirMode.OFF
    assert mp_entity.sound_mode == "Village Vanguard"

    # Straight is special as it is a separate setting on the Zone
    mp_entity.select_sound_mode("Straight")
    assert mock_zone.soundprg is ynca.SoundPrg.VILLAGE_VANGUARD
    assert mock_zone.straight is ynca.Straight.ON
    assert mock_zone.puredirmode is ynca.PureDirMode.OFF
    assert mp_entity.sound_mode == "Straight"

    # Setting soundmode disables Pure Direct (since otherwise it the selected soundmode would be not audible)
    mock_zone.puredirmode = ynca.PureDirMode.ON

    mp_entity.select_sound_mode("Sports")
    assert mock_zone.soundprg is ynca.SoundPrg.SPORTS
    assert mock_zone.straight is ynca.Straight.OFF
    assert mock_zone.puredirmode is ynca.PureDirMode.OFF
    assert mp_entity.sound_mode == "Sports"


async def test_mediaplayer_entity_sound_mode_list(mp_entity: YamahaYncaZone, mock_zone):
    mock_zone.soundprg = ynca.SoundPrg.VILLAGE_VANGUARD
    mock_zone.straight = ynca.Straight.OFF
    assert "Straight" in mp_entity.sound_mode_list

    mock_zone.straight = None
    assert "Straight" not in mp_entity.sound_mode_list

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


async def test_mediaplayer_entity_hidden_sound_mode(hass, mock_ynca, mock_zone):
    mock_zone.soundprg = ynca.SoundPrg.VILLAGE_VANGUARD

    mp_entity = YamahaYncaZone(
        "ReceiverUniqueId", mock_ynca, mock_zone, [], ["MONO_MOVIE"]
    )

    assert "Drama" in mp_entity.sound_mode_list
    assert "Mono movie" not in mp_entity.sound_mode_list

    # Hidden soundmodes should still be shown if they are the current soundmode
    mock_zone.soundprg = ynca.SoundPrg.MONO_MOVIE
    assert mp_entity.sound_mode == "Mono Movie"


async def test_mediaplayer_entity_supported_features(
    mp_entity: YamahaYncaZone, mock_zone, mock_ynca
):
    expected_supported_features = (
        MediaPlayerEntityFeature.TURN_ON | MediaPlayerEntityFeature.TURN_OFF
    )

    # Nothing supported (still reports on/off)
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

    # Radio supports presets
    mock_ynca.dab = create_autospec(ynca.subunits.dab.Dab)
    mock_zone.inp = ynca.Input.TUNER
    expected_supported_features |= MediaPlayerEntityFeature.BROWSE_MEDIA
    expected_supported_features |= MediaPlayerEntityFeature.PLAY_MEDIA
    assert mp_entity.supported_features == expected_supported_features

    # Sources with `playback` attribute support playback controls

    # Internet radio sources support play and stop
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

    # USB also supports repeat and shuffle, but not pause (only stop)
    mock_ynca.usb = create_autospec(ynca.subunits.usb.Usb)
    mock_zone.inp = ynca.Input.USB
    expected_supported_features = (
        expected_supported_features & ~MediaPlayerEntityFeature.PAUSE
    )
    expected_supported_features |= MediaPlayerEntityFeature.REPEAT_SET
    expected_supported_features |= MediaPlayerEntityFeature.SHUFFLE_SET
    assert mp_entity.supported_features == expected_supported_features


async def test_mediaplayer_entity_state(
    mp_entity: YamahaYncaZone, mock_zone, mock_ynca
):
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


async def test_mediaplayer_mediainfo(mp_entity: YamahaYncaZone, mock_zone, mock_ynca):
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
    mock_ynca.usb.song = "Song title"
    assert mp_entity.media_album_name == "AlbumName"
    assert mp_entity.media_artist == "ArtistName"
    assert mp_entity.media_title == "Song title"
    assert mp_entity.media_content_type is MediaType.MUSIC

    # Spotify uses Track for song titles
    mock_zone.inp = ynca.Input.SPOTIFY
    mock_ynca.spotify = create_autospec(ynca.subunits.spotify.Spotify)
    mock_ynca.spotify.album = "AlbumName"
    mock_ynca.spotify.artist = "ArtistName"
    mock_ynca.spotify.track = "Track title"
    assert mp_entity.media_album_name == "AlbumName"
    assert mp_entity.media_artist == "ArtistName"
    assert mp_entity.media_title == "Track title"
    assert mp_entity.media_content_type is MediaType.MUSIC

    # Netradio is a "channel" which name is exposed by the "station" attribute
    mock_zone.inp = ynca.Input.NETRADIO
    mock_ynca.netradio = create_autospec(ynca.subunits.netradio.NetRadio)
    mock_ynca.netradio.station = "StationName"
    mock_ynca.netradio.song = "SongName"
    mock_ynca.netradio.album = "AlbumName"
    assert mp_entity.media_title == "SongName"
    assert mp_entity.media_channel == "StationName"
    assert mp_entity.media_album_name == "AlbumName"
    assert mp_entity.media_content_type is MediaType.CHANNEL

    # Tuner (AM/FM analog radio) is a "channel"
    mock_zone.inp = ynca.Input.TUNER
    mock_ynca.tun = create_autospec(ynca.subunits.tun.Tun)

    # AM has no station name, so name is built from band and frequency
    mock_ynca.tun.preset = None
    mock_ynca.tun.band = ynca.BandTun.AM
    mock_ynca.tun.amfreq = 1234
    assert mp_entity.media_title is None
    assert mp_entity.media_channel == "AM 1234 kHz"
    assert mp_entity.media_content_type is MediaType.CHANNEL

    # FM can have name from RDS info or falls back to band and frequency
    mock_ynca.tun.preset = None
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
    mock_ynca.dab.fmpreset = None
    assert mp_entity.media_title is None
    assert mp_entity.media_channel == "FM 123.45 MHz"
    assert mp_entity.media_content_type is MediaType.CHANNEL

    mock_ynca.dab.fmpreset = ynca.FmPreset.NO_PRESET
    assert mp_entity.media_channel == "FM 123.45 MHz"

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


async def test_mediaplayer_entity_shuffle(
    mp_entity: YamahaYncaZone, mock_zone, mock_ynca
):
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


async def test_mediaplayer_entity_repeat(
    mp_entity: YamahaYncaZone, mock_zone, mock_ynca
):
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


async def test_mediaplayer_entity_play_media_unsupported_media(
    mp_entity: YamahaYncaZone, mock_zone, mock_ynca
):
    mock_zone.inp = ynca.Input.USB
    mock_ynca.tun = create_autospec(ynca.subunits.tun.Tun)

    with pytest.raises(HomeAssistantError):
        # Mediasources not supported
        await mp_entity.async_play_media("media_type", "media-source://")

    with pytest.raises(HomeAssistantError):
        await mp_entity.async_play_media("media_type", "")

    with pytest.raises(HomeAssistantError):
        await mp_entity.async_play_media("media_type", "media_id")

    with pytest.raises(HomeAssistantError):
        await mp_entity.async_play_media("media_type", "tun:preset")  # Missing presetid

    with pytest.raises(HomeAssistantError):
        await mp_entity.async_play_media("media_type", "unsupported:preset:15")

    with pytest.raises(HomeAssistantError):
        await mp_entity.async_play_media("media_type", "tun:unsupported:15")

    # Out of range preset
    MIN_PRESET_ID = 1
    MAX_PRESET_ID = 40
    with pytest.raises(HomeAssistantError):
        await mp_entity.async_play_media(
            "media_type", f"tun:preset:{MIN_PRESET_ID - 1}"
        )
    with pytest.raises(HomeAssistantError):
        await mp_entity.async_play_media(
            "media_type", f"tun:preset:{MAX_PRESET_ID + 1}"
        )

    # Invalid input not handles and does not change state
    mock_zone.pwr = ynca.Pwr.STANDBY
    mock_zone.inp = ynca.Input.USB
    with pytest.raises(HomeAssistantError):
        await mp_entity.async_play_media("media_type", "invalid:preset:15")
    assert mock_zone.pwr is ynca.Pwr.STANDBY
    assert mock_zone.inp is ynca.Input.USB


async def test_mediaplayer_entity_play_media(mp_entity, mock_zone, mock_ynca):
    mock_zone.inp = ynca.Input.USB
    mock_ynca.tun = create_autospec(ynca.subunits.tun.Tun)
    mock_ynca.tun.id = ynca.subunit.Subunit.TUN

    # Different from after state
    mock_zone.pwr = ynca.Pwr.STANDBY
    mock_zone.inp = ynca.Input.USB
    mock_ynca.tun.preset = None

    await mp_entity.async_play_media("channel", "tun:preset:15")
    assert mock_zone.pwr is ynca.Pwr.ON
    assert mock_zone.inp is ynca.Input.TUNER
    assert mock_ynca.tun.preset == 15

    # DAB and TUN have the same input, so delete the TUN subunit
    mock_ynca.tun = None
    mock_ynca.dab = create_autospec(ynca.subunits.dab.Dab)
    mock_ynca.dab.id = ynca.subunit.Subunit.DAB
    mock_ynca.dab.dabpreset = ynca.DabPreset.NO_PRESET
    mock_ynca.dab.fmpreset = ynca.FmPreset.NO_PRESET

    await mp_entity.async_play_media("channel", "dab:dabpreset:16")
    assert mock_zone.pwr is ynca.Pwr.ON
    assert mock_zone.inp is ynca.Input.TUNER
    assert mock_ynca.dab.dabpreset == 16

    await mp_entity.async_play_media("channel", "dab:fmpreset:17")
    assert mock_zone.pwr is ynca.Pwr.ON
    assert mock_zone.inp is ynca.Input.TUNER
    assert mock_ynca.dab.fmpreset == 17


async def test_mediaplayer_entity_zoneb_play_media(
    mp_entity_zoneb, mock_zone_main_with_zoneb, mock_ynca
):
    mock_zone = mock_zone_main_with_zoneb

    mock_zone.inp = ynca.Input.TUNER
    mock_ynca.usb = create_autospec(ynca.subunits.usb.Usb)
    mock_ynca.usb.id = ynca.subunit.Subunit.USB

    # Different from after state
    mock_zone.pwrb = ynca.PwrB.STANDBY
    mock_zone.inp = ynca.Input.TUNER
    mock_ynca.usb.preset = None

    await mp_entity_zoneb.async_play_media("channel", "usb:preset:23")
    assert mock_zone.pwrb is ynca.PwrB.ON
    assert mock_zone.inp is ynca.Input.USB
    assert mock_ynca.usb.preset == 23


async def test_mediaplayer_entity_browse_media_unsupported_media(
    mp_entity: YamahaYncaZone, mock_zone, mock_ynca
):
    mock_zone.inp = ynca.Input.USB
    mock_ynca.tun = create_autospec(ynca.subunits.tun.Tun)

    with pytest.raises(HomeAssistantError):
        await mp_entity.async_browse_media("media_content_type", "media_content_id")


async def test_mediaplayer_entity_browse_media(mp_entity: YamahaYncaZone, mock_ynca):
    mock_ynca.tun = create_autospec(ynca.subunits.tun.Tun)
    mock_ynca.tun.id = ynca.subunit.Subunit.TUN

    # Root
    media = await mp_entity.async_browse_media(None, None)
    assert media.media_class == "directory"
    assert media.media_content_id == "presets"
    assert media.title == "Presets"
    assert media.can_expand is True
    assert media.can_play is False

    assert len(media.children) == 1
    assert media.children[0].media_class == "directory"
    assert media.children[0].media_content_id == "tun:presets"
    assert media.children[0].title == "TUNER"
    assert media.children[0].can_expand is True
    assert media.children[0].can_play is False

    # TUNER
    media = await mp_entity.async_browse_media(None, "tun:presets")
    assert media.media_class == "directory"
    assert media.media_content_id == "tun:presets"
    assert media.title == "TUNER"
    assert media.can_expand is True
    assert media.can_play is False

    assert len(media.children) == 40
    assert media.children[19].media_class == "music"
    assert media.children[19].media_content_id == "tun:preset:20"
    assert media.children[19].title == "Preset 20"
    assert media.children[19].can_expand is False
    assert media.children[19].can_play is True


async def test_mediaplayer_entity_browse_media_dab(
    mp_entity: YamahaYncaZone, mock_ynca
):
    mock_ynca.dab = create_autospec(ynca.subunits.dab.Dab)
    mock_ynca.dab.id = ynca.subunit.Subunit.DAB

    # Root
    media = await mp_entity.async_browse_media(None, None)
    assert media.media_class == "directory"
    assert media.media_content_id == "presets"
    assert media.title == "Presets"
    assert media.can_expand is True
    assert media.can_play is False

    assert len(media.children) == 2
    assert media.children[0].media_class == "directory"
    assert media.children[0].media_content_id == "dab:dabpresets"
    assert media.children[0].title == "TUNER (DAB)"
    assert media.children[0].can_expand is True
    assert media.children[0].can_play is False

    assert media.children[1].media_class == "directory"
    assert media.children[1].media_content_id == "dab:fmpresets"
    assert media.children[1].title == "TUNER (FM)"
    assert media.children[1].can_expand is True
    assert media.children[1].can_play is False

    # TUNER (DAB)
    media = await mp_entity.async_browse_media(None, "dab:dabpresets")
    assert media.media_class == "directory"
    assert media.media_content_id == "dab:dabpresets"
    assert media.title == "TUNER (DAB)"
    assert media.can_expand is True
    assert media.can_play is False

    assert len(media.children) == 40
    assert media.children[19].media_class == "music"
    assert media.children[19].media_content_id == "dab:dabpreset:20"
    assert media.children[19].title == "Preset 20"
    assert media.children[19].can_expand is False
    assert media.children[19].can_play is True

    # TUNER (FM)
    media = await mp_entity.async_browse_media(None, "dab:fmpresets")
    assert media.media_class == "directory"
    assert media.media_content_id == "dab:fmpresets"
    assert media.title == "TUNER (FM)"
    assert media.can_expand is True
    assert media.can_play is False

    assert len(media.children) == 40
    assert media.children[39].media_class == "music"
    assert media.children[39].media_content_id == "dab:fmpreset:40"
    assert media.children[39].title == "Preset 40"
    assert media.children[39].can_expand is False
    assert media.children[39].can_play is True


async def test_mediaplayer_entity_store_preset(
    mp_entity: YamahaYncaZone, mock_zone, mock_ynca
):
    mock_zone.inp = ynca.Input.TUNER
    mock_ynca.tun = create_autospec(ynca.subunits.tun.Tun)

    mp_entity.store_preset(12)
    mock_ynca.tun.mem.assert_called_once_with(12)


async def test_mediaplayer_entity_store_preset_warning(
    mp_entity: YamahaYncaZone, mock_zone, caplog
):
    mock_zone.inp = ynca.Input.HDMI1  # Does not support presets

    mp_entity.store_preset(12)
    assert caplog.record_tuples == [
        (
            "custom_components.yamaha_ynca",
            logging.WARNING,
            "Unable to store preset 12 for current input HDMI1",
        )
    ]
