from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

from homeassistant.helpers.entity import EntityCategory
import pytest

from custom_components import yamaha_ynca
from custom_components.yamaha_ynca.sensor import (
    ENTITY_DESCRIPTIONS,
    YamahaYncaSensor,
    YncaSensorEntityDescription,
    async_setup_entry,
)
from tests.conftest import setup_integration
import ynca

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import (  # type: ignore[import]
        MockConfigEntry,
    )

    from ynca.subunits.zone import ZoneBase


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
async def test_sensor_supported(
    hass: HomeAssistant,
    mock_ynca: Mock,
    mock_zone_main: Mock,
) -> None:
    mock_ynca.main = mock_zone_main
    mock_ynca.main.inp = ynca.Input.HDMI1

    await setup_integration(hass, mock_ynca)

    source = hass.states.get("sensor.modelname_main_source")
    assert source is not None
    assert source.state == "HDMI1"

    mock_ynca.main.inp = ynca.Input.AUDIO1
    # Multiple callbacks are registered, call them all to simulate an update
    for c in range(mock_zone_main.register_update_callback.call_count):
        callback = mock_zone_main.register_update_callback.call_args_list[c].args[0]
        callback("INP", "AUDIO1")
    await hass.async_block_till_done()
    source = hass.states.get("sensor.modelname_main_source")
    assert source.state == "AUDIO1"
