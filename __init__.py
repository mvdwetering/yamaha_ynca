"""The Yamaha YNCA integration."""
import asyncio
import voluptuous as vol
import ynca

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN

CONFIG_SCHEMA = vol.Schema({DOMAIN: vol.Schema({})}, extra=vol.ALLOW_EXTRA)

PLATFORMS = ["media_player"]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Yamaha YNCA component."""
    return True


def setup_receiver(port):
    return ynca.YncaReceiver(port)  # Initialization takes a while

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Yamaha YNCA from a config entry."""
    if not DOMAIN in hass.data:
        hass.data[DOMAIN] = {}

    loop = asyncio.get_running_loop()
    receiver = await loop.run_in_executor(None, setup_receiver, entry.data["serial_port"])
    hass.data[DOMAIN][entry.entry_id] = receiver

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN][entry.entry_id]._connection.disconnect()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
