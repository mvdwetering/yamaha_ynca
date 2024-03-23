from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

import voluptuous as vol  # type: ignore[import]
import ynca

from homeassistant.components import media_source
from homeassistant.components.media_player import (
    BrowseMedia,
    MediaClass,
    MediaPlayerDeviceClass,
    MediaPlayerEnqueue,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
    RepeatMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    config_validation as cv,
    device_registry,
    entity_platform,
)
from homeassistant.helpers.entity import DeviceInfo

from . import build_devicename
from .const import (
    ATTR_PRESET_ID,
    CONF_HIDDEN_INPUTS,
    CONF_HIDDEN_SOUND_MODES,
    DOMAIN,
    LOGGER,
    SERVICE_STORE_PRESET,
    ZONE_ATTRIBUTE_NAMES,
    ZONE_MAX_VOLUME,
    ZONE_MIN_VOLUME,
)
from .helpers import DomainEntryData, scale
from .input_helpers import InputHelper

if TYPE_CHECKING:  # pragma: no cover
    from ynca.subunits.zone import ZoneBase


STRAIGHT = "Straight"

SUPPORTED_MEDIA_ID_TYPES = ["dabpreset", "fmpreset", "preset"]


async def async_setup_entry(hass, config_entry: ConfigEntry, async_add_entities):
    domain_entry_data: DomainEntryData = hass.data[DOMAIN][config_entry.entry_id]

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_STORE_PRESET,
        {
            vol.Required(ATTR_PRESET_ID): cv.positive_int,
        },
        "store_preset",
    )

    entities = []
    for zone_attr_name in ZONE_ATTRIBUTE_NAMES:
        if zone_subunit := getattr(domain_entry_data.api, zone_attr_name):
            hidden_inputs = config_entry.options.get(zone_subunit.id, {}).get(
                CONF_HIDDEN_INPUTS, []
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
    _attr_name = None

    def __init__(
        self,
        receiver_unique_id: str,
        ynca: ynca.YncaApi,
        zone: ZoneBase,
        hidden_inputs: List[str],
        hidden_sound_modes: List[str],
    ):
        self._ynca = ynca
        self._zone = zone
        self._hidden_inputs = hidden_inputs
        self._hidden_sound_modes = hidden_sound_modes

        self._device_id = f"{receiver_unique_id}_{self._zone.id}"

        self._attr_unique_id = self._device_id
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, self._device_id)})

    def update_callback(self, function, value):
        if function == "ZONENAME":
            # Note that the mediaplayer does not have a name since it uses the devicename
            # So update the device name when the zonename changes to keep names as expected
            registry = device_registry.async_get(self.hass)
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
                    (
                        self._zone.maxvol
                        if self._zone.maxvol is not None
                        else ZONE_MAX_VOLUME
                    ),
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

        return sound_modes if sound_modes else None

    def _has_limited_playback_controls(self, subunit):
        """Indicates if subunit has limited playback control (aka only Play and Stop)"""
        return (
            subunit is self._ynca.netradio
            or subunit is self._ynca.sirius
            or subunit is self._ynca.siriusir
            or subunit is self._ynca.siriusxm
        )

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Flag of media commands that are supported."""

        # Assume power is always supported
        # I can't initialize supported_command to nothing
        supported_commands = (
            MediaPlayerEntityFeature.TURN_ON | MediaPlayerEntityFeature.TURN_OFF
        )

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

        # This assumes there is at least one input that supports preset
        if self._has_subunit_that_supports_presets():
            supported_commands |= MediaPlayerEntityFeature.BROWSE_MEDIA
            supported_commands |= MediaPlayerEntityFeature.PLAY_MEDIA

        return supported_commands

    def _has_subunit_that_supports_presets(self):
        source_mapping = InputHelper.get_source_mapping(self._ynca)

        for input in source_mapping:
            if input.value not in self._hidden_inputs:
                if subunit := InputHelper.get_subunit_for_input(self._ynca, input):
                    if hasattr(subunit, "preset"):
                        return True
                    # also covers fmpreset since on the same subunit
                    if hasattr(subunit, "dabpreset"):
                        return True
        return False

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
            if channelname := getattr(subunit, "chname", None):
                return channelname
        return None

    async def async_browse_media(
        self, media_content_type: str | None = None, media_content_id: str | None = None
    ) -> BrowseMedia:
        """Implement the websocket media browsing helper."""

        LOGGER.debug(
            "media_content_id: %s, media_content_type: %s",
            media_content_id,
            media_content_type,
        )


        if media_content_id is None or media_content_id == "presets":
            return self.build_media_root_item()

        parts = media_content_id.split(":", 1)

        if len(parts) == 2:
            subunit_attribute_name = parts[0]
            media_content_id_type = parts[1]

            return self.build_presetlist_media_item(subunit_attribute_name, media_content_id_type)


        raise HomeAssistantError(
            f"Media content id could not be resolved: {media_content_id}"
        )

    def build_media_root_item(self):
        children = []

        # Generic presets
        source_mapping = InputHelper.get_source_mapping(self._ynca)
        for input, name in source_mapping.items():
            if input.value not in self._hidden_inputs:
                if subunit := InputHelper.get_subunit_for_input(self._ynca, input):
                    if hasattr(subunit, "preset"):
                        children.append(
                            self.directory_browse_media_item(name, f"{subunit.id.value.lower()}:presets", [])
                        )

        # Presets for DAB Tuner, it has 2 preset lists and uses different attribute names, so add manually
        if self._ynca.dab and ynca.Input.TUNER.value not in self._hidden_inputs:
            children.extend(
                [
                    self.directory_browse_media_item("TUNER (DAB)", "dab:dabpresets", []),
                    self.directory_browse_media_item("TUNER (FM)", "dab:fmpresets", []),
                ]
            )

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id="presets",
            media_content_type="",
            title=f"Presets",
            can_play=False,
            can_expand=True,
            children=children,
            children_media_class=MediaClass.DIRECTORY,
        )
    
    def build_presetlist_media_item(self, subunit_attribute_name, media_content_id_type):
        if media_content_id_type == "dabpresets":
            name = "TUNER (DAB)"
        elif media_content_id_type == "fmpresets":
            name = "TUNER (FM)"
        else:
            if subunit := getattr(self._ynca, subunit_attribute_name, None):
                input = InputHelper.get_input_for_subunit(subunit)
                source_mapping = InputHelper.get_source_mapping(self._ynca)
                name = source_mapping.get(input, source_mapping[input])

        stripped_media_content_id_type = media_content_id_type[:-1]  # Strips the 's' of xyz_presets
        preset_items = [
            BrowseMedia(
                media_class=MediaClass.MUSIC,
                media_content_id=f"{subunit_attribute_name}:{stripped_media_content_id_type}:{i+1}",
                media_content_type=MediaType.MUSIC,
                title=f"Preset {i+1}",
                can_play=True,
                can_expand=False,
            )
            for i in range(40)
        ]

        return self.directory_browse_media_item(
            name,
            f"{subunit_attribute_name}:{media_content_id_type}",
            preset_items
        )



    def directory_browse_media_item(self, name, media_content_id, presets):
        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=media_content_id,
            media_content_type="",
            title=name,
            can_play=False,
            can_expand=True,
            children=presets,
            children_media_class=MediaClass.MUSIC,
        )
    
    async def async_play_media(
        self,
        media_type: str,
        media_id: str,
        enqueue: MediaPlayerEnqueue | None = None,
        announce: bool | None = None,
        **kwargs: Any,
    ) -> None:
        LOGGER.debug("media type, id: %s, %s", media_type, media_id)

        """Play a piece of media."""
        if media_source.is_media_source_id(media_id):
            raise HomeAssistantError(
                f"Media sources are not supported by this media player: {media_id}"
            )

        # Expected media_id format is: subunit:preset:#

        parts = media_id.split(":")
        if len(parts) != 3:
            raise HomeAssistantError(
                f"Malformed media id: {media_id}"
            )

        media_id_subunit = parts[0]
        media_id_command = parts[1]
        media_id_preset_id = parts[2]

        self.validate_media_id(media_id, media_id_subunit, media_id_command, media_id_preset_id)

        # Apply media_id to receiver
        if self._zone.pwr is ynca.Pwr.STANDBY:
            self._zone.pwr = ynca.Pwr.ON

        subunit = getattr(self._ynca, media_id_subunit)
        input = InputHelper.get_input_for_subunit(subunit)
        if self._zone.inp is not input:
            self._zone.inp = input

        setattr(subunit, media_id_command, int(media_id_preset_id))


    def validate_media_id(self, media_id, media_id_subunit, media_id_command, media_id_preset_id):
        if not hasattr(self._ynca, media_id_subunit):
            raise HomeAssistantError(
                f"Malformed media id: {media_id}"
            )

        if media_id_command not in ["preset", "fmpreset", "dabpreset"]:
            raise HomeAssistantError(
                f"Malformed media id: {media_id}"
            )

        try:
            preset_id = int(media_id_preset_id)
            if preset_id < 1 or preset_id > 40:
                raise ValueError
        except ValueError:
            raise HomeAssistantError(
                f"Malformed preset or out of range: {media_id}"
            )

    def store_preset(self, preset_id: int) -> None:
        if subunit := InputHelper.get_subunit_for_input(self._ynca, self._zone.inp):
            if hasattr(subunit, "mem"):
                subunit.mem(preset_id)
                return

        LOGGER.warning(
            "Unable to store preset %s for current input %s",
            preset_id,
            self._zone.inp.value if self._zone.inp else "None",
        )
