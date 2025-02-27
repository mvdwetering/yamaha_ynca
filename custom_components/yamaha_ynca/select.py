from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

import ynca

from . import YamahaYncaConfigEntry
from .const import (
    CONF_SELECTED_SURROUND_DECODERS,
    SURROUNDDECODEROPTIONS_PLIIX_MAPPING,
    TWOCHDECODER_STRINGS,
    ZONE_ATTRIBUTE_NAMES,
)
from .helpers import YamahaYncaSettingEntity, subunit_supports_entitydescription_key

if TYPE_CHECKING:  # pragma: no cover
    from ynca.subunit import SubunitBase
    from ynca.subunits.zone import ZoneBase


class InitialVolumeMode(str, Enum):
    CONFIGURED_INITIAL_VOLUME = "configured_initial_volume"
    LAST_VALUE = "last_value"
    MUTE = "mute"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: YamahaYncaConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    domain_entry_data = config_entry.runtime_data

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

    # These are features on the SYS subunit, but they are tied to a zone
    assert domain_entry_data.api.sys is not None
    for entity_description in SYS_ENTITY_DESCRIPTIONS:
        assert isinstance(entity_description.associated_zone_attr, str)
        if (
            getattr(domain_entry_data.api.sys, entity_description.key, None) is not None
        ) and (
            zone_subunit := getattr(
                domain_entry_data.api, entity_description.associated_zone_attr
            )
        ):
            entities.append(
                YamahaYncaSelect(
                    config_entry,
                    config_entry.entry_id,
                    domain_entry_data.api.sys,
                    entity_description,
                    associated_zone=zone_subunit,
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
    """Representation of a select entity on a Yamaha Ynca device specifically for Initial Volume.
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
    """Representation of a select entity on a Yamaha Ynca device specifically for SurroundDecoder.
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
    enum: type[Enum]
    """Enum is used to map and generate options (if not specified) for the select entity."""

    function_names: list[str] | None = None
    """Override which function names indicate updates for this entity. Default is `key.upper()`"""

    entity_class: type[YamahaYncaSelect] = YamahaYncaSelect
    """YamahaYncaSelect class to instantiate for this entity_description"""

    supported_check: Callable[[YncaSelectEntityDescription, ZoneBase], bool] = (
        lambda entity_description, zone_subunit: subunit_supports_entitydescription_key(
            entity_description, zone_subunit
        )
    )
    """Callable to check support for this entity on the zone, default checks if attribute `key` is not None."""

    def is_supported(self, zone_subunit: ZoneBase):
        return self.supported_check(self, zone_subunit)

    options_fn: Callable[[ConfigEntry], list[str]] | None = None
    """Override which options are supported for this entity."""

    associated_zone_attr: str | None = None
    """
    When entity is linked to a function on a subunit that is not a Zone, but should still be part of the Zone
    An example is SPPATTERN which is a function on SYS subunit, but I want to display as part of MAIN zone
    Such relation is indicated here
    """


ENTITY_DESCRIPTIONS = [
    YncaSelectEntityDescription(  # type: ignore
        key="hdmiout",
        entity_category=EntityCategory.CONFIG,
        enum=ynca.HdmiOut,
        icon="mdi:hdmi-port",
        options=[
            slugify(e.value)
            for e in [
                ynca.HdmiOut.OFF,
                ynca.HdmiOut.OUT1,
                ynca.HdmiOut.OUT2,
                ynca.HdmiOut.OUT1_PLUS_2,
            ]
        ],
        # HDMIOUT is used for receivers with multiple HDMI outputs and single HDMI output
        # This select handles multiple HDMI outputs, so check if HDMI2 exists to see if it is supported
        supported_check=lambda entity_description, zone_subunit: (
            subunit_supports_entitydescription_key(entity_description, zone_subunit)
            and zone_subunit.lipsynchdmiout2offset is not None
        ),
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

SYS_ENTITY_DESCRIPTIONS = [
    YncaSelectEntityDescription(  # type: ignore
        key="sppattern",
        entity_category=EntityCategory.CONFIG,
        enum=ynca.SpPattern,
        icon="mdi:speaker-multiple",
        associated_zone_attr="main",
    ),
]
