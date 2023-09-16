from __future__ import annotations
import re

from typing import TYPE_CHECKING, Any, Dict, Iterable, Mapping

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


REMOTE_CODES = """
power_toggle, 7E81-2AD5, 7A85-453A, 7A85-4639, 7A85-6F10
power_on, 7E81-2AD5, 7A85-453A, 7A85-4639, 7A85-6F10
arrow_down, 7A85-9C63, 7A85-2C53, 7A85-314E, 7A85-3649
arrow_left, 7A85-9F60, 7A85-2D52, 7A85-324D, 7A85-3748
arrow_right, 7A85-9E61, 7A85-2E51, 7A85-334C, 7A85-3847
arrow_up, 7A85-9D62, 7A85-2B54, 7A85-304F, 7A85-354A
menu_enter, 7A85-DE21, 7A85-2F50, 7A85-344B, 7A85-3946
menu_return, 7A85-AA55, 7A85-3C43, 7A85-3F40, 7A85-423D
menu_option, 7A85-6B14, 7A85-6C13, 7A85-6D12, 7A85-6E11
pause, 7F01-6798, 7F01-8778, 7F01-A758, 
play, 7F01-6897, 7F01-8877, 7F01-A857, 
stop, 7F01-6996, 7F01-8976, 7F01-A956, 
rew, 7F01-6A95, 7F01-8A75, 7F01-AA55, 
ff, 7F01-6B94, 7F01-8B74, 7F01-AB54, 
skip-, 7F01-6C93, 7F01-8C73, 7F01-AC53, 
skip+, 7F01-6D92, 7F01-8D72, 7F01-AD52, 
"""

def get_zone_codes(zone_id:str) -> Dict[str, str]:
    offset = ZONE_ATTRIBUTE_NAMES.index(zone_id.lower()) + 1

    codes = {}
    for line in REMOTE_CODES.splitlines():
        print(line)
        parts = line.split(",")
        print(parts)
        if len(parts) > offset:
            command = parts[0].strip()
            code = parts[offset].strip()
            # code = parts[offset].replace('-', '').strip()
            print(command, code)
            if code != "":
                codes[command] = code

    return codes


async def async_setup_entry(hass, config_entry, async_add_entities):

    domain_entry_data: DomainEntryData = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for zone_attr_name in ZONE_ATTRIBUTE_NAMES:
        if zone_subunit := getattr(domain_entry_data.api, zone_attr_name):
            entities.append(
                YamahaYncaZoneRemote(config_entry.entry_id, domain_entry_data.api, zone_subunit, get_zone_codes(zone_subunit.id))
            )

    async_add_entities(entities)


class YamahaYncaZoneRemote(RemoteEntity):
    """Representation of a remote of a Yamaha Ynca receiver."""

    _remote_code_formats_regex = re.compile(r"^(?P<left>([0-9A-F]{2}){1,2}?)[^0-9A-F]?(?P<right>([0-9A-F]{2}){1,2})$")

    _attr_has_entity_name = True

    def __init__(self, receiver_unique_id, api:ynca.YncaApi, zone:ZoneBase, zone_codes:Dict[str,str]):
        self._api = api
        self._zone_codes = zone_codes
        self._attr_translation_key = str.lower(zone.id)

        self._attr_unique_id = (
            f"{receiver_unique_id}_{zone.id}_remote"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{receiver_unique_id}_{zone.id}")}
        )

        self._extra_state_attributes = {
            "commands": list(self._zone_codes.keys())
        }


    def _format_code(self, input_code:str) -> str:
        """
        Convert various inputs to 32bit NEC
        Supported are (- can be any separator):
          AA-CC / AACC
          AA-CCCC / AACCCC
          AAAA-CCCC / AAAACCCC
        """
        if matches := self._remote_code_formats_regex.match(input_code):
            output_code = ""
            for part in ['left', 'right']:
                part = matches.group(part)
                if len(part) == 2:
                    output_code += part
                    # Add fillerbyte by inverting the first byte, search NEC ir codes for more info
                    # Invert with 'xor 0xFF' because Python ~ operator makes it signed otherwise
                    output_code += int.to_bytes(int.from_bytes(bytes.fromhex(part)) ^ 0xFF).hex()
                else:
                    output_code += part
            return output_code
        raise ValueError(f"Unrecognized remote code format for '{input_code}'")

    def turn_on(self, **kwargs: Any) -> None:
        """Send the power on command."""
        self.send_command(["power_toggle"])

    def turn_off(self, **kwargs: Any) -> None:
        """Send the power off command."""
        self.send_command(["power_toggle"])

    def send_command(self, command: Iterable[str], **kwargs):
        """Send commands to a device."""
        for cmd in command:
            # Get a code from the mapping,
            # otherwise it is assumed to be a raw code
            code = self._zone_codes.get(cmd, cmd)

            code = self._format_code(code)
            self._api.sys.remotecode(code)