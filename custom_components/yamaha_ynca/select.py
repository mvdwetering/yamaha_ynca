from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Type

import ynca

from homeassistant.components.select import (
    SelectEntity,
    SelectEntityDescription,
)
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util import slugify

from .const import DOMAIN, ZONE_ATTRIBUTE_NAMES
from .helpers import DomainEntryData, YamahaYncaSettingEntityMixin


@dataclass
class YncaSelectEntityDescription(SelectEntityDescription):
    enum: Type[Enum] | None = None
    function_names: List[str] | None = None
    """Function names which indicate updates for this entity. Only needed when it does not match `key.upper()`"""


def build_enum_options_list(enum: Type[Enum]) -> List[str]:
    return [slugify(e.value) for e in enum if e.name != "UNKNOWN"]


class InitialVolumeMode(str, Enum):
    CONFIGURED_INITIAL_VOLUME = "configured_initial_volume"
    LAST_VALUE = "last_value"
    MUTE = "mute"


ENTITY_DESCRIPTIONS = [
    # Suppress following mypy message, which seems to be not an issue as other values have defaults:
    # custom_components/yamaha_ynca/number.py:19: error: Missing positional arguments "entity_registry_enabled_default", "entity_registry_visible_default", "force_update", "icon", "has_entity_name", "unit_of_measurement", "max_value", "min_value", "step" in call to "NumberEntityDescription"  [call-arg]
    YncaSelectEntityDescription(  # type: ignore
        key="hdmiout",
        entity_category=EntityCategory.CONFIG,
        enum=ynca.HdmiOut,
        icon="mdi:hdmi-port",
        name="HDMI Out",
        options=build_enum_options_list(ynca.HdmiOut),
    ),
    YncaSelectEntityDescription(  # type: ignore
        key="sleep",
        entity_category=EntityCategory.CONFIG,
        enum=ynca.Sleep,
        icon="mdi:timer-outline",
        name="Sleep timer",
        options=build_enum_options_list(ynca.Sleep),
    ),
]

InitialVolumeModeEntityDescription = YncaSelectEntityDescription(  # type: ignore
    key="initial_volume_mode",
    entity_category=EntityCategory.CONFIG,
    enum=InitialVolumeMode,
    name="Initial Volume Mode",
    options=build_enum_options_list(InitialVolumeMode),
    function_names=["INITVOLMODE", "INITVOLLVL"],
)


async def async_setup_entry(hass, config_entry, async_add_entities):

    domain_entry_data: DomainEntryData = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for zone_attr_name in ZONE_ATTRIBUTE_NAMES:
        if zone_subunit := getattr(domain_entry_data.api, zone_attr_name):
            for entity_description in ENTITY_DESCRIPTIONS:
                if getattr(zone_subunit, entity_description.key, None) is not None:
                    entities.append(
                        YamahaYncaSelect(
                            config_entry.entry_id, zone_subunit, entity_description
                        )
                    )

            if zone_subunit.initvollvl is not None:
                entities.append(
                    YamahaYncaSelectInitialVolumeMode(
                        config_entry.entry_id,
                        zone_subunit,
                        InitialVolumeModeEntityDescription,
                    )
                )

    async_add_entities(entities)


class YamahaYncaSelect(YamahaYncaSettingEntityMixin, SelectEntity):
    """Representation of a select entity on a Yamaha Ynca device."""

    entity_description: YncaSelectEntityDescription

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        return slugify(getattr(self._zone, self.entity_description.key).value)

    def select_option(self, option: str) -> None:
        """Change the selected option."""
        if self.entity_description.enum is not None:
            value = [
                e.value
                for e in self.entity_description.enum
                if slugify(e.value) == option
            ]

            if len(value) == 1:
                setattr(
                    self._zone,
                    self.entity_description.key,
                    self.entity_description.enum(value[0]),
                )


class YamahaYncaSelectInitialVolumeMode(YamahaYncaSelect):
    """
    Representation of a select entity on a Yamaha Ynca device specifically for Initial Volume.
    Initial Volume is special as it dependes on 2 attributes (INITVOLLVL and/or INITVOLMODE)
    """

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        if self._zone.initvolmode is ynca.InitVolMode.OFF:
            return InitialVolumeMode.LAST_VALUE.value
        # Some (newer?) receivers dont have separate mode
        # and report Off in INITVOLLVL
        if self._zone.initvollvl is ynca.InitVolLvl.OFF:
            return InitialVolumeMode.LAST_VALUE.value
        if self._zone.initvollvl is ynca.InitVolLvl.MUTE:
            return InitialVolumeMode.MUTE.value

        return InitialVolumeMode.CONFIGURED_INITIAL_VOLUME.value

    def select_option(self, option: str) -> None:
        """Change the selected option."""
        value = InitialVolumeMode(option)

        if value is InitialVolumeMode.MUTE:
            self._zone.initvollvl = ynca.InitVolLvl.MUTE
            if self._zone.initvolmode is not None:
                self._zone.initvolmode = ynca.InitVolMode.ON
            return

        if value is InitialVolumeMode.LAST_VALUE:
            if self._zone.initvolmode is not None:
                self._zone.initvolmode = ynca.InitVolMode.OFF
            else:
                self._zone.initvollvl = ynca.InitVolLvl.OFF
            return

        if (
            isinstance(self._zone.initvollvl, ynca.InitVolLvl)
            and self._zone.initvollvl in ynca.InitVolLvl
        ):
            # Was Off or Mute, need to fill in some value
            # Since value is also stored in here there is no previous value
            # Lets just take current volume?
            self._zone.initvollvl = self._zone.vol
        if self._zone.initvolmode is not None:
            self._zone.initvolmode = ynca.InitVolMode.ON
