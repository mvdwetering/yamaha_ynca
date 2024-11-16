from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, List

import ynca

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import YamahaYncaConfigEntry
from .const import ZONE_ATTRIBUTE_NAMES
from .helpers import YamahaYncaSettingEntity, subunit_supports_entitydescription_key

if TYPE_CHECKING:  # pragma: no cover
    from ynca.subunits.zone import ZoneBase
    from ynca.subunit import SubunitBase

@dataclass(frozen=True, kw_only=True)
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
    supported_check: Callable[[YncaSwitchEntityDescription, ZoneBase], bool] = (
        lambda entity_description, zone_subunit: subunit_supports_entitydescription_key(entity_description, zone_subunit)
    )
    """
    Callable to check support for this entity on the zone, default checks if attribute `key` is not None.
    This _only_ works for Zone entities, not SYS.
    """

    def is_supported(self, zone_subunit: ZoneBase):
        return self.supported_check(self, zone_subunit)


ZONE_ENTITY_DESCRIPTIONS = [
    # Suppress following mypy message, which seems to be not an issue as other values have defaults:
    # custom_components/yamaha_ynca/number.py:19: error: Missing positional arguments "entity_registry_enabled_default", "entity_registry_visible_default", "force_update", "icon", "has_entity_name", "unit_of_measurement", "max_value", "min_value", "step" in call to "NumberEntityDescription"  [call-arg]
    YncaSwitchEntityDescription(  # type: ignore
        key="adaptivedrc",
        entity_category=EntityCategory.CONFIG,
        on=ynca.AdaptiveDrc.AUTO,
        off=ynca.AdaptiveDrc.OFF,
    ),
    YncaSwitchEntityDescription(  # type: ignore
        key="dirmode",
        entity_category=EntityCategory.CONFIG,
        on=ynca.DirMode.ON,
        off=ynca.DirMode.OFF,
    ),
    YncaSwitchEntityDescription(  # type: ignore
        key="enhancer",
        entity_category=EntityCategory.CONFIG,
        on=ynca.Enhancer.ON,
        off=ynca.Enhancer.OFF,
    ),
    YncaSwitchEntityDescription(  # type: ignore
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
    YncaSwitchEntityDescription(  # type: ignore
        key="puredirmode",
        entity_category=EntityCategory.CONFIG,
        on=ynca.PureDirMode.ON,
        off=ynca.PureDirMode.OFF,
    ),
    YncaSwitchEntityDescription(  # type: ignore
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
    YncaSwitchEntityDescription(  # type: ignore
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
    YncaSwitchEntityDescription(  # type: ignore
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


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: YamahaYncaConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    domain_entry_data = config_entry.runtime_data

    entities = []
    for zone_attr_name in ZONE_ATTRIBUTE_NAMES:
        if zone_subunit := getattr(domain_entry_data.api, zone_attr_name):
            for entity_description in ZONE_ENTITY_DESCRIPTIONS:
                if entity_description.is_supported(zone_subunit):
                    entities.append(
                        YamahaYncaSwitch(
                            config_entry.entry_id, zone_subunit, entity_description
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
                YamahaYncaSwitch(
                    config_entry.entry_id,
                    domain_entry_data.api.sys,
                    entity_description,
                    associated_zone=zone_subunit,
                )
            )

    async_add_entities(entities)


class YamahaYncaSwitch(YamahaYncaSettingEntity, SwitchEntity):
    """Representation of a switch on a Yamaha Ynca device."""

    entity_description: YncaSwitchEntityDescription

    def __init__(
        self,
        receiver_unique_id: str,
        subunit: SubunitBase,
        description: YncaSwitchEntityDescription,
        associated_zone: ZoneBase | None = None,
    ):
        super().__init__(receiver_unique_id, subunit, description, associated_zone)
        self._dirmode_get_sent = datetime.fromtimestamp(0)

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

    def update_callback(self, function, value):
        super().update_callback(function, value)
        
        # DIRMODE does not (always?) report changes
        # but it does report STRAIGHT when DIRMODE changes, even when STRAIGHT did not change
        # So manually request an update for DIRMODE when STRAIGHT is reported
        if self.entity_description.key == "dirmode" and function == "STRAIGHT":

            # But because STRAIGHT also gets reported on GET we need to avoid an infinite loop
            if self._dirmode_get_sent and (datetime.now() - self._dirmode_get_sent < timedelta(seconds=0.5)):
                return

            # There is no API in `ynca` to explicitly do a GET
            # So use internal knowledge for now and ignore the typing issue
            self._associated_zone._connection.get(self._associated_zone.id, "DIRMODE") # type: ignore[union-attr]
            self._dirmode_get_sent = datetime.now()
