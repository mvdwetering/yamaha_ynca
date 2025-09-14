"""The Yamaha (YNCA) integration migrations."""

from __future__ import annotations

import contextlib
from enum import StrEnum, unique
from typing import TYPE_CHECKING

from homeassistant.helpers import device_registry as dr, entity_registry as er

import ynca

from .config_flow import YamahaYncaConfigFlow
from .const import DATA_MODELNAME, DOMAIN, LOGGER
from .helpers import receiver_requires_audio_input_workaround

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

LEGACY_CONF_HIDDEN_INPUTS = "hidden_inputs"
LEGACY_CONF_HIDDEN_SOUND_MODES = "hidden_sound_modes"


# This is a copy of the enum in ynca package so that during migration we have a stable enum that does not change over time
@unique
class YncaSoundPrgCopy(StrEnum):
    HALL_IN_MUNICH = "Hall in Munich"
    HALL_IN_VIENNA = "Hall in Vienna"
    HALL_IN_AMSTERDAM = "Hall in Amsterdam"
    CHURCH_IN_FREIBURG = "Church in Freiburg"
    CHURCH_IN_ROYAUMONT = "Church in Royaumont"
    CHAMBER = "Chamber"
    VILLAGE_VANGUARD = "Village Vanguard"
    WAREHOUSE_LOFT = "Warehouse Loft"
    CELLAR_CLUB = "Cellar Club"
    THE_ROXY_THEATRE = "The Roxy Theatre"
    THE_BOTTOM_LINE = "The Bottom Line"
    SPORTS = "Sports"
    ACTION_GAME = "Action Game"
    ROLEPLAYING_GAME = "Roleplaying Game"
    MUSIC_VIDEO = "Music Video"
    RECITAL_OPERA = "Recital/Opera"
    STANDARD = "Standard"
    SPECTACLE = "Spectacle"
    SCI_FI = "Sci-Fi"
    ADVENTURE = "Adventure"
    DRAMA = "Drama"
    MONO_MOVIE = "Mono Movie"
    TWO_CH_STEREO = "2ch Stereo"
    FIVE_CH_STEREO = "5ch Stereo"
    SEVEN_CH_STEREO = "7ch Stereo"
    NINE_CH_STEREO = "9ch Stereo"
    SURROUND_DECODER = "Surround Decoder"
    ALL_CH_STEREO = "All-Ch Stereo"
    ENHANCED = "Enhanced"


# This is a copy of the enum in ynca package so that during migration we have a stable enum that does not change over time
@unique
class YncaInputCopy(StrEnum):
    # Inputs with connectors on the receiver
    AUDIO = "AUDIO"  # This input is kind of weird since it is not reported by INPNAME=?
    AUDIO1 = "AUDIO1"
    AUDIO2 = "AUDIO2"
    AUDIO3 = "AUDIO3"
    AUDIO4 = "AUDIO4"
    AUDIO5 = "AUDIO5"
    AV1 = "AV1"
    AV2 = "AV2"
    AV3 = "AV3"
    AV4 = "AV4"
    AV5 = "AV5"
    AV6 = "AV6"
    AV7 = "AV7"
    DOCK = "DOCK"  # Selecting DOCK selects iPod for me, might depend on what dock is attached (I have no dock to test)
    HDMI1 = "HDMI1"
    HDMI2 = "HDMI2"
    HDMI3 = "HDMI3"
    HDMI4 = "HDMI4"
    HDMI5 = "HDMI5"
    HDMI6 = "HDMI6"
    HDMI7 = "HDMI7"
    MULTICH = "MULTI CH"
    OPTICAL1 = "OPTICAL1"
    OPTICAL2 = "OPTICAL2"
    PHONO = "PHONO"
    TV = "TV"
    VAUX = "V-AUX"

    # Inputs provided by subunits
    AIRPLAY = "AirPlay"
    BLUETOOTH = "Bluetooth"
    IPOD = "iPod"
    IPOD_USB = "iPod (USB)"
    NAPSTER = "Napster"
    NETRADIO = "NET RADIO"
    PANDORA = "Pandora"
    PC = "PC"
    RHAPSODY = "Rhapsody"
    SERVER = "SERVER"
    SIRIUS = "SIRIUS"
    SIRIUS_IR = "SIRIUS InternetRadio"
    SIRIUS_XM = "SiriusXM"
    SPOTIFY = "Spotify"
    TUNER = "TUNER"  # AM/FM tuner (@TUN) or DAB/FM tuner (@DAB)
    UAW = "UAW"
    USB = "USB"


async def async_migrate_entry(  # noqa: C901, PLR0912
    hass: HomeAssistant, config_entry: ConfigEntry
) -> bool:
    """Migrate old entry."""
    from_version = config_entry.version
    from_minor_version = config_entry.minor_version
    LOGGER.debug("Migrating from version %s.%s", from_version, from_minor_version)

    if config_entry.version > YamahaYncaConfigFlow.VERSION:
        # This means the user has downgraded from a future version
        return False

    if config_entry.version == 1:
        migrate_v1_to_v2(hass, config_entry)

    if config_entry.version == 2:  # noqa: PLR2004
        migrate_v2_to_v3(hass, config_entry)

    if config_entry.version == 3:  # noqa: PLR2004
        migrate_v3_to_v4(hass, config_entry)

    if config_entry.version == 4:  # noqa: PLR2004
        migrate_v4_to_v5(hass, config_entry)

    if config_entry.version == 5:  # noqa: PLR2004
        migrate_v5_to_v6(hass, config_entry)

    if config_entry.version == 6:  # noqa: PLR2004
        migrate_v6_to_v7(hass, config_entry)

    if config_entry.version == 7:  # noqa: PLR2004
        if config_entry.minor_version == 1:
            migrate_v7_1_to_v7_2(hass, config_entry)
        if config_entry.minor_version == 2:  # noqa: PLR2004
            migrate_v7_2_to_v7_3(hass, config_entry)
        if config_entry.minor_version == 3:  # noqa: PLR2004
            migrate_v7_3_to_v7_4(hass, config_entry)
        if config_entry.minor_version == 4:  # noqa: PLR2004
            migrate_v7_4_to_v7_5(hass, config_entry)
        if config_entry.minor_version == 5:  # noqa: PLR2004
            migrate_v7_5_to_v7_6(hass, config_entry)
        if config_entry.minor_version == 6:  # noqa: PLR2004
            migrate_v7_6_to_v7_7(hass, config_entry)
        if config_entry.minor_version == 7:  # noqa: PLR2004
            migrate_v7_7_to_v7_8(hass, config_entry)

    # When adding new migrations do _not_ forget
    # to increase the VERSION of the YamahaYncaConfigFlow
    # and update the version in `create_mock_config_entry`

    LOGGER.info(
        "Migration of ConfigEntry from version %s.%s to version %s.%s successful",
        from_version,
        from_minor_version,
        config_entry.version,
        config_entry.minor_version,
    )

    return True


def migrate_v7_7_to_v7_8(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    options = dict(config_entry.options)  # Convert to dict to be able to use .get

    # Switch from using "hidden_inputs" to "selected_inputs"
    all_inputs = [input_.value for input_ in YncaInputCopy]

    for zone_id in ["MAIN", "ZONE2", "ZONE3", "ZONE4"]:
        if zone_options := options.get(zone_id):
            hidden_inputs = zone_options.get(LEGACY_CONF_HIDDEN_INPUTS, [])

            selected_inputs = list(set(all_inputs) - set(hidden_inputs))

            zone_options["selected_inputs"] = selected_inputs
            zone_options.pop(LEGACY_CONF_HIDDEN_INPUTS, None)

    hass.config_entries.async_update_entry(
        config_entry, options=options, minor_version=8
    )


def migrate_v7_6_to_v7_7(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    options = dict(config_entry.options)  # Convert to dict to be able to use .get

    # Switch from using "hidden_sound_modes" to "selected_sound_modes"
    all_sound_modes = [sound_mode.value for sound_mode in YncaSoundPrgCopy]
    all_sound_modes.sort(key=str.lower)

    unsupported_sound_modes = []
    if modelinfo := ynca.YncaModelInfo.get(config_entry.data[DATA_MODELNAME]):
        modelinfo_soundprgs = [soundprg.value for soundprg in modelinfo.soundprg]
        unsupported_sound_modes = list(set(all_sound_modes) - set(modelinfo_soundprgs))

    hidden_sound_modes = (
        options.get(LEGACY_CONF_HIDDEN_SOUND_MODES, []) + unsupported_sound_modes
    )

    selected_sound_modes = list(set(all_sound_modes) - set(hidden_sound_modes))

    options["selected_sound_modes"] = selected_sound_modes
    options.pop(LEGACY_CONF_HIDDEN_SOUND_MODES, None)

    hass.config_entries.async_update_entry(
        config_entry, options=options, minor_version=7
    )


def migrate_v7_5_to_v7_6(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    options = dict(config_entry.options)  # Convert to dict to be able to use .get

    # Hide new TV input for existing users
    # Code is robust against unsupported inputs being listed in "hidden_input"s

    # Upgrading from _really_ old version might not have zones key
    if "zones" in config_entry.data:
        for zone_id in config_entry.data["zones"]:
            options[zone_id] = options.get(zone_id, {})
            options[zone_id]["hidden_inputs"] = options[zone_id].get(
                "hidden_inputs", []
            )
            options[zone_id]["hidden_inputs"].extend(["OPTICAL1", "OPTICAL2"])

    hass.config_entries.async_update_entry(
        config_entry, options=options, minor_version=6
    )


def migrate_v7_4_to_v7_5(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    options = dict(config_entry.options)  # Convert to dict to be able to use .get

    # Hide new TV input for existing users
    # Code is robust against unsupported inputs being listed in "hidden_input"s

    # Upgrading from _really_ old version might not have zones key
    if "zones" in config_entry.data:
        for zone_id in config_entry.data["zones"]:
            options[zone_id] = options.get(zone_id, {})
            options[zone_id]["hidden_inputs"] = options[zone_id].get(
                "hidden_inputs", []
            )
            options[zone_id]["hidden_inputs"].append("TV")

    hass.config_entries.async_update_entry(
        config_entry, options=options, minor_version=5
    )


def migrate_v7_3_to_v7_4(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    options = dict(config_entry.options)  # Convert to dict to be able to use .get

    # Hide new AUDIO5 input for existing users
    # Code is robust against unsupported inputs being listed in "hidden_input"s

    # Upgrading from _really_ old version might not have zones key
    if "zones" in config_entry.data:
        for zone_id in config_entry.data["zones"]:
            options[zone_id] = options.get(zone_id, {})
            options[zone_id]["hidden_inputs"] = options[zone_id].get(
                "hidden_inputs", []
            )
            options[zone_id]["hidden_inputs"].append("AUDIO5")

    hass.config_entries.async_update_entry(
        config_entry, options=options, minor_version=4
    )


def migrate_v7_2_to_v7_3(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    options = dict(config_entry.options)  # Convert to dict to be able to use .get

    # Check if twochdecoder entity exists for this entry
    # If so then set options to PLII(X) and NEO surround decoders
    # Otherwise do nothing (not set will result in all options being listed)

    registry = er.async_get(hass)
    entities = er.async_entries_for_config_entry(registry, config_entry.entry_id)

    entity_unique_id = f"{config_entry.entry_id}_MAIN_twochdecoder"

    for entity in entities:
        if entity.unique_id == entity_unique_id:
            options["selected_surround_decoders"] = [
                "dolby_pl",
                "dolby_plii_game",
                "dolby_plii_movie",
                "dolby_plii_music",
                "dts_neo_6_cinema",
                "dts_neo_6_music",
            ]

    hass.config_entries.async_update_entry(
        config_entry, options=options, minor_version=3
    )


def migrate_v7_1_to_v7_2(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    options = dict(config_entry.options)  # Convert to dict to be able to use .get

    # Hide new AUDIO input for existing users that do not use impacted receivers
    # Code is robust against unsupported inputs being listed in "hidden_input"s
    # Upgrading from _really_ old version might not have zones key
    if (
        not receiver_requires_audio_input_workaround(config_entry.data["modelname"])
        and "zones" in config_entry.data
    ):
        for zone_id in config_entry.data["zones"]:
            options[zone_id] = options.get(zone_id, {})
            options[zone_id]["hidden_inputs"] = options[zone_id].get(
                "hidden_inputs", []
            )
            options[zone_id]["hidden_inputs"].append("AUDIO")

    hass.config_entries.async_update_entry(
        config_entry, options=options, minor_version=2
    )


def migrate_v6_to_v7(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    # Migrate the current single device (is whole receiver)
    # to the device for MAIN zone to keep device automations working
    # Device automations for Zone2, Zone3 or Zone4 parts will break unfortunately

    old_identifiers = {(DOMAIN, f"{config_entry.entry_id}")}
    new_identifiers = {(DOMAIN, f"{config_entry.entry_id}_MAIN")}

    registry = dr.async_get(hass)
    if device_entry := registry.async_get_device(identifiers=old_identifiers):
        registry.async_update_device(device_entry.id, new_identifiers=new_identifiers)

    hass.config_entries.async_update_entry(
        config_entry, data=config_entry.data, version=7, minor_version=1
    )


def migrate_v5_to_v6(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    # Migrate format of options from `hidden_inputs_<ZONE>` to having a dict per zone
    # Add modelname explictly to data, copy from title

    old_options = dict(config_entry.options)  # Convert to dict to be able to use .get
    new_options = {}

    if hidden_sound_modes := old_options.get("hidden_sound_modes"):
        new_options["hidden_sound_modes"] = hidden_sound_modes

    for zone_id in ["MAIN", "ZONE2", "ZONE3", "ZONE4"]:
        if hidden_inputs := old_options.get(f"hidden_inputs_{zone_id}", None):
            zone_settings = {}
            zone_settings["hidden_inputs"] = hidden_inputs
            new_options[zone_id] = zone_settings

    new_data = {**config_entry.data}
    new_data["modelname"] = config_entry.title

    hass.config_entries.async_update_entry(
        config_entry, data=new_data, options=new_options, version=6, minor_version=1
    )


def migrate_v4_to_v5(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    # For "network" type the IP address or host is stored as a socket:// url directly
    # Convert serial urls using the old "network" format
    # Re-uses the old `serial_url_from_user_input` helper function
    import ipaddress

    def serial_url_from_user_input(user_input: str) -> str:
        # Try and see if an IP address was passed in
        # and convert to a socket url
        try:
            parts = user_input.split(":")
            if len(parts) <= 2:  # noqa: PLR2004
                ipaddress.ip_address(parts[0])  # Throws when invalid IP
                port = int(parts[1]) if len(parts) == 2 else 50000  # noqa: PLR2004
                return f"socket://{parts[0]}:{port}"
        except ValueError:
            pass

        return user_input

    new = {**config_entry.data}
    new["serial_url"] = serial_url_from_user_input(config_entry.data["serial_url"])

    hass.config_entries.async_update_entry(
        config_entry, data=new, version=5, minor_version=1
    )


def migrate_v3_to_v4(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    # Changed how hidden soundmodes are stored
    # Used to be the enum name, now it is the value

    options = dict(config_entry.options)
    if old_hidden_soundmodes := options.get(LEGACY_CONF_HIDDEN_SOUND_MODES):
        new_hidden_soundmodes = []
        for old_hidden_soundmode in old_hidden_soundmodes:
            with contextlib.suppress(KeyError):
                new_hidden_soundmodes.append(ynca.SoundPrg[old_hidden_soundmode].value)
        options[LEGACY_CONF_HIDDEN_SOUND_MODES] = new_hidden_soundmodes

    hass.config_entries.async_update_entry(
        config_entry,
        data=config_entry.data,
        options=options,
        version=4,
        minor_version=1,
    )


def migrate_v2_to_v3(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    # Scene entities are replaced by Button entities
    # (scenes limited to a single devics seem a bit weird)
    # The code to cleanup has been removed as tests started failing and fixing it was too much work

    hass.config_entries.async_update_entry(
        config_entry, data=config_entry.data, version=3, minor_version=1
    )


def migrate_v1_to_v2(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    # Button entities are replaced by scene entities
    # The code to cleanup has been removed as tests started failing and fixing it was too much work

    # Rename to `serial_url` for consistency
    new = {**config_entry.data}
    new["serial_url"] = new.pop("serial_port")

    hass.config_entries.async_update_entry(
        config_entry, data=new, version=2, minor_version=1
    )
