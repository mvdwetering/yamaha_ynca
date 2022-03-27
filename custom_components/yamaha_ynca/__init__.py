"""The Yamaha (YNCA) integration."""
from __future__ import annotations
import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import CONF_SERIAL_URL, DOMAIN, LOGGER

import ynca

# PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]
PLATFORMS: list[Platform] = []


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Yamaha (YNCA) from a config entry."""

    def initialize_receiver(receiver):
        try:
            # Sync function taking a long time (multiple seconds depending on receiver capabilities)
            receiver.initialize()
            return True
        except ynca.YncaConnectionError as e:
            LOGGER.error("Connection to receiver failed")
            raise ConfigEntryNotReady from e
        except ynca.YncaInitializationFailedException as e:
            LOGGER.error("Initialization of receiver failed")
            raise ConfigEntryNotReady from e
        except Exception:
            return False

    def on_disconnect():
        # Reload the entry on disconnect.
        # HA will take care of re-init and retries
        # asyncio.run_coroutine_threadsafe(
        #     hass.config_entries.async_reload(entry.entry_id), hass.loop
        # ).result()
        LOGGER.error("TODO: Add working reload here")

    receiver = ynca.Receiver(entry.data[CONF_SERIAL_URL], on_disconnect)
    initialized = await hass.async_add_executor_job(initialize_receiver, receiver)

    if initialized:
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry.entry_id] = receiver
        hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return initialized


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    def close_receiver(receiver):
        receiver.close()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        receiver = hass.data[DOMAIN].pop(entry.entry_id)
        await hass.async_add_executor_job(close_receiver, receiver)

    return unload_ok
