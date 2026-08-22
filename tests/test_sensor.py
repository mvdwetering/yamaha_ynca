from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

from homeassistant.helpers.entity import EntityCategory
import pytest

from custom_components.yamaha_ynca.sensor import (
    ENTITY_DESCRIPTIONS,
    YncaSensorEntityDescription,
    async_setup_entry,
)
from tests.conftest import setup_integration
import ynca

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.core import HomeAssistant

    from ynca import ZoneBase


TEST_ENTITY_DESCRIPTION = YncaSensorEntityDescription(
    key="hdmiout",
    entity_category=EntityCategory.CONFIG,
    icon="mdi:hdmi-port",
    name="HDMI Out",
)


def get_entity_description_by_key(key: str) -> YncaSensorEntityDescription:
    return next(e for e in ENTITY_DESCRIPTIONS if e.key == key)


async def test_async_setup_entry(
    hass: HomeAssistant,
    mock_ynca: ynca.YncaApi,
    mock_zone_main: ZoneBase,
    mock_zone_zone2: ZoneBase,
) -> None:
    mock_ynca.main = mock_zone_main
    mock_ynca.main.inp = ynca.Input.HDMI1

    mock_ynca.zone2 = mock_zone_zone2
    mock_ynca.zone2.inp = ynca.Input.AUDIO1

    integration = await setup_integration(hass, mock_ynca)
    add_entities_mock = Mock()

    await async_setup_entry(hass, integration.entry, add_entities_mock)

    add_entities_mock.assert_called_once()
    entities = add_entities_mock.call_args.args[0]
    assert len(entities) == 1  # Only once because Zone 2 does not support it


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_source_sensor(
    hass: HomeAssistant,
    mock_ynca: Mock,
    mock_zone_main: Mock,
) -> None:
    mock_ynca.main = mock_zone_main
    mock_ynca.main.inp = ynca.Input.HDMI1

    options = {
        "MAIN": {
            "selected_inputs": [
                "HDMI1",
                "AUDIO1",
            ]
        }
    }
    await setup_integration(hass, mock_ynca, options=options)

    # Check if supported
    entity_state = hass.states.get("sensor.modelname_main_source")
    assert entity_state is not None
    assert entity_state.state == "HDMI1"

    # Options match inputs selected in config entry
    assert set(entity_state.attributes["options"]) == {"HDMI1", "AUDIO1"}

    # Change input to known value
    mock_ynca.main.inp = ynca.Input.AUDIO1
    for callback in mock_zone_main.register_update_callback.call_args_list:
        callback.args[0]("INP", "AUDIO1")
    await hass.async_block_till_done()

    entity_state = hass.states.get("sensor.modelname_main_source")
    assert entity_state.state == "AUDIO1"

    # Change input to one not in options list, should be unknown
    mock_ynca.main.inp = ynca.Input.AUDIO2
    for callback in mock_zone_main.register_update_callback.call_args_list:
        callback.args[0]("INP", "AUDIO2")
    await hass.async_block_till_done()

    entity_state = hass.states.get("sensor.modelname_main_source")
    assert entity_state.state == "unknown"
