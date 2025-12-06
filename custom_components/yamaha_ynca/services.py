"""Services for Yamaha (YNCA)."""

from __future__ import annotations

from homeassistant.components.media_player import DOMAIN as MEDIA_PLAYER_DOMAIN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv, service
import voluptuous as vol

from .const import DOMAIN

ATTR_PRESET_ID = "preset_id"

SERVICE_STORE_PRESET = "store_preset"


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register Yamaha (YNCA) services."""
    # Store Preset
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        SERVICE_STORE_PRESET,
        entity_domain=MEDIA_PLAYER_DOMAIN,
        schema={vol.Required(ATTR_PRESET_ID): cv.positive_int},
        func="store_preset",
    )
