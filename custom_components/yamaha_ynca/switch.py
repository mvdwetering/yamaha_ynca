from __future__ import annotations

from dataclasses import dataclass
from math import inf
from time import monotonic
from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.helpers.entity import EntityCategory

import ynca

from .const import ZONE_ATTRIBUTE_NAMES
from .entity import YamahaYncaSettingEntity
from .helpers import subunit_supports_entitydescription_key

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable
    from enum import Enum

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from ynca.subunit import SubunitBase
    from ynca.subunits.zone import ZoneBase

    from . import YamahaYncaConfigEntry


@dataclass(frozen=True, kw_only=True)
class YncaSwitchEntityDescription(SwitchEntityDescription):
    on: Enum | None = None
    off: Enum | None = None
    function_names: list[str] | None = None
    """Function names which indicate updates for this entity. Only needed when it does not match `key.upper()`"""
    associated_zone_attr: str | None = None
    """
    When entity is linked to a function on a subunit that is not a Zone, but should still be part of the Zone
    An example is HDMIOUT1 which is a function on SYS subunit, but applies to Main zone and can only be set when Main zone is On.
    Such relation is indicated here
    """
    supported_check: Callable[[YncaSwitchEntityDescription, ZoneBase], bool] = (
        lambda entity_description, zone_subunit: subunit_supports_entitydescription_key(
            entity_description, zone_subunit
        )
    )
    """
    Callable to check support for this entity on the zone, default checks if attribute `key` is not None.
    This _only_ works for Zone entities, not SYS.
    """

    def is_supported(self, zone_subunit: ZoneBase) -> bool:
        return self.supported_check(self, zone_subunit)


ZONE_ENTITY_DESCRIPTIONS = [
    # Suppress following mypy message, which seems to be not an issue as other values have defaults:
    # custom_components/yamaha_ynca/number.py:19: error: Missing positional arguments "entity_registry_enabled_default", "entity_registry_visible_default", "force_update", "icon", "has_entity_name", "unit_of_measurement", "max_value", "min_value", "step" in call to "NumberEntityDescription"  [call-arg]
    YncaSwitchEntityDescription(
        key="adaptivedrc",
        entity_category=EntityCategory.CONFIG,
        on=ynca.AdaptiveDrc.AUTO,
        off=ynca.AdaptiveDrc.OFF,
    ),
    YncaSwitchEntityDescription(
        key="dirmode",
        entity_category=EntityCategory.CONFIG,
        on=ynca.DirMode.ON,
        off=ynca.DirMode.OFF,
    ),
    YncaSwitchEntityDescription(
        key="enhancer",
        entity_category=EntityCategory.CONFIG,
        on=ynca.Enhancer.ON,
        off=ynca.Enhancer.OFF,
    ),
    YncaSwitchEntityDescription(
        key="hdmiout",
        icon="mdi:hdmi-port",
        entity_category=EntityCategory.CONFIG,
        on=ynca.HdmiOut.OUT,
        off=ynca.HdmiOut.OFF,
        # HDMIOUT is used for receivers with multiple HDMI outputs and single HDMI output
        # This switch handles single HDMI output, so check if HDMI2 does NOT exist and assume there is only one HDMI output
        supported_check=lambda entity_description, zone_subunit: (
            subunit_supports_entitydescription_key(entity_description, zone_subunit)
            and zone_subunit.lipsynchdmiout2offset is None
        ),
    ),
    YncaSwitchEntityDescription(
        key="puredirmode",
        entity_category=EntityCategory.CONFIG,
        on=ynca.PureDirMode.ON,
        off=ynca.PureDirMode.OFF,
    ),
    YncaSwitchEntityDescription(
        key="speakera",
        icon="mdi:speaker-multiple",
        entity_category=EntityCategory.CONFIG,
        on=ynca.SpeakerA.ON,
        off=ynca.SpeakerA.OFF,
        # On receivers with ZoneB the Speaker A/B functions are linked to zonepower is undesired
        # So avoid showing switches in that case
        supported_check=lambda entity_description, zone_subunit: (
            subunit_supports_entitydescription_key(entity_description, zone_subunit)
            and getattr(zone_subunit, "zonebavail", None) is not ynca.ZoneBAvail.READY
        ),
    ),
    YncaSwitchEntityDescription(
        key="speakerb",
        icon="mdi:speaker-multiple",
        entity_category=EntityCategory.CONFIG,
        on=ynca.SpeakerB.ON,
        off=ynca.SpeakerB.OFF,
        # On receivers with ZoneB the Speaker A/B functions are linked to zonepower is undesired
        # So avoid showing switches in that case
        supported_check=lambda entity_description, zone_subunit: (
            subunit_supports_entitydescription_key(entity_description, zone_subunit)
            and getattr(zone_subunit, "zonebavail", None) is not ynca.ZoneBAvail.READY
        ),
    ),
    YncaSwitchEntityDescription(
        key="surroundai",
        icon="mdi:creation",
        entity_category=EntityCategory.CONFIG,
        on=ynca.SurroundAI.ON,
        off=ynca.SurroundAI.OFF,
    ),
    YncaSwitchEntityDescription(
        key="threedcinema",
        entity_category=EntityCategory.CONFIG,
        function_names=["3DCINEMA"],
        on=ynca.ThreeDeeCinema.AUTO,
        off=ynca.ThreeDeeCinema.OFF,
    ),
]

SYS_ENTITY_DESCRIPTIONS = [
    # Suppress following mypy message, which seems to be not an issue as other values have defaults:
    # custom_components/yamaha_ynca/number.py:19: error: Missing positional arguments "entity_registry_enabled_default", "entity_registry_visible_default", "force_update", "icon", "has_entity_name", "unit_of_measurement", "max_value", "min_value", "step" in call to "NumberEntityDescription"  [call-arg]
    YncaSwitchEntityDescription(
        key="hdmiout1",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:hdmi-port",
        on=ynca.HdmiOutOnOff.ON,
        off=ynca.HdmiOutOnOff.OFF,
        associated_zone_attr="main",
    ),
    YncaSwitchEntityDescription(
        key="hdmiout2",
        entity_category=EntityCategory.CONFIG,
        icon="mdi:hdmi-port",
        on=ynca.HdmiOutOnOff.ON,
        off=ynca.HdmiOutOnOff.OFF,
        associated_zone_attr="main",
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
                    YamahaYncaSwitch(
                        config_entry.entry_id, zone_subunit, entity_description
                    )
                    for entity_description in ZONE_ENTITY_DESCRIPTIONS
                    if entity_description.is_supported(zone_subunit)
                ]
            )

    # These are features on the SYS subunit, but they are tied to a zone
    entities.extend(
        [
            YamahaYncaSwitch(
                config_entry.entry_id,
                domain_entry_data.api.sys,  # type: ignore[arg-type]
                entity_description,
                associated_zone=zone_subunit,
            )
            for entity_description in SYS_ENTITY_DESCRIPTIONS
            if (
                getattr(domain_entry_data.api.sys, entity_description.key, None)
                is not None
            )
            and entity_description.associated_zone_attr
            and (
                zone_subunit := getattr(
                    domain_entry_data.api,
                    entity_description.associated_zone_attr,
                    None,
                )
            )
        ]
    )

    async_add_entities(entities)


class YamahaYncaSwitch(YamahaYncaSettingEntity, SwitchEntity):  # type: ignore[misc]
    """Representation of a switch on a Yamaha Ynca device."""

    entity_description: YncaSwitchEntityDescription

    def __init__(
        self,
        receiver_unique_id: str,
        subunit: SubunitBase,
        description: YncaSwitchEntityDescription,
        associated_zone: ZoneBase | None = None,
    ) -> None:
        super().__init__(receiver_unique_id, subunit, description, associated_zone)
        self._dirmode_get_sent = -inf  # Initialize far in the past

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        return (
            getattr(self._subunit, self.entity_description.key, None)
            == self.entity_description.on
        )

    def turn_on(self, **_kwargs: Any) -> None:
        """Turn the entity on."""
        setattr(self._subunit, self.entity_description.key, self.entity_description.on)

    def turn_off(self, **_kwargs: Any) -> None:
        """Turn the entity off."""
        setattr(self._subunit, self.entity_description.key, self.entity_description.off)

    def update_callback(self, function: str, value: Any) -> None:
        super().update_callback(function, value)

        # DIRMODE does not (always?) report changes
        # but it does report STRAIGHT when DIRMODE changes, even when STRAIGHT did not change
        # So manually request an update for DIRMODE when STRAIGHT is reported
        if self.entity_description.key == "dirmode" and function == "STRAIGHT":
            # But because STRAIGHT also gets reported on GET we need to avoid an infinite loop
            if monotonic() - self._dirmode_get_sent < 0.5:  # noqa: PLR2004
                return

            self._associated_zone._connection.get(  # noqa: SLF001
                self._associated_zone.id, "DIRMODE"
            )
            self._dirmode_get_sent = monotonic()
