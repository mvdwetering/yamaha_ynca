from __future__ import annotations

import re
import time
from typing import TYPE_CHECKING, Any

from homeassistant.components.remote import (
    ATTR_DELAY_SECS,
    ATTR_NUM_REPEATS,
    DEFAULT_DELAY_SECS,
    DEFAULT_NUM_REPEATS,
    RemoteEntity,
)
from homeassistant.helpers.entity import DeviceInfo

import ynca

from .const import ATTR_COMMANDS, DOMAIN, ZONE_ATTRIBUTE_NAMES

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Iterable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ynca.subunits.zone import ZoneBase

    from . import YamahaYncaConfigEntry


# Use a docstring to more easily write the codes
REMOTE_CODES = """

on, 7E81-7E81, 7E81-BA45, 7A85-ED12, 7A85-7B84
standby, 7E81-7F80, 7E81-BB44, 7A85-EE11, 7A85-7C83

receiver_power_toggle, 7E81-2AD5, 7A85-453A, 7A85-4639, 7A85-6F10
source_power_toggle, 7F01-50AF, 7F01-708F, 7F01-906F, 7F01-B04F

mute, 7A85-1CE3, 7A85-DC23, 7A85-FF00
volume_up, 7A85-1AE5, 7A85-DA25, 7A85-FD02
volume_down, 7A85-1BE4, 7A85-DB24, 7A85-FE01

info, 7A85-2758

scene_1, 7A85-007F, 7A85-017E, 7A85-027D, 7A85-1867
scene_2, 7A85-037C, 7A85-047B, 7A85-057A, 7A85-1966
scene_3, 7A85-0679, 7A85-0778, 7A85-0877, 7A85-1A65
scene_4, 7A85-0976, 7A85-0A75, 7A85-0B74, 7A85-1B64

on_screen, 7A85-847B
option, 7A85-6B14, 7A85-6C13, 7A85-6D12, 7A85-6E11

up, 7A85-9D62, 7A85-2B54, 7A85-304F, 7A85-354A
down, 7A85-9C63, 7A85-2C53, 7A85-314E, 7A85-3649
left, 7A85-9F60, 7A85-2D52, 7A85-324D, 7A85-3748
right, 7A85-9E61, 7A85-2E51, 7A85-334C, 7A85-3847

enter, 7A85-DE21, 7A85-2F50, 7A85-344B, 7A85-3946
return, 7A85-AA55, 7A85-3C43, 7A85-3F40, 7A85-423D
display, 7F01-609F, 7F01-807F, 7F01-A05F, 7F01-C03F
top_menu, 7A85-A0DF, 7A85-A1DE, 7A85-A2DD, 7A85-A3DC
popup_menu, 7A85-A4DB, 7A85-A5DA, 7A85-A6D9, 7A85-A7D8

stop, 7F01-6996, 7F01-8976, 7F01-A956,
pause, 7F01-6798, 7F01-8778, 7F01-A758,
play, 7F01-6897, 7F01-8877, 7F01-A857,
rewind, 7F01-6A95, 7F01-8A75, 7F01-AA55,
fast_forward, 7F01-6B94, 7F01-8B74, 7F01-AB54,
previous, 7F01-6C93, 7F01-8C73, 7F01-AC53,
next, 7F01-6D92, 7F01-8D72, 7F01-AD52,

1, 7F01-51AE, 7F01-718E, 7F01-916E
2, 7F01-52AD, 7F01-728D, 7F01-926D
3, 7F01-53AC, 7F01-738C, 7F01-936C
4, 7F01-54AB, 7F01-748B, 7F01-946B
5, 7F01-55AA, 7F01-758A, 7F01-956A
6, 7F01-56A9, 7F01-7689, 7F01-9669
7, 7F01-57A8, 7F01-7788, 7F01-9768
8, 7F01-58A7, 7F01-7887, 7F01-9867
9, 7F01-59A6, 7F01-7986, 7F01-9966
0, 7F01-5AA5, 7F01-7A85, 7F01-9A65
+10, 7F01-5BA4, 7F01-7B84, 7F01-9B64, 7F01-BB44
ent, 7F01-5CA3, 7F01-7C83, 7F01-9C63

hdmi1, 7A-4738
hdmi2, 7A-4A35
hdmi3, 7A-4D32
hdmi4, 7A-502F
hdmi5, 7A-700F
hdmi6, 7A-730C
hdmi7, 7A-98E7
audio1, 7A-651A
audio2, 7A-6817
audio3, 7A-7C03
audio4, 7A-7F00
audio5, 7A-ACD3
av1, 7A-532C
av2, 7A-5629
av3, 7A-5926
av4, 7A-5C23
av5, 7A-5F20
av6, 7A-621D
av7, 7A-7609
phono, 7A-14

program+, 7A85-58A7
program-, 7A85-59A6
straight, 7A85-56A9
movie, 7A85-8877
music, 7A85-8976
classical, 7A85-8A75
live_club, 7A85-8B74
entertainment, 7A85-8C73
surround_decode, 7A85-8D72
stereo, 7A85-8F70
pure_direct, 7A85-DD22
enhancer, 7A85-946B

"""


def get_zone_codes(zone_id: str) -> dict[str, str]:
    offset = ZONE_ATTRIBUTE_NAMES.index(zone_id.lower()) + 1

    codes = {}
    for line in REMOTE_CODES.splitlines():
        parts = line.split(",")
        if len(parts) > offset:
            command = parts[0].strip()
            code = parts[offset].strip()
            if code != "":
                codes[command] = code

    return codes


async def async_setup_entry(
    _hass: HomeAssistant,
    config_entry: YamahaYncaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    domain_entry_data = config_entry.runtime_data

    entities = [
        YamahaYncaZoneRemote(
            config_entry.entry_id,
            domain_entry_data.api,
            zone_subunit,
            get_zone_codes(zone_subunit.id),
        )
        for zone_attr_name in ZONE_ATTRIBUTE_NAMES
        if (zone_subunit := getattr(domain_entry_data.api, zone_attr_name))
    ]

    async_add_entities(entities)


class YamahaYncaZoneRemote(RemoteEntity):
    """Representation of a remote of a Yamaha Ynca receiver."""

    _remotecode_formats_regex = re.compile(
        r"^(?P<left>([0-9A-F]{2}){1,2}?)[^0-9A-F]?(?P<right>([0-9A-F]{2}){1,2})$"
    )
    _attr_has_entity_name = True
    _unrecorded_attributes = frozenset({ATTR_COMMANDS})

    def __init__(
        self,
        receiver_unique_id: str,
        api: ynca.YncaApi,
        zone: ZoneBase,
        zone_codes: dict[str, str],
    ) -> None:
        self._api = api
        self._zone = zone
        self._zone_codes = zone_codes
        self._attr_translation_key = str.lower(zone.id)

        self._attr_unique_id = f"{receiver_unique_id}_{zone.id}_remote"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{receiver_unique_id}_{zone.id}")}
        )

        self._attr_extra_state_attributes = {
            ATTR_COMMANDS: list(self._zone_codes.keys())
        }

    def _format_remotecode(self, input_code: str) -> str:
        """Format the remote codes into 32bit NEC.

        Supported are (- can be any separator):
          AA-CC / AACC
          AA-CCCC / AACCCC
          AAAA-CCCC / AAAACCCC
        """
        matches = self._remotecode_formats_regex.match(input_code)
        if not matches:
            msg = f"Unrecognized remotecode format for '{input_code}'"
            raise ValueError(msg)

        output_code = ""
        for side_selector in ["left", "right"]:
            part = matches.group(side_selector)
            if len(part) == 2:  # noqa: PLR2004
                output_code += part
                # Add filler byte by inverting the first byte, research NEC ir codes for more info
                # Invert with 'xor 0xFF' because Python ~ operator makes it signed otherwise
                output_code += (
                    int.to_bytes(int.from_bytes(bytes.fromhex(part)) ^ 0xFF)
                    .hex()
                    .upper()
                )
            else:
                output_code += part
        return output_code

    def _update_callback(self, function: str | None, _value: Any) -> None:
        if function == "PWR":
            self.schedule_update_ha_state()

    async def async_added_to_hass(self) -> None:
        self._zone.register_update_callback(self._update_callback)

    async def async_will_remove_from_hass(self) -> None:
        self._zone.unregister_update_callback(self._update_callback)

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return self._zone.pwr is ynca.Pwr.ON

    def turn_on(self, **_kwargs: Any) -> None:
        """Send the power on command."""
        self.send_command(["on"])

    def turn_off(self, **_kwargs: Any) -> None:
        """Send the power off command."""
        self.send_command(["standby"])

    def send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send commands to a device."""
        num_repeats = kwargs.get(ATTR_NUM_REPEATS, DEFAULT_NUM_REPEATS)
        delay_secs = kwargs.get(ATTR_DELAY_SECS, DEFAULT_DELAY_SECS)

        first = True
        for _ in range(num_repeats):
            for cmd in command:
                if not first:
                    time.sleep(delay_secs)
                first = False

                # Use raw remotecode from mapping
                # if it is not there assume user provided raw code
                code = self._zone_codes.get(cmd, cmd)
                formatted_code = self._format_remotecode(code)

                self._api.sys.remotecode(formatted_code)  # type: ignore[union-attr]
