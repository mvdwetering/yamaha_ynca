from __future__ import annotations

from typing import Any

import ynca

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, ZONE_ATTRIBUTE_NAMES
from .helpers import DomainEntryData

ENTITY_DESCRIPTIONS = [
    NumberEntityDescription(
        key="maxvol",
        entity_category=EntityCategory.CONFIG,
        native_min_value=-30,
        native_max_value=16.5,
        native_step=0.5,
        device_class=NumberDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        name="Max volume",
    ),
    NumberEntityDescription(
        key="spbass",
        entity_category=EntityCategory.CONFIG,
        native_min_value=-6,
        native_max_value=6,
        native_step=0.5,
        device_class=NumberDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        name="Bass",
    ),
    NumberEntityDescription(
        key="sptreble",
        entity_category=EntityCategory.CONFIG,
        native_min_value=-6,
        native_max_value=6,
        native_step=0.5,
        device_class=NumberDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        name="Treble",
    ),
]


async def async_setup_entry(hass, config_entry, async_add_entities):

    domain_entry_data: DomainEntryData = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for zone_attr_name in ZONE_ATTRIBUTE_NAMES:
        if zone_subunit := getattr(domain_entry_data.api, zone_attr_name):
            for entity_description in ENTITY_DESCRIPTIONS:
                if getattr(zone_subunit, entity_description.key, None) is not None:
                    entities.append(
                        YamahaYncaNumber(
                            config_entry.entry_id, zone_subunit, entity_description
                        )
                    )

    async_add_entities(entities)


class YamahaYncaNumber(NumberEntity):
    """Representation of a number on a Yamaha Ynca device."""

    _attr_has_entity_name = True

    def __init__(self, receiver_unique_id, zone, description: NumberEntityDescription):
        self._zone = zone
        self._relevant_updates = ["PWR", description.key.upper()]
        self.entity_description = description

        self._attr_unique_id = (
            f"{receiver_unique_id}_{self._zone.id}_number_{self.entity_description.key}"
        )
        self._attr_device_info = {
            "identifiers": {(DOMAIN, receiver_unique_id)},
        }

    def update_callback(self, function, value):
        if function in self._relevant_updates:
            self.schedule_update_ha_state()

    async def async_added_to_hass(self):
        self._zone.register_update_callback(self.update_callback)

    async def async_will_remove_from_hass(self):
        self._zone.unregister_update_callback(self.update_callback)

    @property
    def available(self):
        return self._zone.pwr is ynca.Pwr.ON

    @property
    def name(self):
        return f"{self._zone.zonename}: {self.entity_description.name}"

    @property
    def native_value(self) -> float | None:
        """Return the value reported by the number."""
        return getattr(self._zone, self.entity_description.key)

    def set_native_value(self, value: float) -> None:
        setattr(self._zone, self.entity_description.key, value)
