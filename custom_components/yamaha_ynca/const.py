"""Constants for the Yamaha (YNCA) integration."""

import logging
import ynca

DOMAIN = "yamaha_ynca"
LOGGER = logging.getLogger(__package__)

CONF_SERIAL_URL = "serial_url"

MANUFACTURER_NAME = "Yamaha"

ZONE_SUBUNIT_IDS = [
    ynca.Subunit.MAIN,
    ynca.Subunit.ZONE2,
    ynca.Subunit.ZONE3,
    ynca.Subunit.ZONE4,
]


def CONF_HIDDEN_INPUTS_FOR_ZONE(zone: str):
    return f"hidden_inputs_{zone}"
