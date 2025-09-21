from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.entity import DeviceInfo

from .const import (
    CONF_NUMBER_OF_SCENES,
    DOMAIN,
    MAX_NUMBER_OF_SCENES,
    NUMBER_OF_SCENES_AUTODETECT,
    ZONE_ATTRIBUTE_NAMES,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    import ynca

    from . import YamahaYncaConfigEntry


async def async_setup_entry(
    _hass: HomeAssistant,
    config_entry: YamahaYncaConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    domain_entry_data = config_entry.runtime_data

    entities: list[ButtonEntity] = []

    for zone_attr_name in ZONE_ATTRIBUTE_NAMES:
        if zone_subunit := getattr(domain_entry_data.api, zone_attr_name):
            number_of_scenes = config_entry.options.get(zone_subunit.id, {}).get(
                CONF_NUMBER_OF_SCENES, NUMBER_OF_SCENES_AUTODETECT
            )
            if number_of_scenes == NUMBER_OF_SCENES_AUTODETECT:
                number_of_scenes = 0
                for scene_id in range(1, MAX_NUMBER_OF_SCENES + 1):
                    if getattr(zone_subunit, f"scene{scene_id}name"):
                        number_of_scenes += 1
            number_of_scenes = min(MAX_NUMBER_OF_SCENES, number_of_scenes)

            entities.extend(
                YamahaYncaSceneButton(config_entry.entry_id, zone_subunit, scene_id)
                for scene_id in range(1, number_of_scenes + 1)
            )

    async_add_entities(entities)


class YamahaYncaSceneButton(ButtonEntity):
    """Representation of a scene button on a Yamaha Ynca device."""

    _attr_has_entity_name = True

    def __init__(
        self, receiver_unique_id: str, zone: ynca.subunits.zone.ZoneBase, scene_id: int
    ) -> None:
        self._zone = zone
        self._scene_id = scene_id
        self._update_functioname = f"SCENE{scene_id}NAME"

        self._attr_unique_id = (
            f"{receiver_unique_id}_{self._zone.id}_scene_{self._scene_id}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{receiver_unique_id}_{self._zone.id}")}
        )

    def update_callback(self, function: str, _value: Any) -> None:
        if function == self._update_functioname:
            self.schedule_update_ha_state()

    async def async_added_to_hass(self) -> None:
        self._zone.register_update_callback(self.update_callback)

    async def async_will_remove_from_hass(self) -> None:
        self._zone.unregister_update_callback(self.update_callback)

    @property
    def name(self) -> str:
        return (
            getattr(self._zone, f"scene{self._scene_id}name")
            or f"Scene {self._scene_id}"
        )

    def press(self) -> None:
        self._zone.scene(self._scene_id)
