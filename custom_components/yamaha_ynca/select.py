from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.helpers.entity import EntityCategory
from homeassistant.util import slugify

import ynca

from .const import (
    CONF_SELECTED_SURROUND_DECODERS,
    TWOCHDECODER_STRINGS,
    ZONE_ATTRIBUTE_NAMES,
)
from .entity import YamahaYncaSettingEntity
from .helpers import extract_protocol_version, subunit_supports_entitydescription_key

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ynca.subunit import SubunitBase
    from ynca.subunits.zone import ZoneBase

    from . import YamahaYncaConfigEntry


# For 2CHDECODER, there are multiple ProLogic II variants that map to same functionality on receivers
# Older receivers have DolbyPl2xyyy variants which get mapped to DolbyPl2yyy if no presence speakers are available
# Newer receivers have DolbyProLogicII_yyy variants instead of DolbyPl2yyy
# We use this mapping to be able to show ProLogic II in the UI and selected the correct values to send.
# (note that currently the DolbyPl2x variants can not be set, lets fix that when requested)
SURROUNDDECODEROPTIONS_PROLOGIC_II_MAPPING = {
    ynca.TwoChDecoder.DolbyPl2xGame: ynca.TwoChDecoder.DolbyPl2Game,
    ynca.TwoChDecoder.DolbyPl2xMovie: ynca.TwoChDecoder.DolbyPl2Movie,
    ynca.TwoChDecoder.DolbyPl2xMusic: ynca.TwoChDecoder.DolbyPl2Music,
    ynca.TwoChDecoder.DolbyProLogicII_Game: ynca.TwoChDecoder.DolbyPl2Game,
    ynca.TwoChDecoder.DolbyProLogicII_Movie: ynca.TwoChDecoder.DolbyPl2Movie,
    ynca.TwoChDecoder.DolbyProLogicII_Music: ynca.TwoChDecoder.DolbyPl2Music,
}

PROLOGIC_II_TO_NEW_PROTOCOL_MAPPING = {
    ynca.TwoChDecoder.DolbyPl2Game: ynca.TwoChDecoder.DolbyProLogicII_Game,
    ynca.TwoChDecoder.DolbyPl2Movie: ynca.TwoChDecoder.DolbyProLogicII_Movie,
    ynca.TwoChDecoder.DolbyPl2Music: ynca.TwoChDecoder.DolbyProLogicII_Music,
}


class InitialVolumeMode(Enum):
    CONFIGURED_INITIAL_VOLUME = "configured_initial_volume"
    LAST_VALUE = "last_value"
    MUTE = "mute"


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
                    entity_description.entity_class(
                        config_entry,
                        config_entry.entry_id,
                        zone_subunit,
                        entity_description,
                    )
                    for entity_description in ENTITY_DESCRIPTIONS
                    if entity_description.is_supported(zone_subunit)
                ]
            )

    # These are features on the SYS subunit, but they are tied to a zone
    entities.extend(
        YamahaYncaSelect(
            config_entry,
            config_entry.entry_id,
            domain_entry_data.api.sys,  # type: ignore[arg-type]
            entity_description,
            associated_zone=zone_subunit,
        )
        for entity_description in SYS_ENTITY_DESCRIPTIONS
        if getattr(domain_entry_data.api.sys, entity_description.key, None) is not None
        and entity_description.associated_zone_attr
        and (
            zone_subunit := getattr(
                domain_entry_data.api,
                entity_description.associated_zone_attr,
                None,
            )
        )
    )

    async_add_entities(entities)


class YamahaYncaSelect(YamahaYncaSettingEntity, SelectEntity):
    """Representation of a select entity on a Yamaha Ynca device."""

    entity_description: YncaSelectEntityDescription

    def __init__(
        self,
        config_entry: ConfigEntry,
        receiver_unique_id: str,
        subunit: SubunitBase,
        description: YncaSelectEntityDescription,
        associated_zone: ZoneBase | None = None,
    ) -> None:
        super().__init__(receiver_unique_id, subunit, description, associated_zone)

        self._protocol_version = extract_protocol_version(
            config_entry.runtime_data.api.sys.version
        )

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

    def _get_value_for_slug(self, option_slug: str) -> Any:
        value = [
            enum_
            for enum_ in self.entity_description.enum
            if slugify(enum_.value) == option_slug
        ]

        if len(value) == 1:
            return value[0]
        return None

    def select_option(self, option: str) -> None:
        """Change the selected option."""
        if self.entity_description.enum is not None and (
            value := self._get_value_for_slug(option)
        ):
            setattr(
                self._subunit,
                self.entity_description.key,
                self.entity_description.enum(value),
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
        # Map any ProLogic II options to a standard version
        current_option = SURROUNDDECODEROPTIONS_PROLOGIC_II_MAPPING.get(
            current_option, current_option
        )

        return slugify(current_option.value)

    def select_option(self, option: str) -> None:
        """Change the selected option."""
        if value := self._get_value_for_slug(option):
            # Newer receivers use different values for ProLogic II
            if self._protocol_version >= (3, 0):
                value = PROLOGIC_II_TO_NEW_PROTOCOL_MAPPING.get(value, value)

            setattr(
                self._subunit,
                self.entity_description.key,
                self.entity_description.enum(value),
            )


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

    def is_supported(self, zone_subunit: ZoneBase) -> bool:
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
    YncaSelectEntityDescription(
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
    YncaSelectEntityDescription(
        key="sleep",
        entity_category=EntityCategory.CONFIG,
        enum=ynca.Sleep,
        icon="mdi:timer-outline",
    ),
    YncaSelectEntityDescription(
        entity_class=YamahaYncaSelectInitialVolumeMode,
        key="initial_volume_mode",
        entity_category=EntityCategory.CONFIG,
        enum=InitialVolumeMode,
        function_names=["INITVOLMODE", "INITVOLLVL"],
        supported_check=lambda _, zone_subunit: zone_subunit.initvollvl is not None,
    ),
    YncaSelectEntityDescription(
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
    YncaSelectEntityDescription(
        key="sppattern",
        entity_category=EntityCategory.CONFIG,
        enum=ynca.SpPattern,
        icon="mdi:speaker-multiple",
        associated_zone_attr="main",
    ),
]
