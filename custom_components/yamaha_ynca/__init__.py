"""The Yamaha (YNCA) integration."""
from __future__ import annotations

import asyncio
from enum import unique
import re
from typing import List

import ynca

from homeassistant.config_entries import ConfigEntry, OperationNotAllowed
from homeassistant.const import Platform
from homeassistant.core import DOMAIN as HA_DOMAIN, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry, entity_registry
from homeassistant.helpers.service import ServiceCall, async_extract_config_entry_ids

from .const import (
    COMMUNICATION_LOG_SIZE,
    CONF_HIDDEN_SOUND_MODES,
    CONF_SERIAL_URL,
    DATA_ZONES,
    DOMAIN,
    LOGGER,
    MANUFACTURER_NAME,
    ZONE_ATTRIBUTE_NAMES,
)
from .helpers import DomainEntryData

PLATFORMS: List[Platform] = [
    Platform.MEDIA_PLAYER,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
]

SERVICE_SEND_RAW_YNCA = "send_raw_ynca"


async def update_device_registry(
    hass: HomeAssistant, config_entry: ConfigEntry, receiver: ynca.YncaApi
):
    assert receiver.sys is not None

    # Configuration URL for devices connected through IP
    configuration_url = None
    if matches := re.match(
        r"socket:\/\/(.+):\d+",  # Extract IP or hostname
        config_entry.data[CONF_SERIAL_URL],
    ):
        configuration_url = f"http://{matches[1]}"

    # Add device explicitly to registry so other entities just have to report the identifier to link up
    registry = device_registry.async_get(hass)

    for zone_attr_name in ZONE_ATTRIBUTE_NAMES:
        if zone_subunit := getattr(receiver, zone_attr_name):

            devicename = f"{receiver.sys.modelname} {zone_subunit.id}"
            if (
                zone_subunit.zonename
                and zone_subunit.zonename.lower() != zone_subunit.id.lower()
            ):
                # Prefer user defined name over "MODEL ZONE" naming
                devicename = zone_subunit.zonename

            registry.async_get_or_create(
                config_entry_id=config_entry.entry_id,
                identifiers={(DOMAIN, f"{config_entry.entry_id}_{zone_subunit.id}")},
                manufacturer=MANUFACTURER_NAME,
                name=devicename,
                model=receiver.sys.modelname,
                sw_version=receiver.sys.version,
                configuration_url=configuration_url,
            )


async def update_configentry(
    hass: HomeAssistant, config_entry: ConfigEntry, receiver: ynca.YncaApi
):
    assert receiver.sys is not None

    # Older configurations setup before 5.3.0+ will not have zones data filled
    # So fill it when not set already
    # If not set, options will not show for zones
    if DATA_ZONES not in config_entry.data:
        new_data = dict(config_entry.data)
        zones = []
        for zone_attr in ZONE_ATTRIBUTE_NAMES:
            if getattr(receiver, zone_attr, None):
                zones.append(zone_attr.upper())
        new_data[DATA_ZONES] = zones
        hass.config_entries.async_update_entry(config_entry, data=new_data)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    from_version = config_entry.version
    LOGGER.debug("Migrating from version %s", from_version)

    if config_entry.version == 1:
        migrate_v1(hass, config_entry)

    if config_entry.version == 2:
        migrate_v2(hass, config_entry)

    if config_entry.version == 3:
        migrate_v3(hass, config_entry)

    if config_entry.version == 4:
        migrate_v4(hass, config_entry)

    if config_entry.version == 5:
        migrate_v5(hass, config_entry)

    if config_entry.version == 6:
        migrate_v6(hass, config_entry)

    # When adding new migrations do _not_ forget
    # to increase the VERSION of the YamahaYncaConfigFlow
    # and update the version in `setup_integration`

    LOGGER.info(
        "Migration of ConfigEntry from version %s to version %s successful",
        from_version,
        config_entry.version,
    )

    return True


def migrate_v6(hass: HomeAssistant, config_entry: ConfigEntry):
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


def migrate_v5(hass: HomeAssistant, config_entry: ConfigEntry):
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


def migrate_v4(hass: HomeAssistant, config_entry: ConfigEntry):
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


def migrate_v3(hass: HomeAssistant, config_entry: ConfigEntry):
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


def migrate_v2(hass: HomeAssistant, config_entry: ConfigEntry):
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


def migrate_v1(hass: HomeAssistant, config_entry: ConfigEntry):
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


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    # Just reload the integration on update. Crude, but it works
    await hass.config_entries.async_reload(entry.entry_id)


async def async_handle_send_raw_ynca(hass: HomeAssistant, call: ServiceCall):
    config_entry_ids = await async_extract_config_entry_ids(hass, call)
    for config_entry_id in config_entry_ids:
        if domain_entry_info := hass.data[DOMAIN].get(config_entry_id, None):
            domain_entry_info.api.send_raw(call.data.get("raw_data"))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Yamaha (YNCA) from a config entry."""

    def initialize_ynca(ynca_receiver: ynca.YncaApi):
        try:
            # Sync function taking a long time (> 10 seconds depending on receiver capabilities)
            ynca_receiver.initialize()
            return True
        except ynca.YncaConnectionError as e:
            raise ConfigEntryNotReady(
                "Connection to YNCA receiver %s failed" % entry.title
            ) from e
        except ynca.YncaInitializationFailedException as e:
            raise ConfigEntryNotReady(
                "Initialization of YNCA receiver %s failed" % entry.title
            ) from e
        except Exception:
            LOGGER.exception(
                "Unexpected exception during initialization of %s" % entry.title
            )
            return False

    def on_disconnect():
        # Reload the entry on disconnect.
        # HA will take care of re-init and retries

        # The unittest hangs on this it seems.
        # Same for the alternative approach below.
        try:
            asyncio.run_coroutine_threadsafe(
                hass.config_entries.async_reload(entry.entry_id), hass.loop
            ).result()
        except OperationNotAllowed:
            # Can not reload when during setup
            # Which is fine, so just let it go
            pass

        # hass.services.call(
        #     HA_DOMAIN, SERVICE_RELOAD_CONFIG_ENTRY, {"entry_id": entry.entry_id}
        # )

    ynca_receiver = ynca.YncaApi(
        entry.data[CONF_SERIAL_URL],
        on_disconnect,
        COMMUNICATION_LOG_SIZE,
    )
    initialized = await hass.async_add_executor_job(initialize_ynca, ynca_receiver)

    if initialized:
        await update_device_registry(hass, entry, ynca_receiver)
        await update_configentry(hass, entry, ynca_receiver)

        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = DomainEntryData(
            api=ynca_receiver,
            initialization_events=ynca_receiver.get_communication_log_items(),
        )
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        if not hass.services.has_service(DOMAIN, SERVICE_SEND_RAW_YNCA):

            async def async_handle_send_raw_ynca_local(call: ServiceCall):
                await async_handle_send_raw_ynca(hass, call)

            hass.services.async_register(
                DOMAIN, SERVICE_SEND_RAW_YNCA, async_handle_send_raw_ynca_local
            )

        entry.async_on_unload(entry.add_update_listener(async_update_options))

    return initialized


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    def close_ynca(ynca_receiver: ynca.YncaApi):
        ynca_receiver.close()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        domain_entry_info = hass.data[DOMAIN].pop(entry.entry_id)
        await hass.async_add_executor_job(close_ynca, domain_entry_info.api)

    if len(hass.data[DOMAIN]) == 0:
        hass.services.async_remove(DOMAIN, SERVICE_SEND_RAW_YNCA)

    return unload_ok
