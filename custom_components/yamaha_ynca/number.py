from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS
from homeassistant.helpers.entity import EntityCategory

import ynca

from .const import ZONE_ATTRIBUTE_NAMES, ZONE_MAX_VOLUME, ZONE_MIN_VOLUME
from .helpers import YamahaYncaSettingEntity

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from . import YamahaYncaConfigEntry


def volume_native_max_value_fn(associated_zone: ynca.subunits.zone.ZoneBase) -> float:
    return float(
        associated_zone.maxvol
        if associated_zone.maxvol is not None
        else ZONE_MAX_VOLUME
    )


@dataclass(frozen=True, kw_only=True)
class YncaNumberEntityDescription(NumberEntityDescription):
    function_names: list[str] | None = None
    """Function names which indicate updates for this entity. Only needed when it does not match `key.upper()`"""
    native_max_value_fn: Callable[[ynca.subunits.zone.ZoneBase], float] | None = None
    """Function that returns max value. Use when a fixed number is not enough"""


ENTITY_DESCRIPTIONS = [
    # Suppress following mypy message, which seems to be not an issue as other values have defaults:
    # custom_components/yamaha_ynca/number.py:19: error: Missing positional arguments "entity_registry_enabled_default", "entity_registry_visible_default", "force_update", "icon", "has_entity_name", "unit_of_measurement", "max_value", "min_value", "step" in call to "NumberEntityDescription"  [call-arg]
    YncaNumberEntityDescription(
        key="maxvol",
        device_class=NumberDeviceClass.SIGNAL_STRENGTH,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:volume-vibrate",
        native_min_value=-30,
        native_max_value=ZONE_MAX_VOLUME,
        native_step=0.5,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
    ),
    YncaNumberEntityDescription(
        key="vol",
        device_class=NumberDeviceClass.SIGNAL_STRENGTH,
        icon="mdi:volume-high",
        native_min_value=ZONE_MIN_VOLUME,
        native_max_value_fn=volume_native_max_value_fn,
        native_step=0.5,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        function_names=["VOL", "MAXVOL"],
    ),
    YncaNumberEntityDescription(
        key="spbass",
        device_class=NumberDeviceClass.SIGNAL_STRENGTH,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:speaker",
        native_min_value=-6,
        native_max_value=6,
        native_step=0.5,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        entity_registry_enabled_default=False,
    ),
    YncaNumberEntityDescription(
        key="sptreble",
        entity_category=EntityCategory.CONFIG,
        device_class=NumberDeviceClass.SIGNAL_STRENGTH,
        icon="mdi:speaker",
        native_min_value=-6,
        native_max_value=6,
        native_step=0.5,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        entity_registry_enabled_default=False,
    ),
    YncaNumberEntityDescription(
        key="hpbass",
        device_class=NumberDeviceClass.SIGNAL_STRENGTH,
        entity_category=EntityCategory.CONFIG,
        icon="mdi:headphones",
        native_min_value=-6,
        native_max_value=6,
        native_step=0.5,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        entity_registry_enabled_default=False,
    ),
    YncaNumberEntityDescription(
        key="hptreble",
        entity_category=EntityCategory.CONFIG,
        device_class=NumberDeviceClass.SIGNAL_STRENGTH,
        icon="mdi:headphones",
        native_min_value=-6,
        native_max_value=6,
        native_step=0.5,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        entity_registry_enabled_default=False,
    ),
]

InitialVolumeValueEntityDescription = YncaNumberEntityDescription(
    key="initvollvl",
    entity_category=EntityCategory.CONFIG,
    device_class=NumberDeviceClass.SIGNAL_STRENGTH,
    icon="mdi:knob",
    native_min_value=-80.0,
    native_max_value=ZONE_MAX_VOLUME,
    native_step=0.5,
    native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
    function_names=["INITVOLLVL", "INITVOLMODE"],
)


async def async_setup_entry(
    _hass: HomeAssistant,
    config_entry: YamahaYncaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    domain_entry_data = config_entry.runtime_data

    entities = []
    for zone_attr_name in ZONE_ATTRIBUTE_NAMES:
        if zone_subunit := getattr(domain_entry_data.api, zone_attr_name):
            entities.extend(
                [
                    YamahaYncaNumber(
                        config_entry.entry_id, zone_subunit, entity_description
                    )
                    for entity_description in ENTITY_DESCRIPTIONS
                    if getattr(zone_subunit, entity_description.key, None) is not None
                ]
            )

            if zone_subunit.initvollvl is not None:
                entities.append(
                    YamahaYncaNumberInitialVolume(
                        config_entry.entry_id,
                        zone_subunit,
                        InitialVolumeValueEntityDescription,
                    )
                )

    async_add_entities(entities)


class YamahaYncaNumber(YamahaYncaSettingEntity, NumberEntity):
    """Representation of a number on a Yamaha Ynca device."""

    entity_description: YncaNumberEntityDescription

    @property
    def native_value(self) -> float | None:
        """Return the value reported by the number."""
        return getattr(self._subunit, self.entity_description.key, None)

    @property
    def native_max_value(self) -> float:
        """Return the maximum value."""
        if fn := self.entity_description.native_max_value_fn:
            return fn(self._associated_zone)
        return float(super().native_max_value)

    def set_native_value(self, value: float) -> None:
        setattr(self._subunit, self.entity_description.key, value)


class YamahaYncaNumberInitialVolume(YamahaYncaNumber):
    """Representation Initial Volume level.

    This is special as it is not always a number and can depend on InitLvlMode
    """

    @property
    def available(self) -> bool:
        return (
            super().available
            and isinstance(self._associated_zone.initvollvl, float)
            and self._associated_zone.initvolmode is not ynca.InitVolMode.OFF
        )
