"""The Yamaha (YNCA) integration."""
from __future__ import annotations
import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN

import ynca

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Yamaha (YNCA) from a config entry."""

    def initialize_receiver(receiver):
        try:
            # Sync function taking a long time (multiple seconds depending on receiver capabilities)
            receiver.initialize()
            return True
        except Exception:
            return False

    def on_disconnect():
        # Reload the entry on disconnect.
        # HA will take care of re-init and retries
        asyncio.run_coroutine_threadsafe(
            hass.config_entries.async_reload(entry.entry_id), hass.loop
        ).result()

    receiver = ynca.Receiver(entry.data["serial_url"], on_disconnect)
    initialized = await hass.async_add_executor_job(initialize_receiver, receiver)

    if initialized:
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
