from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

import ynca

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    RepeatMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity import DeviceInfo

from . import build_devicename
from .const import (
    CONF_HIDDEN_INPUTS,
    CONF_HIDDEN_SOUND_MODES,
    DOMAIN,
    LOGGER,
    ZONE_ATTRIBUTE_NAMES,
    ZONE_MAX_VOLUME,
    ZONE_MIN_VOLUME,
)
from .helpers import DomainEntryData, scale
from .input_helpers import InputHelper

if TYPE_CHECKING:  # pragma: no cover
    from ynca.subunits.zone import ZoneBase


STRAIGHT = "Straight"


async def async_setup_entry(hass, config_entry: ConfigEntry, async_add_entities):
    domain_entry_data: DomainEntryData = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for zone_attr_name in ZONE_ATTRIBUTE_NAMES:
        if zone_subunit := getattr(domain_entry_data.api, zone_attr_name):
            hidden_inputs = config_entry.options.get(zone_subunit.id, {}).get(
                CONF_HIDDEN_INPUTS, []
            )
            hidden_sound_modes = config_entry.options.get(CONF_HIDDEN_SOUND_MODES, [])

            entities.append(
                YamahaYncaZone(
                    hass,
                    config_entry.entry_id,
                    domain_entry_data.api,
                    zone_subunit,
                    hidden_inputs,
                    hidden_sound_modes,
                )
            )

    async_add_entities(entities)


class YamahaYncaZone(MediaPlayerEntity):
    """Representation of a zone of a Yamaha Ynca device."""

    _attr_device_class = MediaPlayerDeviceClass.RECEIVER
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        receiver_unique_id: str,
        ynca: ynca.YncaApi,
        zone: ZoneBase,
        hidden_inputs: List[str],
        hidden_sound_modes: List[str],
    ):
        self._hass = hass
        self._ynca = ynca
        self._zone = zone
        self._hidden_inputs = hidden_inputs
        self._hidden_sound_modes = hidden_sound_modes

        self._device_id = f"{receiver_unique_id}_{self._zone.id}"

        self._attr_unique_id = self._device_id
        self._attr_device_info = DeviceInfo(
            identifiers = {(DOMAIN, self._device_id)}
        )

    def update_callback(self, function, value):
        if function == "ZONENAME":
            # Note that the mediaplayer does not have a name since it uses the devicename
            # So update the device name when the zonename changes to keep names as expected
            registry = device_registry.async_get(self._hass)
            device = registry.async_get_device(identifiers={(DOMAIN, self._device_id)})
            if device:
                devicename = build_devicename(self._ynca, self._zone)
                registry.async_update_device(device.id, name=devicename)

        self.schedule_update_ha_state()

    def _get_input_subunits(self):
        for attribute in sorted(dir(self._ynca)):
            if attribute in ["sys", "main", "zone2", "zone3", "zone4"]:
                continue
            if attribute_instance := getattr(self._ynca, attribute):
                if isinstance(attribute_instance, ynca.subunit.SubunitBase):
                    yield attribute_instance

    async def async_added_to_hass(self):
        # Register to catch input renames on SYS
        assert self._ynca.sys is not None
        self._ynca.sys.register_update_callback(self.update_callback)
        self._zone.register_update_callback(self.update_callback)

        for subunit in self._get_input_subunits():
            subunit.register_update_callback(self.update_callback)

    async def async_will_remove_from_hass(self):
        assert self._ynca.sys is not None
        self._ynca.sys.unregister_update_callback(self.update_callback)
        self._zone.unregister_update_callback(self.update_callback)

        for subunit in self._get_input_subunits():
            subunit.unregister_update_callback(self.update_callback)

    def _get_input_subunit(self):
        if self._zone.inp is not None:
            return InputHelper.get_subunit_for_input(self._ynca, self._zone.inp)

    @property
    def state(self):
        """Return the state of the entity."""
        if self._zone.pwr is ynca.Pwr.STANDBY:
            return MediaPlayerState.OFF

        if input_subunit := self._get_input_subunit():
            playbackinfo = getattr(input_subunit, "playbackinfo", None)
            if playbackinfo is ynca.PlaybackInfo.PLAY:
                return MediaPlayerState.PLAYING
            if playbackinfo is ynca.PlaybackInfo.PAUSE:
                return MediaPlayerState.PAUSED
            if playbackinfo is ynca.PlaybackInfo.STOP:
                return MediaPlayerState.IDLE

        return MediaPlayerState.IDLE

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        if self._zone.vol is not None:
            return scale(
                self._zone.vol,
                [
                    ZONE_MIN_VOLUME,
                    self._zone.maxvol
                    if self._zone.maxvol is not None
                    else ZONE_MAX_VOLUME,
                ],
                [0, 1],
            )

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        if self._zone.mute is not None:
            return self._zone.mute != ynca.Mute.OFF

    @property
    def source(self):
        """Return the current input source."""
        if self._zone.inp is not None:
            return (
                InputHelper.get_name_of_input(self._ynca, self._zone.inp) or "Unknown"
            )

    @property
    def source_list(self) -> List[str]:
        """List of available sources."""
        source_mapping = InputHelper.get_source_mapping(self._ynca)

        filtered_sources = [
            name
            for input, name in source_mapping.items()
            if input.value not in self._hidden_inputs
        ]

        return sorted(filtered_sources, key=str.lower)

    @property
    def sound_mode(self):
        """Return the current input sound mode."""
        return (
            STRAIGHT if self._zone.straight is ynca.Straight.ON else self._zone.soundprg
        )

    @property
    def sound_mode_list(self):
        """List of available sound modes."""
        sound_modes = []
        if self._zone.straight is not None:
            sound_modes.append(STRAIGHT)
        if self._zone.soundprg:
            assert self._ynca.sys is not None
            assert isinstance(self._ynca.sys.modelname, str)
            modelinfo = ynca.YncaModelInfo.get(self._ynca.sys.modelname)
            device_sound_modes = [
                sound_mode.value
                for sound_mode in (modelinfo.soundprg if modelinfo else ynca.SoundPrg)  # type: ignore[attr-defined]
                if sound_mode is not ynca.SoundPrg.UNKNOWN
            ]
            sound_modes.extend(device_sound_modes)

        # Filter hidden sound modes
        sound_modes = [
            sound_mode
            for sound_mode in sound_modes
            if sound_mode not in self._hidden_sound_modes
        ]
        sound_modes.sort(key=str.lower)

        return sound_modes if len(sound_modes) > 0 else None

    def _has_limited_playback_controls(self, subunit):
        """Indicates if subunit has limited playback control (aka only Play and Stop)"""
        return (
            subunit is self._ynca.netradio
            or subunit is self._ynca.sirius
            or subunit is self._ynca.siriusir
            or subunit is self._ynca.siriusxm
        )

    @property
    def supported_features(self):
        """Flag of media commands that are supported."""
        supported_commands = 0

        if self._zone.pwr is not None:
            supported_commands |= MediaPlayerEntityFeature.TURN_ON
            supported_commands |= MediaPlayerEntityFeature.TURN_OFF

        if self._zone.vol is not None:
            supported_commands |= MediaPlayerEntityFeature.VOLUME_SET
            supported_commands |= MediaPlayerEntityFeature.VOLUME_STEP

        if self._zone.mute is not None:
            supported_commands |= MediaPlayerEntityFeature.VOLUME_MUTE

        if self._zone.inp is not None:
            supported_commands |= MediaPlayerEntityFeature.SELECT_SOURCE

        if self._zone.soundprg is not None:
            supported_commands |= MediaPlayerEntityFeature.SELECT_SOUND_MODE

        if input_subunit := self._get_input_subunit():
            if getattr(input_subunit, "playback", None) is not None:
                supported_commands |= MediaPlayerEntityFeature.PLAY
                supported_commands |= MediaPlayerEntityFeature.STOP
                if not self._has_limited_playback_controls(input_subunit):
                    supported_commands |= MediaPlayerEntityFeature.PAUSE
                    supported_commands |= MediaPlayerEntityFeature.NEXT_TRACK
                    supported_commands |= MediaPlayerEntityFeature.PREVIOUS_TRACK
            if getattr(input_subunit, "repeat", None) is not None:
                supported_commands |= MediaPlayerEntityFeature.REPEAT_SET
            if getattr(input_subunit, "shuffle", None) is not None:
                supported_commands |= MediaPlayerEntityFeature.SHUFFLE_SET
        return supported_commands

    def turn_on(self):
        """Turn the media player on."""
        self._zone.pwr = ynca.Pwr.ON

    def turn_off(self):
        """Turn off media player."""
        self._zone.pwr = ynca.Pwr.STANDBY

    def set_volume_level(self, volume):
        """Set volume level, convert range from 0..1."""
        self._zone.vol = scale(
            volume,
            [0, 1],
            [
                ZONE_MIN_VOLUME,
                self._zone.maxvol if self._zone.maxvol is not None else ZONE_MAX_VOLUME,
            ],
        )

    def volume_up(self):
        """Volume up media player."""
        self._zone.vol_up()

    def volume_down(self):
        """Volume down media player."""
        self._zone.vol_down()

    def mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        self._zone.mute = ynca.Mute.ON if mute else ynca.Mute.OFF

    def select_source(self, source):
        """Select input source."""
        if input := InputHelper.get_input_by_name(self._ynca, source):
            self._zone.inp = input

    def select_sound_mode(self, sound_mode):
        """Switch the sound mode of the entity."""
        if sound_mode == STRAIGHT:
            self._zone.straight = ynca.Straight.ON
        else:
            self._zone.soundprg = ynca.SoundPrg(sound_mode)

            if self._zone.straight is ynca.Straight.ON:
                self._zone.straight = ynca.Straight.OFF

            if self._zone.puredirmode is ynca.PureDirMode.ON:
                self._zone.puredirmode = ynca.PureDirMode.OFF

    # Playback controls (zone forwards to active subunit automatically it seems)
    def media_play(self):
        self._zone.playback(ynca.Playback.PLAY)

    def media_pause(self):
        self._zone.playback(ynca.Playback.PAUSE)

    def media_stop(self):
        self._zone.playback(ynca.Playback.STOP)

    def media_next_track(self):
        self._zone.playback(ynca.Playback.SKIP_FWD)

    def media_previous_track(self):
        self._zone.playback(ynca.Playback.SKIP_REV)

    @property
    def shuffle(self) -> Optional[bool]:
        """Boolean if shuffle is enabled."""
        if subunit := self._get_input_subunit():
            if shuffle := getattr(subunit, "shuffle", None):
                return shuffle == ynca.Shuffle.ON
        return None

    def set_shuffle(self, shuffle):
        """Enable/disable shuffle mode."""
        self._get_input_subunit().shuffle = (
            ynca.Shuffle.ON if shuffle else ynca.Shuffle.OFF
        )

    @property
    def repeat(self) -> Optional[str]:
        """Return current repeat mode."""
        if subunit := self._get_input_subunit():
            if repeat := getattr(subunit, "repeat", None):
                if repeat == ynca.Repeat.SINGLE:
                    return RepeatMode.ONE
                if repeat == ynca.Repeat.ALL:
                    return RepeatMode.ALL
                if repeat == ynca.Repeat.OFF:
                    return RepeatMode.OFF
        return None

    def set_repeat(self, repeat):
        """Set repeat mode."""
        subunit = self._get_input_subunit()
        if repeat == RepeatMode.ALL:
            subunit.repeat = ynca.Repeat.ALL
        elif repeat == RepeatMode.OFF:
            subunit.repeat = ynca.Repeat.OFF
        elif repeat == RepeatMode.ONE:
            subunit.repeat = ynca.Repeat.SINGLE

    def _is_radio_subunit(self, subunit: ynca.subunit.Subunit) -> bool:
        return (
            subunit is self._ynca.dab
            or subunit is self._ynca.netradio
            or subunit is self._ynca.tun
            or subunit is self._ynca.sirius
            or subunit is self._ynca.siriusir
            or subunit is self._ynca.siriusxm
        )

    # Media info
    @property
    def media_content_type(self) -> Optional[str]:
        """Content type of current playing media."""
        if subunit := self._get_input_subunit():
            if self._is_radio_subunit(subunit):
                return MediaType.CHANNEL
            if (
                getattr(subunit, "song", None) is not None
                or getattr(subunit, "track", None) is not None
            ):
                return MediaType.MUSIC
        return None

    @property
    def media_title(self) -> Optional[str]:
        """Title of current playing media."""
        if subunit := self._get_input_subunit():
            if song := getattr(subunit, "song", None):
                return song
            if track := getattr(subunit, "track", None):
                return track
            if subunit is self._ynca.dab and subunit.band is ynca.BandDab.DAB:
                if subunit.dabdlslabel:
                    return subunit.dabdlslabel
        return None

    @property
    def media_artist(self) -> Optional[str]:
        """Artist of current playing media, music track only."""
        if subunit := self._get_input_subunit():
            return getattr(subunit, "artist", None)
        return None

    @property
    def media_album_name(self) -> Optional[str]:
        """Album name of current playing media, music track only."""
        if subunit := self._get_input_subunit():
            return getattr(subunit, "album", None)
        return None

    @property
    def media_channel(self) -> Optional[str]:
        """Channel currently playing."""
        if subunit := self._get_input_subunit():
            if subunit is self._ynca.tun:
                # AM/FM Tuner
                if subunit.band is ynca.BandTun.AM:
                    return f"AM {subunit.amfreq} kHz"
                if subunit.band is ynca.BandTun.FM:
                    return (
                        subunit.rdsprgservice
                        if subunit.rdsprgservice
                        else f"FM {subunit.fmfreq:.2f} MHz"
                    )
            if subunit is self._ynca.dab:
                # DAB/FM Tuner
                if subunit.band is ynca.BandDab.FM:
                    return (
                        subunit.fmrdsprgservice
                        if subunit.fmrdsprgservice
                        else f"FM {subunit.fmfreq:.2f} MHz"
                    )
                if subunit.band is ynca.BandDab.DAB:
                    return subunit.dabservicelabel

            # Netradio
            if station := getattr(subunit, "station", None):
                return station

            # Sirius variants
            channelname = getattr(subunit, "chname", None)
            return channelname
        return None
