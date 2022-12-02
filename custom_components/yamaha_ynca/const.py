"""Constants for the Yamaha (YNCA) integration."""

import logging

DOMAIN = "yamaha_ynca"
LOGGER = logging.getLogger(__package__)

COMMUNICATION_LOG_SIZE = 1000

CONF_SERIAL_URL = "serial_url"
CONF_HOST = "host"
CONF_PORT = "port"

MANUFACTURER_NAME = "Yamaha"

ZONE_MAX_VOLUME = 16.5  # Seems to be 16.5 when MAXVOL function not implemented
ZONE_MIN_VOLUME = -80.5

ZONE_SUBUNITS = [
    "main",
    "zone2",
    "zone3",
    "zone4",
]

CONF_HIDDEN_SOUND_MODES = "hidden_sound_modes"


def CONF_HIDDEN_INPUTS_FOR_ZONE(zone: str):
    return f"hidden_inputs_{zone}"
