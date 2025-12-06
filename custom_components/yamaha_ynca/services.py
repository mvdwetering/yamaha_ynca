"""Services for Yamaha (YNCA)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.const import ATTR_CONFIG_ENTRY_ID
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, service
import voluptuous as vol

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.helpers.service import ServiceCall

ATTR_PRESET_ID = "preset_id"
ATTR_RAW_DATA = "raw_data"

SERVICE_SEND_RAW_YNCA = "send_raw_ynca"
SERVICE_STORE_PRESET = "store_preset"


async def async_handle_send_raw_ynca(hass: HomeAssistant, call: ServiceCall) -> None:
    config_entry = hass.config_entries.async_get_entry(
        call.data.get(ATTR_CONFIG_ENTRY_ID)
    )

    if config_entry is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="config_entry_not_found",
            translation_placeholders={
                "config_entry_id": call.data.get(ATTR_CONFIG_ENTRY_ID)
            },
        )

    # Handle actual call
    for line in call.data.get(ATTR_RAW_DATA, "").splitlines():
        line = line.strip()  # noqa: PLW2901
        if line.startswith("@"):
            config_entry.runtime_data.api.send_raw(line)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register Yamaha (YNCA) services."""

    async def async_handle_send_raw_ynca_local(call: ServiceCall) -> None:
        await async_handle_send_raw_ynca(hass, call)

    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_RAW_YNCA,
        async_handle_send_raw_ynca_local,
        schema=vol.Schema(
            {
                vol.Required(ATTR_CONFIG_ENTRY_ID): cv.string,
                vol.Required(ATTR_RAW_DATA): cv.string,
            }
        ),
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
