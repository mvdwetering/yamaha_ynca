"""Constants for the Yamaha (YNCA) integration."""

import logging

DOMAIN = "yamaha_ynca"
LOGGER = logging.getLogger(__package__)

COMMUNICATION_LOG_SIZE = 5000

CONF_SERIAL_URL = "serial_url"
CONF_HOST = "host"
CONF_PORT = "port"

DATA_MODELNAME = "modelname"
DATA_ZONES = "zones"


MANUFACTURER_NAME = "Yamaha"

ZONE_MAX_VOLUME = 16.5  # Seems to be 16.5 when MAXVOL function not implemented
ZONE_MIN_VOLUME = -80.5

ZONE_ATTRIBUTE_NAMES = [
    "main",
    "zone2",
    "zone3",
    "zone4",
]

CONF_HIDDEN_SOUND_MODES = "hidden_sound_modes"
CONF_SELECTED_SOUND_MODES = "selected_sound_modes"
CONF_HIDDEN_INPUTS = "hidden_inputs"
CONF_SELECTED_INPUTS = "selected_inputs"
CONF_NUMBER_OF_SCENES = "number_of_scenes"
NUMBER_OF_SCENES_AUTODETECT = -1
MAX_NUMBER_OF_SCENES = 12
