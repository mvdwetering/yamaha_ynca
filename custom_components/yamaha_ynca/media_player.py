from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

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
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_platform,
)
from homeassistant.helpers.entity import DeviceInfo
import voluptuous as vol  # type: ignore[import]

import ynca
import ynca.subunit
from ynca.subunits.zone import Main

from . import YamahaYncaConfigEntry, build_zone_devicename, build_zoneb_devicename
from .const import (
    ATTR_PRESET_ID,
    CONF_HIDDEN_INPUTS,
    CONF_HIDDEN_SOUND_MODES,
    DOMAIN,
    LOGGER,
    NUM_PRESETS,
    SERVICE_STORE_PRESET,
    ZONE_ATTRIBUTE_NAMES,
    ZONE_MAX_VOLUME,
    ZONE_MIN_VOLUME,
)
from .helpers import scale
from .input_helpers import InputHelper

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Generator

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ynca.subunits.zone import ZoneBase


STRAIGHT = "Straight"

SUPPORTED_MEDIA_ID_TYPES = ["dabpreset", "fmpreset", "preset"]


async def async_setup_entry(
    _hass: HomeAssistant,
    config_entry: YamahaYncaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    domain_entry_data = config_entry.runtime_data
    api = domain_entry_data.api

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_STORE_PRESET,
        {
            vol.Required(ATTR_PRESET_ID): cv.positive_int,
        },
        "store_preset",
    )

    entities: list[MediaPlayerEntity] = []
    for zone_attr_name in ZONE_ATTRIBUTE_NAMES:
        if zone_subunit := getattr(api, zone_attr_name):
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

            if (
                zone_subunit == api.main
                and api.main.zonebavail is ynca.ZoneBAvail.READY
            ):
                entities.append(
                    YamahaYncaZoneB(config_entry.entry_id, api, hidden_inputs)
                )

    async_add_entities(entities)


class YamahaYncaZone(MediaPlayerEntity):
    """Representation of a zone of a Yamaha Ynca device."""

    _attr_device_class = MediaPlayerDeviceClass.RECEIVER
    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_name = None

    _ZONENAME_FUNCTION = "ZONENAME"

    def __init__(  # noqa: PLR0913
        self,
        receiver_unique_id: str,
        ynca: ynca.YncaApi,
        zone: ZoneBase,
        hidden_inputs: list[str],
        hidden_sound_modes: list[str],
        is_zone_b: bool = False,  # noqa: FBT001, FBT002
    ) -> None:
        self._ynca = ynca
        self._zone = zone
        self._hidden_inputs = hidden_inputs
        self._hidden_sound_modes = hidden_sound_modes
        self._is_zone_b = is_zone_b

        if TYPE_CHECKING and is_zone_b:  # pragma: no cover
            assert isinstance(self._zone, Main)  # noqa: S101

        self._device_id = (
            f"{receiver_unique_id}_{self._zone.id if not is_zone_b else 'ZONEB'}"
        )

        self._attr_unique_id = self._device_id
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, self._device_id)})

    def update_callback(self, function: str | None, _value: Any) -> None:
        if function == self._ZONENAME_FUNCTION:
            # Note that the mediaplayer does not have a name since it uses the devicename
            # So update the device name when the zonename changes to keep names as expected
            registry = dr.async_get(self.hass)
            device = registry.async_get_device(identifiers={(DOMAIN, self._device_id)})
            if device:
                devicename = (
                    build_zoneb_devicename(self._ynca)
                    if self._is_zone_b
                    else build_zone_devicename(self._ynca, self._zone)
                )

                registry.async_update_device(device.id, name=devicename)

        self.schedule_update_ha_state()

    def _get_input_subunits(self) -> Generator[ynca.subunit.SubunitBase]:
        for attribute in sorted(dir(self._ynca)):
            if attribute in ["sys", "main", "zone2", "zone3", "zone4"]:
                continue
            if (attribute_instance := getattr(self._ynca, attribute)) and isinstance(
                attribute_instance, ynca.subunit.SubunitBase
            ):
                yield attribute_instance

    async def async_added_to_hass(self) -> None:
        # Register to catch input renames on SYS
        self._ynca.sys.register_update_callback(self.update_callback)
        self._zone.register_update_callback(self.update_callback)

        for subunit in self._get_input_subunits():
            subunit.register_update_callback(self.update_callback)

    async def async_will_remove_from_hass(self) -> None:
        self._ynca.sys.unregister_update_callback(self.update_callback)
        self._zone.unregister_update_callback(self.update_callback)

        for subunit in self._get_input_subunits():
            subunit.unregister_update_callback(self.update_callback)

    def _get_input_subunit(self) -> ynca.subunit.SubunitBase | None:
        if self._zone.inp is not None:
            return InputHelper.get_subunit_for_input(self._ynca, self._zone.inp)
        return None

    @property
    def state(self) -> MediaPlayerState | None:
        """Return the state of the entity."""
        if self._is_zone_b:
            if self._zone.pwrb is ynca.PwrB.STANDBY:  # type: ignore[attr-defined]
                return MediaPlayerState.OFF
        elif self._zone.pwr is ynca.Pwr.STANDBY:
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
    def volume_level(self) -> float | None:
        """Volume level of the media player (0..1)."""
        if self._is_zone_b:
            if self._zone.zonebvol is not None:  # type: ignore[attr-defined]
                return scale(
                    self._zone.zonebvol,  # type: ignore[attr-defined]
                    [ZONE_MIN_VOLUME, ZONE_MAX_VOLUME],
                    [0, 1],
                )
        elif self._zone.vol is not None:
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
        return None

    @property
    def is_volume_muted(self) -> bool | None:
        """Boolean if volume is currently muted."""
        if self._is_zone_b and self._zone.zonebmute is not None:
            return self._zone.zonebmute != ynca.ZoneBMute.OFF

        if self._zone.mute is not None:
            return self._zone.mute != ynca.Mute.OFF

        return None

    @property
    def source(self) -> str | None:
        """Return the current input source."""
        if self._zone.inp is not None:
            return (
                InputHelper.get_name_of_input(self._ynca, self._zone.inp) or "Unknown"
            )
        return None

    @property
    def source_list(self) -> list[str]:
        """List of available sources."""
        source_mapping = InputHelper.get_source_mapping(self._ynca)

        filtered_sources = [
            name
            for input_, name in source_mapping.items()
            if input_.value not in self._hidden_inputs
        ]

        return sorted(filtered_sources, key=str.lower)

    @property
    def sound_mode(self) -> str | None:
        """Return the current input sound mode."""
        return (
            STRAIGHT if self._zone.straight is ynca.Straight.ON else self._zone.soundprg
        )

    @property
    def sound_mode_list(self) -> list[str] | None:
        """List of available sound modes."""
        sound_modes = []
        if self._zone.straight is not None:
            sound_modes.append(STRAIGHT)
        if self._zone.soundprg:
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

    def _has_limited_playback_controls(self, subunit: ynca.subunit.SubunitBase) -> bool:
        """Indicate if subunit has limited playback control (aka only Play and Stop)."""
        return (
            subunit is self._ynca.netradio
            or subunit is self._ynca.sirius
            or subunit is self._ynca.siriusir
            or subunit is self._ynca.siriusxm
        )

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:  # noqa: C901
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

        if self._zone.soundprg is not None and not self._is_zone_b:
            supported_commands |= MediaPlayerEntityFeature.SELECT_SOUND_MODE

        if input_subunit := self._get_input_subunit():
            if getattr(input_subunit, "playback", None) is not None:
                supported_commands |= MediaPlayerEntityFeature.PLAY
                supported_commands |= MediaPlayerEntityFeature.STOP
                if not self._has_limited_playback_controls(input_subunit):
                    if input_subunit is not self._ynca.usb:
                        supported_commands |= MediaPlayerEntityFeature.PAUSE
                    supported_commands |= MediaPlayerEntityFeature.NEXT_TRACK
                    supported_commands |= MediaPlayerEntityFeature.PREVIOUS_TRACK
            if getattr(input_subunit, "repeat", None) is not None:
                supported_commands |= MediaPlayerEntityFeature.REPEAT_SET
            if getattr(input_subunit, "shuffle", None) is not None:
                supported_commands |= MediaPlayerEntityFeature.SHUFFLE_SET

        if self._has_subunit_that_supports_presets():
            supported_commands |= MediaPlayerEntityFeature.BROWSE_MEDIA
            supported_commands |= MediaPlayerEntityFeature.PLAY_MEDIA

        return supported_commands

    def _has_subunit_that_supports_presets(self) -> bool:
        source_mapping = InputHelper.get_source_mapping(self._ynca)

        for input_ in source_mapping:
            if input_.value not in self._hidden_inputs and (
                subunit := InputHelper.get_subunit_for_input(self._ynca, input_)
            ):
                if hasattr(subunit, "preset"):
                    return True
                # also covers fmpreset since on the same subunit
                if hasattr(subunit, "dabpreset"):
                    return True
        return False

    def turn_on(self) -> None:
        """Turn the media player on."""
        if self._is_zone_b:
            self._zone.pwrb = ynca.PwrB.ON  # type: ignore[attr-defined]
        else:
            self._zone.pwr = ynca.Pwr.ON

    def turn_off(self) -> None:
        """Turn off media player."""
        if self._is_zone_b:
            self._zone.pwrb = ynca.PwrB.STANDBY  # type: ignore[attr-defined]
        else:
            self._zone.pwr = ynca.Pwr.STANDBY

    def set_volume_level(self, volume: float) -> None:
        """Set volume level, convert range from 0..1."""
        if self._is_zone_b:
            self._zone.zonebvol = scale(  # type: ignore[attr-defined]
                volume,
                [0, 1],
                [ZONE_MIN_VOLUME, ZONE_MAX_VOLUME],
            )
        else:
            self._zone.vol = scale(
                volume,
                [0, 1],
                [
                    ZONE_MIN_VOLUME,
                    (
                        self._zone.maxvol
                        if self._zone.maxvol is not None
                        else ZONE_MAX_VOLUME
                    ),
                ],
            )

    def volume_up(self) -> None:
        """Volume up media player."""
        if self._is_zone_b:
            self._zone.zonebvol_up()  # type: ignore[attr-defined]
        else:
            self._zone.vol_up()

    def volume_down(self) -> None:
        """Volume down media player."""
        if self._is_zone_b:
            self._zone.zonebvol_down()  # type: ignore[attr-defined]
        else:
            self._zone.vol_down()

    def mute_volume(self, mute: bool) -> None:  # noqa: FBT001
        """Mute (true) or unmute (false) media player."""
        if self._is_zone_b:
            self._zone.zonebmute = ynca.ZoneBMute.ON if mute else ynca.ZoneBMute.OFF  # type: ignore[attr-defined]
        else:
            self._zone.mute = ynca.Mute.ON if mute else ynca.Mute.OFF

    def select_source(self, source: str) -> None:
        """Select input source."""
        if input_ := InputHelper.get_input_by_name(self._ynca, source):
            self._zone.inp = input_

    def select_sound_mode(self, sound_mode: str) -> None:
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
    def media_play(self) -> None:
        self._zone.playback(ynca.Playback.PLAY)

    def media_pause(self) -> None:
        self._zone.playback(ynca.Playback.PAUSE)

    def media_stop(self) -> None:
        self._zone.playback(ynca.Playback.STOP)

    def media_next_track(self) -> None:
        self._zone.playback(ynca.Playback.SKIP_FWD)

    def media_previous_track(self) -> None:
        self._zone.playback(ynca.Playback.SKIP_REV)

    @property
    def shuffle(self) -> bool | None:
        """Boolean if shuffle is enabled."""
        if (subunit := self._get_input_subunit()) and (
            shuffle := getattr(subunit, "shuffle", None)
        ):
            return shuffle == ynca.Shuffle.ON
        return None

    def set_shuffle(self, shuffle: bool) -> None:  # noqa: FBT001
        """Enable/disable shuffle mode."""
        self._get_input_subunit().shuffle = (
            ynca.Shuffle.ON if shuffle else ynca.Shuffle.OFF
        )

    @property
    def repeat(self) -> str | None:
        """Return current repeat mode."""
        if (subunit := self._get_input_subunit()) and (
            repeat := getattr(subunit, "repeat", None)
        ):
            if repeat == ynca.Repeat.SINGLE:
                return RepeatMode.ONE
            if repeat == ynca.Repeat.ALL:
                return RepeatMode.ALL
            if repeat == ynca.Repeat.OFF:
                return RepeatMode.OFF
        return None

    def set_repeat(self, repeat: str) -> None:
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
    def media_content_type(self) -> str | None:
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
    def media_title(self) -> str | None:
        """Title of current playing media."""
        if subunit := self._get_input_subunit():
            if song := getattr(subunit, "song", None):
                return song
            if track := getattr(subunit, "track", None):
                return track
            if subunit is self._ynca.dab and subunit.band is ynca.BandDab.DAB:
                return subunit.dabdlslabel or None
        return None

    @property
    def media_artist(self) -> str | None:
        """Artist of current playing media, music track only."""
        if (subunit := self._get_input_subunit()) and (
            artist := getattr(subunit, "artist", None)
        ):
            return artist
        return None

    @property
    def media_album_name(self) -> str | None:
        """Album name of current playing media, music track only."""
        if (subunit := self._get_input_subunit()) and (
            album := getattr(subunit, "album", None)
        ):
            return album
        return None

    @property
    def media_channel(self) -> str | None:  # noqa: PLR0911
        """Channel currently playing."""
        subunit = self._get_input_subunit()
        if not subunit:
            return None

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
                return subunit.dabservicelabel or None

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

        if len(parts) == 2:  # noqa: PLR2004
            subunit_attribute_name = parts[0]
            media_content_id_type = parts[1]

            return self.build_presetlist_media_item(
                subunit_attribute_name, media_content_id_type
            )

        msg = f"Media content id could not be resolved: {media_content_id}"
        raise HomeAssistantError(msg)

    def build_media_root_item(self) -> BrowseMedia:
        children = []

        # Generic presets
        source_mapping = InputHelper.get_source_mapping(self._ynca)
        for input_, name in source_mapping.items():
            if (
                input_.value not in self._hidden_inputs
                and (subunit := InputHelper.get_subunit_for_input(self._ynca, input_))
                and hasattr(subunit, "preset")
            ):
                children.append(
                    self.directory_browse_media_item(
                        name, f"{subunit.id.value.lower()}:presets", []
                    )
                )

        # Presets for DAB Tuner, it has 2 preset lists and uses different attribute names, so add manually
        if self._ynca.dab and ynca.Input.TUNER.value not in self._hidden_inputs:
            children.extend(
                [
                    self.directory_browse_media_item(
                        "TUNER (DAB)", "dab:dabpresets", []
                    ),
                    self.directory_browse_media_item("TUNER (FM)", "dab:fmpresets", []),
                ]
            )

        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id="presets",
            media_content_type="",
            title="Presets",
            can_play=False,
            can_expand=True,
            children=children,
            children_media_class=MediaClass.DIRECTORY,
        )

    def build_presetlist_media_item(
        self, subunit_attribute_name: str, media_content_id_type: str
    ) -> BrowseMedia:
        if media_content_id_type == "dabpresets":
            name = "TUNER (DAB)"
        elif media_content_id_type == "fmpresets":
            name = "TUNER (FM)"
        elif subunit := getattr(self._ynca, subunit_attribute_name, None):
            input_ = InputHelper.get_input_for_subunit(subunit)
            source_mapping = InputHelper.get_source_mapping(self._ynca)
            name = source_mapping.get(input_, source_mapping[input_])

        stripped_media_content_id_type = media_content_id_type[
            :-1
        ]  # Strips the 's' of xyz_presets
        preset_items = [
            BrowseMedia(
                media_class=MediaClass.MUSIC,
                media_content_id=f"{subunit_attribute_name}:{stripped_media_content_id_type}:{i + 1}",
                media_content_type=MediaType.MUSIC,
                title=f"Preset {i + 1}",
                can_play=True,
                can_expand=False,
            )
            for i in range(NUM_PRESETS)
        ]

        return self.directory_browse_media_item(
            name, f"{subunit_attribute_name}:{media_content_id_type}", preset_items
        )

    def directory_browse_media_item(
        self, name: str, media_content_id: str, presets: list[BrowseMedia]
    ) -> BrowseMedia:
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
        _enqueue: MediaPlayerEnqueue | None = None,
        _announce: bool | None = None,
        **_kwargs: Any,
    ) -> None:
        LOGGER.debug("media type, id: %s, %s", media_type, media_id)

        """Play a piece of media."""
        if media_source.is_media_source_id(media_id):
            msg = f"Media sources are not supported by this media player: {media_id}"
            raise HomeAssistantError(msg)

        # Expected media_id format is: subunit:preset:#

        parts = media_id.split(":")
        if len(parts) != 3:  # noqa: PLR2004
            msg = f"Malformed media id: {media_id}"
            raise HomeAssistantError(msg)

        media_id_subunit = parts[0]
        media_id_command = parts[1]
        media_id_preset_id = parts[2]

        self.validate_media_id(
            media_id, media_id_subunit, media_id_command, media_id_preset_id
        )

        # Apply media_id to receiver

        # First turn on if needed
        if self._is_zone_b:
            if self._zone.pwrb is ynca.PwrB.STANDBY:  # type: ignore[attr-defined]
                self._zone.pwrb = ynca.PwrB.ON  # type: ignore[attr-defined]
        elif self._zone.pwr is ynca.Pwr.STANDBY:
            self._zone.pwr = ynca.Pwr.ON

        # Switch input if needed
        subunit = getattr(self._ynca, media_id_subunit)
        input_ = InputHelper.get_input_for_subunit(subunit)
        if self._zone.inp is not input_:
            self._zone.inp = input_

            # Tuner input needs some time before it is possible to set the preset
            # it gets ignored otherwise
            # see https://github.com/mvdwetering/yamaha_ynca/issues/271
            if input_ == ynca.Input.TUNER:
                await asyncio.sleep(1.0)

        setattr(subunit, media_id_command, int(media_id_preset_id))

    def validate_media_id(
        self,
        media_id: str,
        media_id_subunit: str,
        media_id_command: str,
        media_id_preset_id: str,
    ) -> None:
        if not hasattr(self._ynca, media_id_subunit):
            msg = f"Malformed media id: {media_id}"
            raise HomeAssistantError(msg)

        if media_id_command not in ["preset", "fmpreset", "dabpreset"]:
            msg = f"Malformed media id: {media_id}"
            raise HomeAssistantError(msg)

        preset_id = 0
        try:
            preset_id = int(media_id_preset_id)
        except ValueError:
            msg = f"Malformed preset: {media_id}"
            raise HomeAssistantError(msg) from None

        if preset_id < 1 or preset_id > NUM_PRESETS:
            msg = "Preset id out of range"
            raise HomeAssistantError(msg) from None

    def store_preset(self, preset_id: int) -> None:
        if (
            subunit := InputHelper.get_subunit_for_input(self._ynca, self._zone.inp)
        ) and hasattr(subunit, "mem"):
            subunit.mem(preset_id)
            return

        LOGGER.warning(
            "Unable to store preset %s for current input %s",
            preset_id,
            self._zone.inp.value if self._zone.inp else "None",
        )


class YamahaYncaZoneB(YamahaYncaZone):
    """ZoneB is a limited subset of a normal zone.

    Basically it only supports volume and mute.
    Input is same as MAIN zone.

    Since it uses same Input it also provides control and state for that input
    so it seems easier to build the zoneb specific parts into the normal mediaplayer
    which will also make it less likely that ZoneB implementations are forgotten when updating features
    """

    _ZONENAME_FUNCTION = "ZONEBNAME"

    def __init__(
        self,
        receiver_unique_id: str,
        ynca: ynca.YncaApi,
        hidden_inputs: list[str],
    ) -> None:
        super().__init__(
            receiver_unique_id, ynca, ynca.main, hidden_inputs, [], is_zone_b=True
        )

    def update_callback(self, function: str, value: Any) -> None:
        # Just forward to normal zone handling for now
        # Might result in a few too many updates, but should not be a lot
        super().update_callback(function, value)
