from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Callable, List, Type

import ynca

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util import slugify

from .const import (
    CONF_SELECTED_SURROUND_DECODERS,
    DOMAIN,
    TWOCHDECODER_STRINGS,
    ZONE_ATTRIBUTE_NAMES,
    SURROUNDDECODEROPTIONS_PLIIX_MAPPING,
)
from .helpers import DomainEntryData, YamahaYncaSettingEntity

if TYPE_CHECKING:  # pragma: no cover
    from ynca.subunit import SubunitBase
    from ynca.subunits.zone import ZoneBase


class InitialVolumeMode(str, Enum):
    CONFIGURED_INITIAL_VOLUME = "configured_initial_volume"
    LAST_VALUE = "last_value"
    MUTE = "mute"


async def async_setup_entry(hass, config_entry, async_add_entities):

    domain_entry_data: DomainEntryData = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for zone_attr_name in ZONE_ATTRIBUTE_NAMES:
        if zone_subunit := getattr(domain_entry_data.api, zone_attr_name):
            for entity_description in ENTITY_DESCRIPTIONS:
                if entity_description.is_supported(zone_subunit):
                    entities.append(
                        entity_description.entity_class(
                            config_entry,
                            config_entry.entry_id,
                            zone_subunit,
                            entity_description,
                        )
                    )

    async_add_entities(entities)


class YamahaYncaSelect(YamahaYncaSettingEntity, SelectEntity):
    """Representation of a select entity on a Yamaha Ynca device."""

    entity_description: YncaSelectEntityDescription

    def __init__(
        self,
        config_entry: ConfigEntry,
        receiver_unique_id,
        subunit: SubunitBase,
        description: YncaSelectEntityDescription,
        associated_zone: ZoneBase | None = None,
    ):
        super().__init__(receiver_unique_id, subunit, description, associated_zone)

        if description.options_fn is not None:
            self._attr_options = description.options_fn(config_entry)
        elif description.options is None:
            self._attr_options = [
                slugify(e.value) for e in description.enum if e.name != "UNKNOWN"
            ]

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        return slugify(getattr(self._subunit, self.entity_description.key).value)

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
                    self._subunit,
                    self.entity_description.key,
                    self.entity_description.enum(value[0]),
                )


class YamahaYncaSelectInitialVolumeMode(YamahaYncaSelect):
    """
    Representation of a select entity on a Yamaha Ynca device specifically for Initial Volume.
    Initial Volume is special as it depends on 2 attributes (INITVOLLVL and/or INITVOLMODE)
    """

    # Note that _associated_zone is used instead of _subunit
    # both will be the same as initvol is only available on zones
    # and this way type checkers see ZoneBase instead of SubunitBase

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        if self._associated_zone.initvolmode is ynca.InitVolMode.OFF:
            return InitialVolumeMode.LAST_VALUE.value
        # Some (newer?) receivers don't have separate mode
        # and report Off in INITVOLLVL
        if self._associated_zone.initvollvl is ynca.InitVolLvl.OFF:
            return InitialVolumeMode.LAST_VALUE.value
        if self._associated_zone.initvollvl is ynca.InitVolLvl.MUTE:
            return InitialVolumeMode.MUTE.value

        return InitialVolumeMode.CONFIGURED_INITIAL_VOLUME.value

    def select_option(self, option: str) -> None:
        """Change the selected option."""
        value = InitialVolumeMode(option)

        if value is InitialVolumeMode.MUTE:
            self._associated_zone.initvollvl = ynca.InitVolLvl.MUTE
            if self._associated_zone.initvolmode is not None:
                self._associated_zone.initvolmode = ynca.InitVolMode.ON
            return

        if value is InitialVolumeMode.LAST_VALUE:
            if self._associated_zone.initvolmode is not None:
                self._associated_zone.initvolmode = ynca.InitVolMode.OFF
            else:
                self._associated_zone.initvollvl = ynca.InitVolLvl.OFF
            return

        if (
            isinstance(self._associated_zone.initvollvl, ynca.InitVolLvl)
            and self._associated_zone.initvollvl in ynca.InitVolLvl
        ):
            # Was Off or Mute, need to fill in some value
            # Since value is also stored in here there is no previous value
            # Lets just take current volume?
            self._associated_zone.initvollvl = self._associated_zone.vol
        if self._associated_zone.initvolmode is not None:
            self._associated_zone.initvolmode = ynca.InitVolMode.ON


class YamahaYncaSelectSurroundDecoder(YamahaYncaSelect):
    """
    Representation of a select entity on a Yamaha Ynca device specifically for SurroundDecoder.
    Surround Decoder is special in that the receiver transparently translates the
    PLII/PLIIx settings to match receiver configuration.
    E.g. setting DolbyPLIIx on a receiver without presence speakers will fallback to DolbyPLII.
    Solution is to map PLII and PLIIx to same values in HA (as receiver will translate anyway this should work)
    """

    @property
    def current_option(self) -> str | None:
        """Return the selected entity option to represent the entity state."""
        if self._associated_zone.twochdecoder is None:
            return None

        current_option = self._associated_zone.twochdecoder
        # Map any PLLx options back as if it was the normal version
        current_option = SURROUNDDECODEROPTIONS_PLIIX_MAPPING.get(
            current_option, current_option
        )

        return slugify(current_option.value)


@dataclass(frozen=True, kw_only=True)
class YncaSelectEntityDescription(SelectEntityDescription):
    enum: Type[Enum]
    """Enum is used to map and generate options (if not specified) for the select entity."""

    function_names: List[str] | None = None
    """Override which function names indicate updates for this entity. Default is `key.upper()`"""

    entity_class: Type[YamahaYncaSelect] = YamahaYncaSelect
    """YamahaYncaSelect class to instantiate for this entity_description"""

    supported_check: Callable[[YncaSelectEntityDescription, ZoneBase], bool] = (
        lambda entity_description, zone_subunit: getattr(
            zone_subunit, entity_description.key, None
        )
        is not None
    )
    """Callable to check support for this entity on the zone, default checks if attribute `key` is not None."""

    def is_supported(self, zone_subunit: ZoneBase):
        return self.supported_check(self, zone_subunit)

    options_fn: Callable[[ConfigEntry], List[str]] | None = None
    """Override which optionns are supported for this entity."""


ENTITY_DESCRIPTIONS = [
    # Suppress following mypy message, which seems to be not an issue as other values have defaults:
    # custom_components/yamaha_ynca/number.py:19: error: Missing positional arguments "entity_registry_enabled_default", "entity_registry_visible_default", "force_update", "icon", "has_entity_name", "unit_of_measurement", "max_value", "min_value", "step" in call to "NumberEntityDescription"  [call-arg]
    YncaSelectEntityDescription(  # type: ignore
        key="hdmiout",
        entity_category=EntityCategory.CONFIG,
        enum=ynca.HdmiOut,
        icon="mdi:hdmi-port",
    ),
    YncaSelectEntityDescription(  # type: ignore
        key="sleep",
        entity_category=EntityCategory.CONFIG,
        enum=ynca.Sleep,
        icon="mdi:timer-outline",
    ),
    YncaSelectEntityDescription(  # type: ignore
        entity_class=YamahaYncaSelectInitialVolumeMode,
        key="initial_volume_mode",
        entity_category=EntityCategory.CONFIG,
        enum=InitialVolumeMode,
        function_names=["INITVOLMODE", "INITVOLLVL"],
        supported_check=lambda _, zone_subunit: zone_subunit.initvollvl is not None,
    ),
    YncaSelectEntityDescription(  # type: ignore
        entity_class=YamahaYncaSelectSurroundDecoder,
        key="twochdecoder",
        entity_category=EntityCategory.CONFIG,
        enum=ynca.TwoChDecoder,
        icon="mdi:surround-sound",
        options_fn=lambda config_entry: sorted(
            config_entry.options.get(
                CONF_SELECTED_SURROUND_DECODERS, TWOCHDECODER_STRINGS.keys()
            )
        ),
        function_names=["2CHDECODER"],
    ),
]
