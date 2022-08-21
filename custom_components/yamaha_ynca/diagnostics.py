"""Diagnostics support for Yamaha (YNCA)."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

import ynca

from .const import DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = {}
    data["config_entry"] = entry.as_dict()

    # Add data from the device itself
    if domain_entry_data := hass.data[DOMAIN].get(entry.entry_id, None):
        api: ynca.Ynca = domain_entry_data.api
        data["SYS"] = {
            "modelname": api.SYS.modelname,
            "version": api.SYS.version,
        }
        data["communication"] = {
            "initialization": domain_entry_data.initialization_events,
            "history": api.get_communication_log_items(),
        }

    return data
