from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any, List

import ynca

from homeassistant.components.switch import (
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, ZONE_ATTRIBUTE_NAMES
from .helpers import DomainEntryData, YamahaYncaSettingEntityMixin


@dataclass
class YncaSwitchEntityDescription(SwitchEntityDescription):
    on: Enum | None = None
    off: Enum | None = None
    function_names: List[str] | None = None
    """Function names which indicate updates for this entity. Only needed when it does not match `key.upper()`"""


ENTITY_DESCRIPTIONS = [
    # Suppress following mypy message, which seems to be not an issue as other values have defaults:
    # custom_components/yamaha_ynca/number.py:19: error: Missing positional arguments "entity_registry_enabled_default", "entity_registry_visible_default", "force_update", "icon", "has_entity_name", "unit_of_measurement", "max_value", "min_value", "step" in call to "NumberEntityDescription"  [call-arg]
    YncaSwitchEntityDescription(  # type: ignore
        key="enhancer",
        entity_category=EntityCategory.CONFIG,
        name="Compressed Music Enhancer",
        on=ynca.Enhancer.ON,
        off=ynca.Enhancer.OFF,
    ),
    YncaSwitchEntityDescription(  # type: ignore
        key="adaptivedrc",
        entity_category=EntityCategory.CONFIG,
        name="Adaptive DRC",
        on=ynca.AdaptiveDrc.AUTO,
        off=ynca.AdaptiveDrc.OFF,
    ),
    YncaSwitchEntityDescription(  # type: ignore
        key="threedcinema",
        entity_category=EntityCategory.CONFIG,
        function_names=["3DCINEMA"],
        name="CINEMA DSP 3D Mode",
        on=ynca.ThreeDeeCinema.AUTO,
        off=ynca.ThreeDeeCinema.OFF,
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
                        YamahaYncaSwitch(
                            config_entry.entry_id, zone_subunit, entity_description
                        )
                    )

    async_add_entities(entities)


class YamahaYncaSwitch(YamahaYncaSettingEntityMixin, SwitchEntity):
    """Representation of a switch on a Yamaha Ynca device."""

    entity_description: YncaSwitchEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return (
            getattr(self._zone, self.entity_description.key)
            == self.entity_description.on
        )

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        setattr(self._zone, self.entity_description.key, self.entity_description.on)

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        setattr(self._zone, self.entity_description.key, self.entity_description.off)
