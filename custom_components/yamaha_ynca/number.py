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
from .helpers import DomainEntryData, YamahaYncaSettingEntityMixin

ENTITY_DESCRIPTIONS = [
    # Suppress following mypy message, which seems to be not an issue as other values have defaults:
    # custom_components/yamaha_ynca/number.py:19: error: Missing positional arguments "entity_registry_enabled_default", "entity_registry_visible_default", "force_update", "icon", "has_entity_name", "unit_of_measurement", "max_value", "min_value", "step" in call to "NumberEntityDescription"  [call-arg]
    NumberEntityDescription(  # type: ignore
        key="maxvol",
        device_class=NumberDeviceClass.SIGNAL_STRENGTH,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:volume-high",
        name="Max volume",
        native_max_value=16.5,
        native_min_value=-30,
        native_step=0.5,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
    ),
    NumberEntityDescription(  # type: ignore
        key="spbass",
        device_class=NumberDeviceClass.SIGNAL_STRENGTH,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:speaker",
        name="Speaker bass",
        native_min_value=-6,
        native_max_value=6,
        native_step=0.5,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
    ),
    NumberEntityDescription(  # type: ignore
        key="sptreble",
        entity_category=EntityCategory.CONFIG,
        device_class=NumberDeviceClass.SIGNAL_STRENGTH,
        icon="mdi:speaker",
        name="Speaker treble",
        native_min_value=-6,
        native_max_value=6,
        native_step=0.5,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
    ),
    NumberEntityDescription(  # type: ignore
        key="hpbass",
        device_class=NumberDeviceClass.SIGNAL_STRENGTH,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:headphones",
        name="Headphone bass",
        native_min_value=-6,
        native_max_value=6,
        native_step=0.5,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        entity_registry_enabled_default=False,
    ),
    NumberEntityDescription(  # type: ignore
        key="hptreble",
        entity_category=EntityCategory.CONFIG,
        device_class=NumberDeviceClass.SIGNAL_STRENGTH,
        icon="mdi:headphones",
        name="Headphones treble",
        native_min_value=-6,
        native_max_value=6,
        native_step=0.5,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        entity_registry_enabled_default=False,
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


class YamahaYncaNumber(YamahaYncaSettingEntityMixin, NumberEntity):
    """Representation of a number on a Yamaha Ynca device."""

    entity_description: NumberEntityDescription

    @property
    def native_value(self) -> float | None:
        """Return the value reported by the number."""
        return getattr(self._zone, self.entity_description.key)

    def set_native_value(self, value: float) -> None:
        setattr(self._zone, self.entity_description.key, value)
