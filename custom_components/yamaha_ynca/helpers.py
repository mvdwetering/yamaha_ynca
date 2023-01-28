"""Helpers for the Yamaha (YNCA) integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List

import ynca

from custom_components.yamaha_ynca.const import DOMAIN
from homeassistant.helpers.entity import EntityDescription

if TYPE_CHECKING:  # pragma: no cover
    from ynca.subunits.zone import ZoneBase


@dataclass
class DomainEntryData:
    api: ynca.YncaApi
    initialization_events: List[str]


def scale(input_value, input_range, output_range):
    input_min = input_range[0]
    input_max = input_range[1]
    input_spread = input_max - input_min

    output_min = output_range[0]
    output_max = output_range[1]
    output_spread = output_max - output_min

    value_scaled = float(input_value - input_min) / float(input_spread)

    return output_min + (value_scaled * output_spread)


class YamahaYncaSettingEntity:
    """
    Common code for YamahaYnca settings entities.
    Entities derived from this also need to derive from the standard HA entities.
    """

    _attr_has_entity_name = True

    def __init__(
        self, receiver_unique_id, zone: ZoneBase, description: EntityDescription
    ):
        self.entity_description = description
        self._zone = zone

        function_names = getattr(self.entity_description, "function_names", None)
        self._relevant_updates = ["PWR"]
        self._relevant_updates.extend(
            function_names or [self.entity_description.key.upper()]
        )

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{receiver_unique_id}_{self._zone.id}")}
        }
        self._attr_name = self.entity_description.name
        self._attr_translation_key = self.entity_description.key
        self._attr_unique_id = (
            f"{receiver_unique_id}_{self._zone.id}_{self.entity_description.key}"
        )

    def update_callback(self, function, value):
        if function in self._relevant_updates:
            self.schedule_update_ha_state()  # type: ignore

    async def async_added_to_hass(self):
        self._zone.register_update_callback(self.update_callback)

    async def async_will_remove_from_hass(self):
        self._zone.unregister_update_callback(self.update_callback)

    @property
    def available(self):
        return self._zone.pwr is ynca.Pwr.ON
