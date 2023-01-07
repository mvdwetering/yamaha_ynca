"""The Yamaha (YNCA) integration migrations."""
from __future__ import annotations

import ynca

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry, entity_registry

from .const import (
    CONF_HIDDEN_SOUND_MODES,
    DOMAIN,
    LOGGER,
)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    from_version = config_entry.version
    LOGGER.debug("Migrating from version %s", from_version)

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

    # When adding new migrations do _not_ forget
    # to increase the VERSION of the YamahaYncaConfigFlow
    # and update the version in `setup_integration`

    LOGGER.info(
        "Migration of ConfigEntry from version %s to version %s successful",
        from_version,
        config_entry.version,
    )

    return True


def migrate_v6_to_v7(hass: HomeAssistant, config_entry: ConfigEntry):
    # Migrate the current single device (is whole receiver)
    # to the device for MAIN zone to keep device automations working
    # Device automations for Zone2, Zone3 or Zone4 parts will break unfortunately

    old_identifiers = {(DOMAIN, f"{config_entry.entry_id}")}
    new_identifiers = {(DOMAIN, f"{config_entry.entry_id}_MAIN")}

    registry = device_registry.async_get(hass)
    if device_entry := registry.async_get_device(identifiers=old_identifiers):
        registry.async_update_device(device_entry.id, new_identifiers=new_identifiers)

    config_entry.version = 7
    hass.config_entries.async_update_entry(config_entry, data=config_entry.data)


def migrate_v5_to_v6(hass: HomeAssistant, config_entry: ConfigEntry):
    # Migrate format of options from `hidden_inputs_<ZONE>` to having a dict per zone
    # Add modelname explictly to data, copy from title

    old_options = dict(config_entry.options)  # Convert to dict to be able to use .get
    new_options = {}

    if hidden_sound_modes := old_options.get("hidden_sound_modes", None):
        new_options["hidden_sound_modes"] = hidden_sound_modes

    for zone_id in ["MAIN", "ZONE2", "ZONE3", "ZONE4"]:
        if hidden_inputs := old_options.get(f"hidden_inputs_{zone_id}", None):
            zone_settings = {}
            zone_settings["hidden_inputs"] = hidden_inputs
            new_options[zone_id] = zone_settings

    new_data = {**config_entry.data}
    new_data["modelname"] = config_entry.title

    config_entry.version = 6
    hass.config_entries.async_update_entry(
        config_entry, data=new_data, options=new_options
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

    config_entry.version = 5
    hass.config_entries.async_update_entry(config_entry, data=new)


def migrate_v3_to_v4(hass: HomeAssistant, config_entry: ConfigEntry):
    # Changed how hidden soundmodes are stored
    # Used to be the enum name, now it is the value

    options = dict(config_entry.options)
    if old_hidden_soundmodes := options.get(CONF_HIDDEN_SOUND_MODES, None):
        new_hidden_soundmodes = []
        for old_hidden_soundmode in old_hidden_soundmodes:
            try:
                new_hidden_soundmodes.append(ynca.SoundPrg[old_hidden_soundmode].value)
            except KeyError:
                pass
        options[CONF_HIDDEN_SOUND_MODES] = new_hidden_soundmodes

    config_entry.version = 4
    hass.config_entries.async_update_entry(
        config_entry, data=config_entry.data, options=options
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

    config_entry.version = 3
    hass.config_entries.async_update_entry(config_entry, data=config_entry.data)


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

    config_entry.version = 2
    hass.config_entries.async_update_entry(config_entry, data=new)
