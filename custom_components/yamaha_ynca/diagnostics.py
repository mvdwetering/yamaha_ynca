"""Diagnostics support for Yamaha (YNCA)."""
from __future__ import annotations

from typing import Any

import ynca

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .helpers import DomainEntryData


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = {}
    data["config_entry"] = entry.as_dict()

    # Add data from the device itself
    domain_entry_data: DomainEntryData = hass.data[DOMAIN].get(entry.entry_id, None)
    if domain_entry_data:
        api: ynca.YncaApi = domain_entry_data.api
        if api.sys:
            data["sys"] = {
                "modelname": api.sys.modelname,
                "version": api.sys.version,
            }
        data["communication"] = {
            "initialization": domain_entry_data.initialization_events,
            "history": api.get_communication_log_items(),
        }

    return data
