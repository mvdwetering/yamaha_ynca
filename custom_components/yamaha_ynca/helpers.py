"""Helpers for the Yamaha (YNCA) integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List

import ynca

from custom_components.yamaha_ynca.const import DOMAIN
from homeassistant.helpers.entity import EntityDescription, DeviceInfo

if TYPE_CHECKING:  # pragma: no cover
    from ynca.subunits.zone import ZoneBase
    from ynca.subunit import SubunitBase


@dataclass
class DomainEntryData:
    api: ynca.YncaApi
    initialization_events: List[str]


def scale(input_value, input_range, output_range):
    input_min = input_range[0]
    input_max = input_range[1]
    input_spread = input_max - input_min

    output_min = output_range[0]
    output_max = output_range[1]
    output_spread = output_max - output_min

    value_scaled = float(input_value - input_min) / float(input_spread)

    return output_min + (value_scaled * output_spread)


def receiver_requires_audio_input_workaround(modelname) -> bool:
    # These models do not report the (single) AUDIO input properly
    # Reported for RX-V475, including RX-V575, HTR-4066, HTR-5066 because they share firmware
    # See https://github.com/mvdwetering/yamaha_ynca/issues/230
    # Also for RX-V473, including RX-V573, HTR-4065, HTR-5065 because they share firmware
    # See https://github.com/mvdwetering/yamaha_ynca/discussions/234
    return modelname in [
        "RX-V475",
        "RX-V575",
        "HTR-4066",
        "HTR-5066",
        "RX-V473",
        "RX-V573",
        "HTR-4065",
        "HTR-5065",
    ]

def subunit_supports_entitydescription_key(entity_description, subunit) -> bool:
    return getattr(
            subunit, entity_description.key, None
        ) is not None

class YamahaYncaSettingEntity:
    """
    Common code for YamahaYnca settings entities.
    Entities derived from this also need to derive from the standard HA entities.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        receiver_unique_id,
        subunit: SubunitBase,
        description: EntityDescription,
        associated_zone: ZoneBase | None = None,
    ):
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

    def update_callback(self, function, value):
        if function in self._relevant_updates:
            self.schedule_update_ha_state()  # type: ignore

    async def async_added_to_hass(self):
        self._subunit.register_update_callback(self.update_callback)

    async def async_will_remove_from_hass(self):
        self._subunit.unregister_update_callback(self.update_callback)

    @property
    def available(self):
        return self._associated_zone.pwr is ynca.Pwr.ON
