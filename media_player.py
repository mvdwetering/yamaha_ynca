"""
Support for Yamaha Receivers with the YNCA protocol

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/media_player.yamaha_ynca/

This custom component handles communication with certain Yamaha receivers supporting the YNCA protocol.
I guess it is mostly for older receivers since it also supports the serial port.
"""
import asyncio
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

import ynca

from .const import DOMAIN, MANUFACTURER_NAME, LOGGER

SUPPORT_YAMAHA_YNCA = SUPPORT_VOLUME_SET | SUPPORT_VOLUME_MUTE | SUPPORT_VOLUME_STEP | \
    SUPPORT_TURN_ON | SUPPORT_TURN_OFF | SUPPORT_SELECT_SOURCE

DEFAULT_NAME = 'Yamaha Receiver (YNCA)'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_PORT): cv.string,
})

# OLD
# def setup_platform(hass, config, add_devices, discovery_info=None):
#     """Setup the Yamaha YNCA platform."""

#     port = config.get(CONF_PORT)
#     receiver = ynca.YncaReceiver(port)  # Initialization takes a while

#     devices = []
#     for zone in receiver.zones:
#         if zone not in zone_ignore:
#             devices.append(YamahaYncaDevice(name, receiver, receiver.zones[zone], source_ignore, source_names))

#     add_devices(devices)

def setup_receiver(port):
    return ynca.YncaReceiver(port)  # Initialization takes a while

async def async_setup_entry(hass, config_entry, async_add_entities):
    LOGGER.warn("async_setup_entry")
    LOGGER.warn(config_entry)

    loop = asyncio.get_running_loop()
    receiver = await loop.run_in_executor(None, setup_receiver, config_entry.data["serial_port"])

    hass.data[DOMAIN][config_entry.entry_id]["receiver"] = receiver

    entities = []
    for zone in receiver.zones:
        # Since there is no discovery and the device exposes no unique identifiers on the API
        # lets invent one ourselves. Since the only way to add is through ConfigFlow there will
        # be a configentry with an ID which must already be unique.
        entities.append(YamahaYncaZone(config_entry.entry_id, receiver, receiver.zones[zone]))

    async_add_entities(entities)


class YamahaYncaZone(MediaPlayerDevice):
    """Representation of a zone of a Yamaha Ynca device."""

    def __init__(self, receiver_unique_id, receiver, zone):
        self._receiver = receiver
        self._zone = zone
        self._zone.on_update_callback = self.update
        self._receiver_unique_id = receiver_unique_id

    @property
    def device_info(self):
        """Return the device info."""
        return {
            'identifiers': {
                (DOMAIN, self._receiver_unique_id)
            },
            'name': f"{MANUFACTURER_NAME} {self._receiver.model_name}",
            'manufacturer': MANUFACTURER_NAME,
            'model': self._receiver.model_name,
            'sw_version': self._receiver.firmware_version,
        }

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
        return "{} {}".format(self._receiver.model_name, self._zone.name)

    @property
    def unique_id(self):
        """Return the uniqueid of the entity."""
        return f"{self._receiver_unique_id}_{self._zone}"

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
        return self._zone.mute == ynca.Mute.on

    @property
    def source(self):
        """Return the current input source."""
        return self._zone.input

    @property
    def source_list(self):
        """List of available input sources."""
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
