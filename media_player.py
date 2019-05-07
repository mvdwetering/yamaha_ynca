"""
Support for Yamaha Receivers with the YNCA protocol

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/media_player.yamaha_ynca/

This custom component handles communication with certain Yamaha receivers supporting the YNCA protocol.
I guess it is mostly for older receivers since it also supports the serial port.
"""
import logging

import voluptuous as vol

from homeassistant.components.media_player import (
    MediaPlayerDevice, PLATFORM_SCHEMA)
from homeassistant.components.media_player.const import (
    SUPPORT_TURN_OFF, SUPPORT_TURN_ON, SUPPORT_VOLUME_MUTE,
    SUPPORT_VOLUME_SET, SUPPORT_VOLUME_STEP, SUPPORT_SELECT_SOURCE)
from homeassistant.const import (CONF_NAME, CONF_PORT,  STATE_OFF, STATE_ON,
                                 STATE_PLAYING, STATE_IDLE)
import homeassistant.helpers.config_validation as cv

REQUIREMENTS = ['ynca==0.3.0']


_LOGGER = logging.getLogger(__name__)

SUPPORT_YAMAHA_YNCA = SUPPORT_VOLUME_SET | SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_STEP | \
    SUPPORT_TURN_ON | SUPPORT_TURN_OFF | SUPPORT_SELECT_SOURCE

CONF_SOURCE_NAMES = 'source_names'
CONF_SOURCE_IGNORE = 'source_ignore'
CONF_ZONE_IGNORE = 'zone_ignore'

DEFAULT_NAME = 'Yamaha Receiver (YNCA)'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=None): cv.string,
    vol.Optional(CONF_PORT): cv.string,
    vol.Optional(CONF_SOURCE_IGNORE, default=[]):
        vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_ZONE_IGNORE, default=[]):
        vol.All(cv.ensure_list, [cv.string]),
    vol.Optional(CONF_SOURCE_NAMES, default={}): {cv.string: cv.string},
})


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Yamaha YNCA platform."""
    import ynca

    name = config.get(CONF_NAME)
    port = config.get(CONF_PORT)
    source_ignore = config.get(CONF_SOURCE_IGNORE)
    source_names = config.get(CONF_SOURCE_NAMES)
    zone_ignore = config.get(CONF_ZONE_IGNORE)

    receiver = ynca.YncaReceiver(port)  # Initialization takes a while

    devices = []
    for zone in receiver.zones:
        if zone not in zone_ignore:
            devices.append(YamahaYncaDevice(name, receiver, receiver.zones[zone], source_ignore, source_names))

    add_devices(devices)


class YamahaYncaDevice(MediaPlayerDevice):
    """Representation of a Yamaha Ynca device."""

    def __init__(self, name, receiver, zone, source_ignore, source_names):
        self._name = name
        self._receiver = receiver
        self._zone = zone
        self._zone.on_update_callback = self.update

    def update(self):
        self.schedule_update_ha_state()

    @staticmethod
    def scale(input_value, input_range, output_range):
        input_min = input_range[0]
        input_max = input_range[1]
        input_spread = input_max - input_min

        output_min = output_range[0]
        output_max = output_range[1]
        output_spread = output_max - output_min

        value_scaled = float(input_value - input_min) / float(input_spread)

        return output_min + (value_scaled * output_spread)

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the device."""
        return "{} {}".format(self._name or self._receiver.model_name, self._zone.name)

    @property
    def state(self):
        """Return the state of the device."""
        return STATE_ON if self._zone.on else STATE_OFF

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self.scale(self._zone.volume, [self._zone.min_volume, self._zone.max_volume], [0, 1])

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        import ynca
        return self._zone.mute == ynca.Mute.on

    @property
    def source(self):
        """Return the current input source."""
        return self._zone.input

    @property
    def source_list(self):
        """List of available input sources."""
        # TODO combine with ignore/whitelist
        return sorted(self._receiver.inputs.keys())

    @property
    def supported_features(self):
        """Flag of media commands that are supported."""
        supported_commands = SUPPORT_YAMAHA_YNCA
        return supported_commands

    def turn_off(self):
        """Turn off media player."""
        self._zone.on = False

    def set_volume_level(self, volume):
        """Set volume level, convert range from 0..1."""
        self._zone.volume = self.scale(volume, [0, 1], [self._zone.min_volume, self._zone.max_volume])

    def volume_up(self):
        """Volume up media player."""
        self._zone.volume_up()

    def volume_down(self):
        """Volume down media player."""
        self._zone.volume_down()

    def mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        import ynca
        if mute:
            self._zone.mute = ynca.Mute.on
        else:
            self._zone.mute = ynca.Mute.off

    def turn_on(self):
        """Turn the media player on."""
        self._zone.on = True

    def select_source(self, source):
        """Select input source."""
        self._zone.input = source
