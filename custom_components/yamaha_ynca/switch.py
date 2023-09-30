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
from .helpers import DomainEntryData, YamahaYncaSettingEntity


@dataclass
class YncaSwitchEntityDescription(SwitchEntityDescription):
    on: Enum | None = None
    off: Enum | None = None
    function_names: List[str] | None = None
    """Function names which indicate updates for this entity. Only needed when it does not match `key.upper()`"""
    associated_zone_attr: str | None = None
    """
    When entity is linked to a function on a subunit that is not a Zone, but should still be part of the Zone
    An example is HDMIOUT1 which is a function on SYS subunit, but applies to Main zone and can only be set when Main zone is On.
    Such relation is indicated here
    """

ZONE_ENTITY_DESCRIPTIONS = [
    # Suppress following mypy message, which seems to be not an issue as other values have defaults:
    # custom_components/yamaha_ynca/number.py:19: error: Missing positional arguments "entity_registry_enabled_default", "entity_registry_visible_default", "force_update", "icon", "has_entity_name", "unit_of_measurement", "max_value", "min_value", "step" in call to "NumberEntityDescription"  [call-arg]
    YncaSwitchEntityDescription(  # type: ignore
        key="enhancer",
        entity_category=EntityCategory.CONFIG,
        on=ynca.Enhancer.ON,
        off=ynca.Enhancer.OFF,
    ),
    YncaSwitchEntityDescription(  # type: ignore
        key="adaptivedrc",
        entity_category=EntityCategory.CONFIG,
        on=ynca.AdaptiveDrc.AUTO,
        off=ynca.AdaptiveDrc.OFF,
    ),
    YncaSwitchEntityDescription(  # type: ignore
        key="threedcinema",
        entity_category=EntityCategory.CONFIG,
        function_names=["3DCINEMA"],
        on=ynca.ThreeDeeCinema.AUTO,
        off=ynca.ThreeDeeCinema.OFF,
    ),
    YncaSwitchEntityDescription(  # type: ignore
        key="puredirmode",
        entity_category=EntityCategory.CONFIG,
        on=ynca.PureDirMode.ON,
        off=ynca.PureDirMode.OFF,
    ),
]

SYS_ENTITY_DESCRIPTIONS = [
    # Suppress following mypy message, which seems to be not an issue as other values have defaults:
    # custom_components/yamaha_ynca/number.py:19: error: Missing positional arguments "entity_registry_enabled_default", "entity_registry_visible_default", "force_update", "icon", "has_entity_name", "unit_of_measurement", "max_value", "min_value", "step" in call to "NumberEntityDescription"  [call-arg]
    YncaSwitchEntityDescription(  # type: ignore
        key="hdmiout1",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:hdmi-port",
        on=ynca.HdmiOutOnOff.ON,
        off=ynca.HdmiOutOnOff.OFF,
        associated_zone_attr="main",
    ),
    YncaSwitchEntityDescription(  # type: ignore
        key="hdmiout2",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:hdmi-port",
        on=ynca.HdmiOutOnOff.ON,
        off=ynca.HdmiOutOnOff.OFF,
        associated_zone_attr="main",
    ),
]

async def async_setup_entry(hass, config_entry, async_add_entities):

    domain_entry_data: DomainEntryData = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for zone_attr_name in ZONE_ATTRIBUTE_NAMES:
        if zone_subunit := getattr(domain_entry_data.api, zone_attr_name):
            for entity_description in ZONE_ENTITY_DESCRIPTIONS:
                if getattr(zone_subunit, entity_description.key, None) is not None:
                    entities.append(
                        YamahaYncaSwitch(
                            config_entry.entry_id, zone_subunit, entity_description
                        )
                    )

    # These are features on the SYS subunit, but they are tied to a zone
    assert(domain_entry_data.api.sys is not None)
    for entity_description in SYS_ENTITY_DESCRIPTIONS:
        assert(isinstance(entity_description.associated_zone_attr, str))
        if getattr(domain_entry_data.api.sys, entity_description.key, None) is not None:
            if zone_subunit := getattr(domain_entry_data.api, entity_description.associated_zone_attr):
                entities.append(
                    YamahaYncaSwitch(
                        config_entry.entry_id, domain_entry_data.api.sys, entity_description, associated_zone=zone_subunit
                    )
                )

    async_add_entities(entities)


class YamahaYncaSwitch(YamahaYncaSettingEntity, SwitchEntity):
    """Representation of a switch on a Yamaha Ynca device."""

    entity_description: YncaSwitchEntityDescription

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return (
            getattr(self._subunit, self.entity_description.key)
            == self.entity_description.on
        )

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the entity on."""
        setattr(self._subunit, self.entity_description.key, self.entity_description.on)

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the entity off."""
        setattr(self._subunit, self.entity_description.key, self.entity_description.off)
