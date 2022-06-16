"""The Yamaha (YNCA) integration."""
from __future__ import annotations

import asyncio
import re
from typing import List

import ynca

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import DOMAIN as HA_DOMAIN, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry, entity_registry

from .const import CONF_SERIAL_URL, DOMAIN, LOGGER, MANUFACTURER_NAME
from .helpers import serial_url_from_user_input

PLATFORMS: List[Platform] = [Platform.MEDIA_PLAYER, Platform.BUTTON]


async def update_device_registry(
    hass: HomeAssistant, config_entry: ConfigEntry, receiver: ynca.Ynca
):
    assert receiver.SYS is not None

    # Configuration URL for devices connected through IP
    configuration_url = None
    if matches := re.match(
        r"socket:\/\/(.+):\d+",  # Extract IP or hostname
        serial_url_from_user_input(config_entry.data[CONF_SERIAL_URL]),
    ):
        configuration_url = f"http://{matches[1]}"

    # Add device explicitly to registry so other entities just have to report the identifier to link up
    registry = device_registry.async_get(hass)
    registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, config_entry.entry_id)},
        manufacturer=MANUFACTURER_NAME,
        name=f"{MANUFACTURER_NAME} {receiver.SYS.modelname}",
        model=receiver.SYS.modelname,
        sw_version=receiver.SYS.version,
        configuration_url=configuration_url,
    )


async def async_migrate_entry(hass, config_entry: ConfigEntry):
    """Migrate old entry."""
    LOGGER.debug("Migrating from version %s", config_entry.version)

    if config_entry.version == 1:
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

    if config_entry.version == 2:
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

    LOGGER.info("Migration to version %s successful", config_entry.version)

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    # Just reload the integration on update. Crude, but it works
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Yamaha (YNCA) from a config entry."""

    def initialize_ynca(ynca_receiver: ynca.Ynca):
        try:
            # Sync function taking a long time (multiple seconds depending on receiver capabilities)
            ynca_receiver.initialize()
            return True
        except ynca.YncaConnectionError as e:
            LOGGER.error("Connection to YNCA receiver failed")
            raise ConfigEntryNotReady from e
        except ynca.YncaInitializationFailedException as e:
            LOGGER.error("Initialization of YNCA receiver failed")
            raise ConfigEntryNotReady from e
        except Exception:
            return False

    def on_disconnect():
        # Reload the entry on disconnect.
        # HA will take care of re-init and retries

        # The unittest hangs on this it seems.
        # Same for the alternative approach below.
        asyncio.run_coroutine_threadsafe(
            hass.config_entries.async_reload(entry.entry_id), hass.loop
        ).result()

        # hass.services.call(
        #     HA_DOMAIN, SERVICE_RELOAD_CONFIG_ENTRY, {"entry_id": entry.entry_id}
        # )

    ynca_receiver = ynca.Ynca(
        serial_url_from_user_input(entry.data[CONF_SERIAL_URL]), on_disconnect
    )
    initialized = await hass.async_add_executor_job(initialize_ynca, ynca_receiver)

    if initialized:
        await update_device_registry(hass, entry, ynca_receiver)
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = ynca_receiver
        hass.config_entries.async_setup_platforms(entry, PLATFORMS)

        entry.async_on_unload(entry.add_update_listener(async_update_options))

    return initialized


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    def close_ynca(ynca_receiver: ynca.Ynca):
        ynca_receiver.close()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        ynca_receiver = hass.data[DOMAIN].pop(entry.entry_id)
        await hass.async_add_executor_job(close_ynca, ynca_receiver)

    return unload_ok
