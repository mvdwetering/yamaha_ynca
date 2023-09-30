from __future__ import annotations
import re

from typing import TYPE_CHECKING, Any, Dict, Iterable

from homeassistant.components.remote import RemoteEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    DOMAIN,
    ZONE_ATTRIBUTE_NAMES,
)
from .helpers import DomainEntryData
import ynca

if TYPE_CHECKING:  # pragma: no cover
    from ynca.subunits.zone import ZoneBase


# Use a docstring to more easily write the codes
REMOTE_CODES = """

on, 7E81-7E81, 7E81-BA45, 7A85-ED12, 7A85-7B84
standby, 7E81-7F80, 7E81-BB44, 7A85-EE11, 7A85-7C83

receiver_power_toggle, 7E81-2AD5, 7A85-453A, 7A85-4639, 7A85-6F10
source_power_toggle, 7F01-50AF, 7F01-708F, 7F01-906F, 7F01-B04F

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
ent,7F01-5CA3, 7F01-7C83, 7F01-9C63

"""


def get_zone_codes(zone_id: str) -> Dict[str, str]:
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


async def async_setup_entry(hass, config_entry, async_add_entities):
    domain_entry_data: DomainEntryData = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for zone_attr_name in ZONE_ATTRIBUTE_NAMES:
        if zone_subunit := getattr(domain_entry_data.api, zone_attr_name):
            entities.append(
                YamahaYncaZoneRemote(
                    config_entry.entry_id,
                    domain_entry_data.api,
                    zone_subunit,
                    get_zone_codes(zone_subunit.id),
                )
            )

    async_add_entities(entities)


class YamahaYncaZoneRemote(RemoteEntity):
    """Representation of a remote of a Yamaha Ynca receiver."""

    _remotecode_formats_regex = re.compile(
        r"^(?P<left>([0-9A-F]{2}){1,2}?)[^0-9A-F]?(?P<right>([0-9A-F]{2}){1,2})$"
    )
    _attr_has_entity_name = True
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        receiver_unique_id,
        api: ynca.YncaApi,
        zone: ZoneBase,
        zone_codes: Dict[str, str],
    ):
        self._api = api
        self._zone = zone
        self._zone_codes = zone_codes
        self._attr_translation_key = str.lower(zone.id)

        self._attr_unique_id = f"{receiver_unique_id}_{zone.id}_remote"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{receiver_unique_id}_{zone.id}")}
        )

        self._attr_extra_state_attributes = {"commands": list(self._zone_codes.keys())}

    def _format_remotecode(self, input_code: str) -> str:
        """
        Convert various inputs to 32bit NEC
        Supported are (- can be any separator):
          AA-CC / AACC
          AA-CCCC / AACCCC
          AAAA-CCCC / AAAACCCC
        """
        matches = self._remotecode_formats_regex.match(input_code)
        if not matches:
            raise ValueError(f"Unrecognized remotecode format for '{input_code}'")

        output_code = ""
        for part in ["left", "right"]:
            part = matches.group(part)
            if len(part) == 2:
                output_code += part
                # Add filler byte by inverting the first byte, research NEC ir codes for more info
                # Invert with 'xor 0xFF' because Python ~ operator makes it signed otherwise
                output_code += int.to_bytes(
                    int.from_bytes(bytes.fromhex(part)) ^ 0xFF
                ).hex()
            else:
                output_code += part
        return output_code

    def turn_on(self, **kwargs: Any) -> None:
        """Send the power on command."""
        self.send_command(["on"])

    def turn_off(self, **kwargs: Any) -> None:
        """Send the power off command."""
        self.send_command(["standby"])

    def send_command(self, command: Iterable[str], **kwargs):
        """Send commands to a device."""
        for cmd in command:
            # Use raw remotecode from mapping otherwise assume user provided raw code
            code = self._zone_codes.get(cmd, cmd)
            code = self._format_remotecode(code)

            self._api.sys.remotecode(code)  # type: ignore
