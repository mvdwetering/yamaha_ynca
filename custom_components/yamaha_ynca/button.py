from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import YamahaYncaConfigEntry
from .const import (
    CONF_NUMBER_OF_SCENES,
    DOMAIN,
    MAX_NUMBER_OF_SCENES,
    NUMBER_OF_SCENES_AUTODETECT,
    ZONE_ATTRIBUTE_NAMES,
)


async def async_setup_entry(hass: HomeAssistant, config_entry: YamahaYncaConfigEntry, async_add_entities: AddEntitiesCallback):
    domain_entry_data = config_entry.runtime_data
    entities = []
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
            for scene_id in range(1, number_of_scenes + 1):
                entities.append(
                    YamahaYncaSceneButton(config_entry.entry_id, zone_subunit, scene_id)
                )

    async_add_entities(entities)


class YamahaYncaSceneButton(ButtonEntity):
    """Representation of a scene button on a Yamaha Ynca device."""

    _attr_has_entity_name = True

    def __init__(self, receiver_unique_id, zone, scene_id):
        self._zone = zone
        self._scene_id = scene_id
        self._update_functioname = f"SCENE{scene_id}NAME"

        self._attr_unique_id = (
            f"{receiver_unique_id}_{self._zone.id}_scene_{self._scene_id}"
        )
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{receiver_unique_id}_{self._zone.id}")}
        )

    def update_callback(self, function, value):
        if function == self._update_functioname:
            self.schedule_update_ha_state()

    async def async_added_to_hass(self):
        self._zone.register_update_callback(self.update_callback)

    async def async_will_remove_from_hass(self):
        self._zone.unregister_update_callback(self.update_callback)

    @property
    def name(self):
        return (
            getattr(self._zone, f"scene{self._scene_id}name")
            or f"Scene {self._scene_id}"
        )

    def press(self) -> None:
        self._zone.scene(self._scene_id)
