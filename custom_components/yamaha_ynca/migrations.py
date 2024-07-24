"""The Yamaha (YNCA) integration migrations."""

from __future__ import annotations

import ynca

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, entity_registry

from .const import CONF_HIDDEN_SOUND_MODES, DOMAIN, LOGGER
from .helpers import receiver_requires_audio_input_workaround


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    from_version = config_entry.version
    from_minor_version = config_entry.minor_version
    LOGGER.debug("Migrating from version %s.%s", from_version, from_minor_version)

    if config_entry.version == 1:
        migrate_v1_to_v2(hass, config_entry)

    if config_entry.version == 2:
        migrate_v2_to_v3(hass, config_entry)

    if config_entry.version == 3:
        migrate_v3_to_v4(hass, config_entry)

    if config_entry.version == 4:
        migrate_v4_to_v5(hass, config_entry)

    if config_entry.version == 5:
        migrate_v5_to_v6(hass, config_entry)

    if config_entry.version == 6:
        migrate_v6_to_v7(hass, config_entry)

    if config_entry.version == 7:
        if config_entry.minor_version == 1:
            migrate_v7_1_to_v7_2(hass, config_entry)
        if config_entry.minor_version == 2:
            migrate_v7_2_to_v7_3(hass, config_entry)
        if config_entry.minor_version == 3:
            migrate_v7_3_to_v7_4(hass, config_entry)
        if config_entry.minor_version == 4:
            migrate_v7_4_to_v7_5(hass, config_entry)

    # When adding new migrations do _not_ forget
    # to increase the VERSION of the YamahaYncaConfigFlow
    # and update the version in `setup_integration`

    LOGGER.info(
        "Migration of ConfigEntry from version %s.%s to version %s.%s successful",
        from_version,
        from_minor_version,
        config_entry.version,
        config_entry.minor_version,
    )

    return True


def migrate_v7_4_to_v7_5(hass: HomeAssistant, config_entry: ConfigEntry):
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


def migrate_v7_3_to_v7_4(hass: HomeAssistant, config_entry: ConfigEntry):
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


def migrate_v7_2_to_v7_3(hass: HomeAssistant, config_entry: ConfigEntry):
    options = dict(config_entry.options)  # Convert to dict to be able to use .get

    # Check if twochdecoder entity exists for this entry
    # If so then set options to PLII(X) and NEO surround decoders
    # Otherwise do nothing (not set will result in all options being listed)

    registry = entity_registry.async_get(hass)
    entities = entity_registry.async_entries_for_config_entry(
        registry, config_entry.entry_id
    )

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


def migrate_v7_1_to_v7_2(hass: HomeAssistant, config_entry: ConfigEntry):
    options = dict(config_entry.options)  # Convert to dict to be able to use .get

    # Hide new AUDIO input for existing users that do not use impacted receivers
    # Code is robust against unsupported inputs being listed in "hidden_input"s
    if not receiver_requires_audio_input_workaround(config_entry.data["modelname"]):
        # Upgrading from _really_ old version might not have zones key
        if "zones" in config_entry.data:
            for zone_id in config_entry.data["zones"]:
                options[zone_id] = options.get(zone_id, {})
                options[zone_id]["hidden_inputs"] = options[zone_id].get(
                    "hidden_inputs", []
                )
                options[zone_id]["hidden_inputs"].append("AUDIO")

    hass.config_entries.async_update_entry(
        config_entry, options=options, minor_version=2
    )


def migrate_v6_to_v7(hass: HomeAssistant, config_entry: ConfigEntry):
    # Migrate the current single device (is whole receiver)
    # to the device for MAIN zone to keep device automations working
    # Device automations for Zone2, Zone3 or Zone4 parts will break unfortunately

    old_identifiers = {(DOMAIN, f"{config_entry.entry_id}")}
    new_identifiers = {(DOMAIN, f"{config_entry.entry_id}_MAIN")}

    registry = device_registry.async_get(hass)
    if device_entry := registry.async_get_device(identifiers=old_identifiers):
        registry.async_update_device(device_entry.id, new_identifiers=new_identifiers)

    hass.config_entries.async_update_entry(
        config_entry, data=config_entry.data, version=7, minor_version=1
    )


def migrate_v5_to_v6(hass: HomeAssistant, config_entry: ConfigEntry):
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


def migrate_v4_to_v5(hass: HomeAssistant, config_entry: ConfigEntry):
    # For "network" type the IP address or host is stored as a socket:// url directly
    # Convert serial urls using the old "network" format
    # Re-uses the old `serial_url_from_user_input` helper function
    import ipaddress

    def serial_url_from_user_input(user_input: str) -> str:
        # Try and see if an IP address was passed in
        # and convert to a socket url
        try:
            parts = user_input.split(":")
            if len(parts) <= 2:
                ipaddress.ip_address(parts[0])  # Throws when invalid IP
                port = int(parts[1]) if len(parts) == 2 else 50000
                return f"socket://{parts[0]}:{port}"
        except ValueError:
            pass

        return user_input

    new = {**config_entry.data}
    new["serial_url"] = serial_url_from_user_input(config_entry.data["serial_url"])

    hass.config_entries.async_update_entry(
        config_entry, data=new, version=5, minor_version=1
    )


def migrate_v3_to_v4(hass: HomeAssistant, config_entry: ConfigEntry):
    # Changed how hidden soundmodes are stored
    # Used to be the enum name, now it is the value

    options = dict(config_entry.options)
    if old_hidden_soundmodes := options.get(CONF_HIDDEN_SOUND_MODES):
        new_hidden_soundmodes = []
        for old_hidden_soundmode in old_hidden_soundmodes:
            try:
                new_hidden_soundmodes.append(ynca.SoundPrg[old_hidden_soundmode].value)
            except KeyError:
                pass
        options[CONF_HIDDEN_SOUND_MODES] = new_hidden_soundmodes

    hass.config_entries.async_update_entry(
        config_entry,
        data=config_entry.data,
        options=options,
        version=4,
        minor_version=1,
    )


def migrate_v2_to_v3(hass: HomeAssistant, config_entry: ConfigEntry):
    # Scene entities are replaced by Button entities
    # (scenes limited to a single devics seem a bit weird)
    # cleanup the scene entities so the user does not have to
    registry = entity_registry.async_get(hass)
    entities = entity_registry.async_entries_for_config_entry(
        registry, config_entry.entry_id
    )
    for entity in entities:
        if entity.domain == Platform.SCENE:
            registry.async_remove(entity.entity_id)

    hass.config_entries.async_update_entry(
        config_entry, data=config_entry.data, version=3, minor_version=1
    )


def migrate_v1_to_v2(hass: HomeAssistant, config_entry: ConfigEntry):
    # Button entities are replaced by scene entities
    # cleanup the button entities so the user does not have to
    registry = entity_registry.async_get(hass)
    entities = entity_registry.async_entries_for_config_entry(
        registry, config_entry.entry_id
    )
    for entity in entities:
        if entity.domain == Platform.BUTTON:
            registry.async_remove(entity.entity_id)

    # Rename to `serial_url` for consistency
    new = {**config_entry.data}
    new["serial_url"] = new.pop("serial_port")

    hass.config_entries.async_update_entry(
        config_entry, data=new, version=2, minor_version=1
    )
