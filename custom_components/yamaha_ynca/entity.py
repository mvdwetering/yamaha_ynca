"""Base entities for the Yamaha (YNCA) integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.helpers.entity import DeviceInfo, EntityDescription

from custom_components.yamaha_ynca.const import DOMAIN
import ynca

if TYPE_CHECKING:  # pragma: no cover
    from ynca.subunit import SubunitBase
    from ynca.subunits.zone import ZoneBase


class YamahaYncaSettingEntity:
    """Common code for YamahaYnca settings entities.

    Entities derived from this also need to derive from the standard HA entities.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        receiver_unique_id: str,
        subunit: SubunitBase,
        description: EntityDescription,
        associated_zone: ZoneBase | None = None,
    ) -> None:
        self.entity_description = description
        self._subunit = subunit

        if associated_zone is None:
            if TYPE_CHECKING:  # pragma: no cover
                assert isinstance(subunit, ZoneBase)
            associated_zone = subunit
        self._associated_zone = associated_zone

        function_names = getattr(self.entity_description, "function_names", None)
        self._relevant_updates = ["PWR"]
        self._relevant_updates.extend(
            function_names or [self.entity_description.key.upper()]
        )

        self._receiver_unique_id_subunit_id = f"{receiver_unique_id}_{self._subunit.id}"

        # Need to provide type annotations since in MRO for subclasses this class is before the
        # HA entity that actually defines the _attr_* methods
        self._attr_device_info: DeviceInfo | None = DeviceInfo(
            identifiers={(DOMAIN, f"{receiver_unique_id}_{self._associated_zone.id}")}
        )
        self._attr_translation_key: str | None = self.entity_description.key
        self._attr_unique_id: str | None = (
            f"{self._receiver_unique_id_subunit_id}_{self.entity_description.key}"
        )

    def update_callback(self, function: str, _value: Any) -> None:
        if function in self._relevant_updates:
            # schedule_update_ha_state is part of Entity, but typechecker does not know
            self.schedule_update_ha_state()  # type: ignore[attr-defined]

    async def async_added_to_hass(self) -> None:
        self._subunit.register_update_callback(self.update_callback)

    async def async_will_remove_from_hass(self) -> None:
        self._subunit.unregister_update_callback(self.update_callback)

    @property
    def available(self) -> bool:
        return self._associated_zone.pwr is ynca.Pwr.ON
