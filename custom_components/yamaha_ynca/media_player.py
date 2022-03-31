from __future__ import annotations
from typing import Optional, Type

import ynca

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerDeviceClass,
)
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_MUSIC,
    MEDIA_TYPE_CHANNEL,
    REPEAT_MODE_ALL,
    REPEAT_MODE_OFF,
    REPEAT_MODE_ONE,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
    SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET,
    SUPPORT_VOLUME_STEP,
    SUPPORT_SELECT_SOURCE,
    SUPPORT_SELECT_SOUND_MODE,
    SUPPORT_PLAY,
    SUPPORT_PAUSE,
    SUPPORT_STOP,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_REPEAT_SET,
    SUPPORT_SHUFFLE_SET,
)
from homeassistant.const import (
    STATE_OFF,
    STATE_ON,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_IDLE,
)

from .const import DOMAIN, LOGGER

SUPPORT_YAMAHA_YNCA_BASE = (
    SUPPORT_VOLUME_SET
    | SUPPORT_VOLUME_MUTE
    | SUPPORT_VOLUME_STEP
    | SUPPORT_TURN_ON
    | SUPPORT_TURN_OFF
    | SUPPORT_SELECT_SOURCE
)

RADIO_SUBUNITS = [ynca.Subunit.NETRADIO, ynca.Subunit.SIRIUS, ynca.Subunit.SIRIUSIR]

STRAIGHT = "Straight"


async def async_setup_entry(hass, config_entry, async_add_entities):

    receiver = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for zone_subunit_id in ynca.ZONE_SUBUNIT_IDS:
        if zone_subunit := getattr(receiver, zone_subunit_id):
            entities.append(
                YamahaYncaZone(config_entry.entry_id, receiver, zone_subunit)
            )

    async_add_entities(entities)


class YamahaYncaZone(MediaPlayerEntity):
    """Representation of a zone of a Yamaha Ynca device."""

    _attr_device_class = MediaPlayerDeviceClass.RECEIVER
    _attr_should_poll = False

    def __init__(
        self, receiver_unique_id: str, receiver: ynca.Receiver, zone: Type[ynca.Zone]
    ):
        self._receiver = receiver
        self._zone = zone

        self._attr_unique_id = f"{receiver_unique_id}_{self._zone.id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, receiver_unique_id)},
        }

    async def async_added_to_hass(self):
        # Register to catch input renames on SYS
        self._receiver.SYS.register_update_callback(self.schedule_update_ha_state)
        self._zone.register_update_callback(self.schedule_update_ha_state)

        # TODO: Optimize registrations as now all zones get triggered by all changes
        #       even when change happens on subunit that is not input of this zone
        for subunit_id in ynca.SUBUNIT_INPUT_MAPPINGS.keys():
            if subunit := getattr(self._receiver, subunit_id.value, None):
                subunit.register_update_callback(self.schedule_update_ha_state)

    async def async_will_remove_from_hass(self):
        self._receiver.SYS.unregister_update_callback(self.schedule_update_ha_state)
        self._zone.unregister_update_callback(self.schedule_update_ha_state)
        for subunit_id in ynca.SUBUNIT_INPUT_MAPPINGS.keys():
            if subunit := getattr(self._receiver, subunit_id.value, None):
                subunit.unregister_update_callback(self.schedule_update_ha_state)

    @staticmethod
    def scale(input_value, input_range, output_range):
        input_min = input_range[0]
        input_max = input_range[1]
        input_spread = input_max - input_min

        output_min = output_range[0]
        output_max = output_range[1]
        output_spread = output_max - output_min

        value_scaled = float(input_value - input_min) / float(input_spread)

        return output_min + (value_scaled * output_spread)

    def get_input_from_source(self, source):
        for input, name in self._receiver.inputs.items():
            if name == source:
                return input

    def _input_subunit(self) -> Optional[ynca.Subunit]:
        """Returns Subunit for current selected input if possible, otherwise None"""
        for subunit, input_name in ynca.SUBUNIT_INPUT_MAPPINGS.items():
            if input_name == self._zone.input:
                return getattr(self._receiver, subunit.value, None)
        return None

    @property
    def name(self):
        """Return the name of the entity."""
        return self._zone.name

    @property
    def state(self):
        """Return the state of the entity."""
        if not self._zone.on:
            return STATE_OFF

        if input_subunit := self._input_subunit():
            playbackinfo = getattr(input_subunit, "playbackinfo", None)
            if playbackinfo == ynca.PlaybackInfo.PLAY:
                return STATE_PLAYING
            if playbackinfo == ynca.PlaybackInfo.PAUSE:
                return STATE_PAUSED
            if playbackinfo == ynca.PlaybackInfo.STOP:
                return STATE_IDLE

        return STATE_ON

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self.scale(
            self._zone.volume, [self._zone.min_volume, self._zone.max_volume], [0, 1]
        )

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._zone.mute != ynca.Mute.off

    @property
    def source(self):
        """Return the current input source."""
        return self._receiver.inputs[self._zone.input]

    @property
    def source_list(self):
        """List of available input sources."""
        # Return the user given names instead HDMI1 etc...
        return sorted(
            list(self._receiver.inputs.values()), key=str.lower
        )  # Using `str.lower` does not work for all languages, but better than nothing

    @property
    def sound_mode(self):
        """Return the current input source."""
        return STRAIGHT if self._zone.straight else self._zone.dsp_sound_program

    @property
    def sound_mode_list(self):
        """List of available sound modes."""
        sound_modes = []
        if self._zone.straight is not None:
            sound_modes.append(STRAIGHT)
        if self._zone.dsp_sound_program:
            sound_modes.extend(ynca.DSP_SOUND_PROGRAMS)
        sound_modes.sort(
            key=str.lower
        )  # Using `str.lower` does not work for all languages, but better than nothing
        return sound_modes if len(sound_modes) > 0 else None

    @property
    def supported_features(self):
        """Flag of media commands that are supported."""
        supported_commands = SUPPORT_YAMAHA_YNCA_BASE
        if self._zone.dsp_sound_program:
            supported_commands |= SUPPORT_SELECT_SOUND_MODE

        if input_subunit := self._input_subunit():
            if hasattr(input_subunit, "playback"):
                supported_commands |= SUPPORT_PLAY
                supported_commands |= SUPPORT_STOP
                if input_subunit not in RADIO_SUBUNITS:
                    supported_commands |= SUPPORT_PAUSE
                    supported_commands |= SUPPORT_NEXT_TRACK
                    supported_commands |= SUPPORT_PREVIOUS_TRACK
            if hasattr(input_subunit, "repeat"):
                supported_commands |= SUPPORT_REPEAT_SET
            if hasattr(input_subunit, "shuffle"):
                supported_commands |= SUPPORT_SHUFFLE_SET
        return supported_commands

    def turn_on(self):
        """Turn the media player on."""
        self._zone.on = True

    def turn_off(self):
        """Turn off media player."""
        self._zone.on = False

    def set_volume_level(self, volume):
        """Set volume level, convert range from 0..1."""
        self._zone.volume = self.scale(
            volume, [0, 1], [self._zone.min_volume, self._zone.max_volume]
        )

    def volume_up(self):
        """Volume up media player."""
        self._zone.volume_up()

    def volume_down(self):
        """Volume down media player."""
        self._zone.volume_down()

    def mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        self._zone.mute = ynca.Mute.on if mute else ynca.Mute.off

    def select_source(self, source):
        """Select input source."""
        self._zone.input = self.get_input_from_source(source)

    def select_sound_mode(self, sound_mode):
        """Switch the sound mode of the entity."""
        if sound_mode == STRAIGHT:
            self._zone.straight = True
        else:
            self._zone.straight = False
            self._zone.dsp_sound_program = sound_mode

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
        self._input_subunit().shuffle

    @property
    def repeat(self) -> Optional[str]:
        """Return current repeat mode."""
        if subunit := self._input_subunit():
            repeat = getattr(subunit, "repeat", None)
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
            if hasattr(subunit, "song"):
                return MEDIA_TYPE_MUSIC
            if hasattr(subunit, "station"):
                return MEDIA_TYPE_CHANNEL
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
            return getattr(subunit, "station", None)
        return None
