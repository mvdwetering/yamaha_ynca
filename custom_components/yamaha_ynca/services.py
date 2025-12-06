"""Services for Yamaha (YNCA)."""

from __future__ import annotations

from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, service
from homeassistant.helpers.service import ServiceCall, async_extract_config_entry_ids
import voluptuous as vol

from .const import DOMAIN

ATTR_PRESET_ID = "preset_id"
ATTR_RAW_DATA = "raw_data"

SERVICE_SEND_RAW_YNCA = "send_raw_ynca"
SERVICE_STORE_PRESET = "store_preset"


async def async_handle_send_raw_ynca(hass: HomeAssistant, call: ServiceCall) -> None:
    for config_entry_id in await async_extract_config_entry_ids(hass, call):  # type: ignore[arg-type]
        # Check if configentry is ours, could be others when targeting areas for example
        if (
            (config_entry := hass.config_entries.async_get_entry(config_entry_id))
            and (config_entry.domain == DOMAIN)
            and (domain_entry_info := config_entry.runtime_data)
        ):
            # Handle actual call
            for line in call.data.get(ATTR_RAW_DATA).splitlines():
                line = line.strip()  # noqa: PLW2901
                if line.startswith("@"):
                    domain_entry_info.api.send_raw(line)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register Yamaha (YNCA) services."""

    async def async_handle_send_raw_ynca_local(call: ServiceCall) -> None:
        await async_handle_send_raw_ynca(hass, call)

    hass.services.async_register(
        DOMAIN, SERVICE_SEND_RAW_YNCA, async_handle_send_raw_ynca_local
    )

    # Store Preset
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_STORE_PRESET,
        entity_domain=MEDIA_PLAYER_DOMAIN,
        schema={vol.Required(ATTR_PRESET_ID): cv.positive_int},
        func="store_preset",
    )
