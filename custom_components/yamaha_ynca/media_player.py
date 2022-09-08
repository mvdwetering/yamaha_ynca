from __future__ import annotations
from typing import List, Optional, Type

import ynca

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerDeviceClass,
)
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_MUSIC,
    MEDIA_TYPE_CHANNEL,
    REPEAT_MODE_ALL,
    REPEAT_MODE_OFF,
    REPEAT_MODE_ONE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_OFF,
    STATE_ON,
    STATE_PLAYING,
    STATE_PAUSED,
)


from .const import (
    CONF_HIDDEN_SOUND_MODES,
    DOMAIN,
    LOGGER,
    ZONE_MIN_VOLUME,
    ZONE_SUBUNIT_IDS,
    CONF_HIDDEN_INPUTS_FOR_ZONE,
)
from .helpers import scale, DomainEntryData

SUPPORT_YAMAHA_YNCA_BASE = (
    MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.VOLUME_MUTE
    | MediaPlayerEntityFeature.VOLUME_STEP
    | MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
    | MediaPlayerEntityFeature.SELECT_SOURCE
)

LIMITED_PLAYBACK_CONTROL_SUBUNITS = [
    ynca.Subunit.NETRADIO,
    ynca.Subunit.SIRIUS,
    ynca.Subunit.SIRIUSIR,
    ynca.Subunit.SIRIUSXM,
]

RADIO_SOURCES = [
    ynca.Subunit.NETRADIO,
    ynca.Subunit.TUN,
    ynca.Subunit.SIRIUS,
    ynca.Subunit.SIRIUSIR,
    ynca.Subunit.SIRIUSXM,
]

STRAIGHT = "Straight"


async def async_setup_entry(hass, config_entry: ConfigEntry, async_add_entities):

    domain_entry_data: DomainEntryData = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for zone_subunit_id in ZONE_SUBUNIT_IDS:
        if zone_subunit := getattr(domain_entry_data.api, zone_subunit_id):
            hidden_inputs = config_entry.options.get(
                CONF_HIDDEN_INPUTS_FOR_ZONE(zone_subunit_id), []
            )
            hidden_sound_modes = config_entry.options.get(CONF_HIDDEN_SOUND_MODES, [])

            entities.append(
                YamahaYncaZone(
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
        receiver_unique_id: str,
        ynca: ynca.Ynca,
        zone: Type[ynca.zone.ZoneBase],
        hidden_inputs: List[str],
        hidden_sound_modes: List[str],
    ):
        self._ynca = ynca
        self._zone = zone
        self._hidden_inputs = hidden_inputs
        self._hidden_sound_modes = hidden_sound_modes

        self._attr_unique_id = f"{receiver_unique_id}_{self._zone.id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, receiver_unique_id)},
        }

    def update_callback(self):
        self.schedule_update_ha_state()

    def _get_input_subunits(self):
        for inputinfo in ynca.get_inputinfo_list(self._ynca):
            if inputinfo.subunit is None:
                continue
            if subunit := getattr(self._ynca, inputinfo.subunit.value, None):
                yield subunit

    async def async_added_to_hass(self):
        # Register to catch input renames on SYS
        self._ynca.SYS.register_update_callback(self.update_callback)
        self._zone.register_update_callback(self.update_callback)

        # TODO: Optimize registrations as now all zones get triggered by all changes
        #       even when change happens on subunit that is not input of this zone
        for subunit in self._get_input_subunits():
            subunit.register_update_callback(self.update_callback)

    async def async_will_remove_from_hass(self):
        self._ynca.SYS.unregister_update_callback(self.update_callback)
        self._zone.unregister_update_callback(self.update_callback)

        for subunit in self._get_input_subunits():
            subunit.unregister_update_callback(self.update_callback)

    def _get_input_from_source(self, source):
        for inputinfo in ynca.get_inputinfo_list(self._ynca):
            if inputinfo.name == source:
                return inputinfo.input
        return None

    def _input_subunit(self):
        """Returns Subunit for current selected input if possible, otherwise None"""
        for inputinfo in ynca.get_inputinfo_list(self._ynca):
            if inputinfo.subunit is None:
                continue
            if inputinfo.input == self._zone.inp:
                return getattr(self._ynca, inputinfo.subunit.value, None)
        return None

    @property
    def name(self):
        """Return the name of the entity."""
        return self._zone.zonename or self._zone.id

    @property
    def state(self):
        """Return the state of the entity."""
        if not self._zone.pwr:
            return STATE_OFF

        if input_subunit := self._input_subunit():
            playbackinfo = getattr(input_subunit, "playbackinfo", None)
            if playbackinfo == ynca.PlaybackInfo.PLAY:
                return STATE_PLAYING
            if playbackinfo == ynca.PlaybackInfo.PAUSE:
                return STATE_PAUSED
            if playbackinfo == ynca.PlaybackInfo.STOP:
                return STATE_ON

        return STATE_ON

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return scale(self._zone.vol, [ZONE_MIN_VOLUME, self._zone.maxvol], [0, 1])

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._zone.mute != ynca.Mute.off

    @property
    def source(self):
        """Return the current input source."""
        current_input_info = [
            inputinfo
            for inputinfo in ynca.get_inputinfo_list(self._ynca)
            if inputinfo.input == self._zone.inp
        ]
        return (
            current_input_info[0].name
            if len(current_input_info) > 0
            else self._zone.inp
        )

    @property
    def source_list(self):
        """List of available input sources."""
        inputinfos = ynca.get_inputinfo_list(self._ynca)
        filtered_inputs = [
            inputinfo.name
            for inputinfo in inputinfos
            if inputinfo.input not in self._hidden_inputs
        ]

        # Return the user given names instead HDMI1 etc...
        return sorted(
            filtered_inputs, key=str.lower
        )  # Using `str.lower` does not work for all languages, but better than nothing

    @property
    def sound_mode(self):
        """Return the current input source."""
        return STRAIGHT if self._zone.straight else self._zone.soundprg

    @property
    def sound_mode_list(self):
        """List of available sound modes."""
        sound_modes = []
        if self._zone.straight is not None:
            sound_modes.append(STRAIGHT)
        if self._zone.soundprg:
            modelinfo = ynca.get_modelinfo(self._ynca.SYS.modelname)
            filtered_sound_modes = [
                sound_mode.value
                for sound_mode in (modelinfo.soundprg if modelinfo else ynca.SoundPrg)
                if sound_mode.name not in self._hidden_sound_modes
            ]
            sound_modes.extend(filtered_sound_modes)

        sound_modes.sort(
            key=str.lower
        )  # Using `str.lower` does not work for all languages, but better than nothing
        return sound_modes if len(sound_modes) > 0 else None

    @property
    def supported_features(self):
        """Flag of media commands that are supported."""
        supported_commands = SUPPORT_YAMAHA_YNCA_BASE
        if self._zone.soundprg:
            supported_commands |= MediaPlayerEntityFeature.SELECT_SOUND_MODE

        if input_subunit := self._input_subunit():
            if hasattr(input_subunit, "playback"):
                supported_commands |= MediaPlayerEntityFeature.PLAY
                supported_commands |= MediaPlayerEntityFeature.STOP
                if input_subunit.id not in LIMITED_PLAYBACK_CONTROL_SUBUNITS:
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
        self._zone.pwr = True

    def turn_off(self):
        """Turn off media player."""
        self._zone.pwr = False

    def set_volume_level(self, volume):
        """Set volume level, convert range from 0..1."""
        self._zone.vol = scale(volume, [0, 1], [ZONE_MIN_VOLUME, self._zone.maxvol])

    def volume_up(self):
        """Volume up media player."""
        self._zone.vol_up()

    def volume_down(self):
        """Volume down media player."""
        self._zone.vol_down()

    def mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        self._zone.mute = ynca.Mute.on if mute else ynca.Mute.off

    def select_source(self, source):
        """Select input source."""
        if input := self._get_input_from_source(source):
            self._zone.inp = input

    def select_sound_mode(self, sound_mode):
        """Switch the sound mode of the entity."""
        if sound_mode == STRAIGHT:
            self._zone.straight = True
        else:
            self._zone.straight = False
            self._zone.soundprg = sound_mode

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
        if subunit := self._input_subunit():
            return getattr(subunit, "shuffle", None)
        return None

    def set_shuffle(self, shuffle):
        """Enable/disable shuffle mode."""
        self._input_subunit().shuffle = shuffle

    @property
    def repeat(self) -> Optional[str]:
        """Return current repeat mode."""
        if subunit := self._input_subunit():
            if repeat := getattr(subunit, "repeat", None):
                if repeat == ynca.Repeat.SINGLE:
                    return REPEAT_MODE_ONE
                if repeat == ynca.Repeat.ALL:
                    return REPEAT_MODE_ALL
                if repeat == ynca.Repeat.OFF:
                    return REPEAT_MODE_OFF
        return None

    def set_repeat(self, repeat):
        """Set repeat mode."""
        subunit = self._input_subunit()
        if repeat == REPEAT_MODE_ALL:
            subunit.repeat = ynca.Repeat.ALL
        elif repeat == REPEAT_MODE_OFF:
            subunit.repeat = ynca.Repeat.OFF
        elif repeat == REPEAT_MODE_ONE:
            subunit.repeat = ynca.Repeat.SINGLE

    # Media info
    @property
    def media_content_type(self) -> Optional[str]:
        """Content type of current playing media."""
        if subunit := self._input_subunit():
            if subunit.id in RADIO_SOURCES:
                return MEDIA_TYPE_CHANNEL
            if getattr(subunit, "song", None) is not None:
                return MEDIA_TYPE_MUSIC
        return None

    @property
    def media_title(self) -> Optional[str]:
        """Title of current playing media."""
        if subunit := self._input_subunit():
            return getattr(subunit, "song", None)
        return None

    @property
    def media_artist(self) -> Optional[str]:
        """Artist of current playing media, music track only."""
        if subunit := self._input_subunit():
            return getattr(subunit, "artist", None)
        return None

    @property
    def media_album_name(self) -> Optional[str]:
        """Album name of current playing media, music track only."""
        if subunit := self._input_subunit():
            return getattr(subunit, "album", None)
        return None

    @property
    def media_channel(self) -> Optional[str]:
        """Channel currently playing."""
        if subunit := self._input_subunit():
            if subunit.id == ynca.Subunit.TUN:
                return (
                    f"FM {subunit.fmfreq:.2f} MHz"
                    if subunit.band == ynca.Band.FM
                    else f"AM {subunit.amfreq} kHz"
                )
            if subunit.id == ynca.Subunit.NETRADIO:
                return subunit.station
            channelname = getattr(subunit, "chname", None)  # Sirius*
            return channelname
        return None
