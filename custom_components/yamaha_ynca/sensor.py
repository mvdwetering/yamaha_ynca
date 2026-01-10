from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from propcache.api import cached_property

import ynca

from .const import (
    CONF_SELECTED_INPUTS,
    ZONE_ATTRIBUTE_NAMES,
)
from .entity import YamahaYncaSettingEntity
from .helpers import subunit_supports_entitydescription_key
from .input_helpers import InputHelper

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ynca.subunits.zone import ZoneBase

    from . import YamahaYncaConfigEntry


@dataclass(frozen=True, kw_only=True)
class YncaSensorEntityDescription(SensorEntityDescription):

    is_supported: Callable[[YncaSensorEntityDescription, ZoneBase], bool] = (
        lambda entity_description, zone_subunit: subunit_supports_entitydescription_key(
            entity_description, zone_subunit
        )
    )
    """Callable to check support for this entity on the zone, default checks if attribute `key` is not None."""

    value_converter: Callable[[ynca.YncaApi, Any], str | None] | None = None
    """Optional callable to convert the raw value to a string for the sensor state. Default is str()."""

    options_fn: Callable[[ynca.YncaApi, Any], list[str]] | None = None
    """Optional callable to provide which options are supported for this entity. For static lists use `options`. Only relevant for deviceclass enum."""

    extra_data_fn: Callable[[YamahaYncaConfigEntry, ZoneBase], Any] | None = None
    """Optional callable to collect extra data when the entity is created. It will be stored in the entity `_extra_state` attribute."""


def get_selected_inputs(
    config_entry: YamahaYncaConfigEntry, zone_subunit: ZoneBase
) -> set[str]:
    all_inputs = [
        input_.value for input_ in ynca.Input if input_ is not ynca.Input.UNKNOWN
    ]

    selected_inputs: list[str] = config_entry.options.get(zone_subunit.id, {}).get(
        CONF_SELECTED_INPUTS, list(all_inputs)
    )

    return set(selected_inputs)


ENTITY_DESCRIPTIONS = [
    YncaSensorEntityDescription(
        key="inp",
        icon="mdi:import",
        device_class=SensorDeviceClass.ENUM,
        entity_registry_enabled_default=False,
        is_supported=lambda _entity_description, zone_subunit: (
            # Only supported on MAIN zone, Zone 2 does not switch inputs it seems
            isinstance(zone_subunit, ynca.Main)
        ),
        options_fn=lambda api, extra_data: InputHelper.get_source_list(api, extra_data),
        value_converter=lambda api, value: InputHelper.get_name_of_input(api, value),
        extra_data_fn=get_selected_inputs,
    ),
]


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
                    YamahaYncaSensor(
                        config_entry,
                        config_entry.entry_id,
                        zone_subunit,
                        entity_description,
                    )
                    for entity_description in ENTITY_DESCRIPTIONS
                    if entity_description.is_supported(entity_description, zone_subunit)
                ]
            )

    async_add_entities(entities)


class YamahaYncaSensor(YamahaYncaSettingEntity, SensorEntity):
    """Representation of a sensor entity on a Yamaha Ynca device."""

    entity_description: YncaSensorEntityDescription

    def __init__(
        self,
        config_entry: YamahaYncaConfigEntry,
        receiver_unique_id: str,
        subunit: ZoneBase,
        description: YncaSensorEntityDescription,
    ) -> None:
        super().__init__(receiver_unique_id, subunit, description)
        self._api = config_entry.runtime_data.api

        self._extra_data = (
            description.extra_data_fn(config_entry, subunit)
            if description.extra_data_fn
            else None
        )

    @property
    def available(self) -> bool:
        # In contrast to most other entities, sensors are always available (at least the current ones)
        return True

    @property
    def native_value(self) -> str | None:
        """Return the state of the sensor."""
        if value := getattr(self._subunit, self.entity_description.key, None):
            return (
                str(value)
                if self.entity_description.value_converter is None
                else self.entity_description.value_converter(self._api, value)
            )

        return value

    @cached_property
    def options(self) -> list[str] | None:
        """Return a set of possible options."""
        if self.entity_description.options_fn is not None:
            return self.entity_description.options_fn(self._api, self._extra_data)

        return super().options
