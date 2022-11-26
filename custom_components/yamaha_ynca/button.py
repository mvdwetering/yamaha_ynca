from typing import Any

from homeassistant.components.button import ButtonEntity

from .const import DOMAIN, ZONE_SUBUNITS
from .helpers import DomainEntryData


async def async_setup_entry(hass, config_entry, async_add_entities):

    domain_entry_data: DomainEntryData = hass.data[DOMAIN][config_entry.entry_id]

    entities = []
    for zone_attr_name in ZONE_SUBUNITS:
        if zone_subunit := getattr(domain_entry_data.api, zone_attr_name):
            for scene_id in range(1, 12 + 1):
                if getattr(zone_subunit, f"scene{scene_id}name"):
                    entities.append(
                        YamahaYncaSceneButton(
                            config_entry.entry_id, zone_subunit, scene_id
                        )
                    )

    async_add_entities(entities)


class YamahaYncaSceneButton(ButtonEntity):
    """Representation of a scene button on a Yamaha Ynca device."""

    _attr_has_entity_name = True

    def __init__(self, receiver_unique_id, zone, scene_id):
        self._zone = zone
        self._scene_id = scene_id

        self._attr_unique_id = (
            f"{receiver_unique_id}_{self._zone.id}_scene_{self._scene_id}"
        )
        self._attr_device_info = {
            "identifiers": {(DOMAIN, receiver_unique_id)},
        }

    def update_callback(self, function, value):
        if function in ["ZONENAME", f"SCENE{self._scene_id}NAME"]:
            self.schedule_update_ha_state()

    async def async_added_to_hass(self):
        self._zone.register_update_callback(self.update_callback)

    async def async_will_remove_from_hass(self):
        self._zone.unregister_update_callback(self.update_callback)

    @property
    def name(self):
        return f"{self._zone.zonename}: {getattr(self._zone, f'scene{self._scene_id}name', f'Scene {self._scene_id}')}"

    def press(self) -> None:
        self._zone.scene(self._scene_id)
