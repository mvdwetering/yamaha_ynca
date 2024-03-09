"""Constants for the Yamaha (YNCA) integration."""

import logging

import ynca

DOMAIN = "yamaha_ynca"
LOGGER = logging.getLogger(__package__)

COMMUNICATION_LOG_SIZE = 5000

CONF_SERIAL_URL = "serial_url"
CONF_HOST = "host"
CONF_PORT = "port"

DATA_MODELNAME = "modelname"
DATA_ZONES = "zones"

SERVICE_SEND_RAW_YNCA = "send_raw_ynca"
SERVICE_STORE_PRESET = "store_preset"

ATTR_COMMANDS = "commands"
ATTR_PRESET_ID = "preset_id"

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
CONF_SELECTED_SURROUND_DECODERS = "selected_surround_decoders"
CONF_NUMBER_OF_SCENES = "number_of_scenes"
NUMBER_OF_SCENES_AUTODETECT = -1
MAX_NUMBER_OF_SCENES = 12


SURROUNDDECODEROPTIONS_PLIIX_MAPPING = {
    ynca.TwoChDecoder.DolbyPl2xGame: ynca.TwoChDecoder.DolbyPl2Game,
    ynca.TwoChDecoder.DolbyPl2xMovie: ynca.TwoChDecoder.DolbyPl2Movie,
    ynca.TwoChDecoder.DolbyPl2xMusic: ynca.TwoChDecoder.DolbyPl2Music,
}

TWOCHDECODER_STRINGS = {
    "dolby_pl": "Dolby Pro Logic",
    "dolby_plii_game": "Dolby Pro Logic II(x) Game",
    "dolby_plii_movie": "Dolby Pro Logic II(x) Movie",
    "dolby_plii_music": "Dolby Pro Logic II(x) Music",
    "dts_neo_6_cinema": "DTS NEO:6 Cinema",
    "dts_neo_6_music": "DTS NEO:6 Music",
    "auto": "Auto",
    "dolby_surround": "Dolby Surround",
    "dts_neural_x": "DTS Neural:X",
    "auro_3d": "AURO-3D"
}
