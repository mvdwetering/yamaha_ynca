from __future__ import annotations

from unittest.mock import ANY, Mock, call, patch

import pytest
import ynca

import custom_components.yamaha_ynca as yamaha_ynca
from custom_components.yamaha_ynca.number import YamahaYncaNumber, async_setup_entry
from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS
from homeassistant.helpers.entity import EntityCategory

from tests.conftest import setup_integration


@pytest.fixture
def mock_zone():
    """Create a mocked Zone instance."""
    zone = Mock(
        spec=ynca.subunits.zone.ZoneBase,
    )

    zone.id = "ZoneId"

    return zone


TEST_ENTITY_DESCRIPTION = NumberEntityDescription(
    key="spbass",
    entity_category=EntityCategory.CONFIG,
    native_min_value=-6,
    native_max_value=6,
    native_step=0.5,
    device_class=NumberDeviceClass.SIGNAL_STRENGTH,
    native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
    name="Name",
)


@patch("custom_components.yamaha_ynca.number.YamahaYncaNumber", autospec=True)
async def test_async_setup_entry(
    yamahayncanumber_mock,
    hass,
    mock_ynca,
):

    mock_ynca.main = Mock(spec=ynca.subunits.zone.Main)
    mock_ynca.main.maxvol = 0
    mock_ynca.main.spbass = -1
    mock_ynca.main.sptreble = 1

    integration = await setup_integration(hass, mock_ynca)
    add_entities_mock = Mock()

    await async_setup_entry(hass, integration.entry, add_entities_mock)

    yamahayncanumber_mock.assert_has_calls(
        [
            # TODO: improve checks to see if expected entity descriptions are used
            #       but just want to check for key, not the whole (internal) configuration
            call("entry_id", mock_ynca.main, ANY),
            call("entry_id", mock_ynca.main, ANY),
            call("entry_id", mock_ynca.main, ANY),
        ]
    )

    add_entities_mock.assert_called_once()
    entities = add_entities_mock.call_args.args[0]
    assert len(entities) == 3


async def test_number_entity_fields(mock_zone):

    entity = YamahaYncaNumber("ReceiverUniqueId", mock_zone, TEST_ENTITY_DESCRIPTION)

    entity.name == "ZoneId: Name"
    entity.unique_id == "ReceiverUniqueId_ZoneId_number_spbass"

    # Setting value
    entity.set_native_value(-4.5)
    mock_zone.spbass == -4.5

    # Reading state
    mock_zone.spbass = 5
    entity.state == 5


async def test_number_entity_behavior(mock_zone):

    entity = YamahaYncaNumber("ReceiverUniqueId", mock_zone, TEST_ENTITY_DESCRIPTION)

    # Check handling of updtes from YNCA
    await entity.async_added_to_hass()
    mock_zone.register_update_callback.assert_called_once()
    callback = mock_zone.register_update_callback.call_args.args[0]
    entity.schedule_update_ha_state = Mock()

    # Ignore unrelated updates
    callback("SCENE11NAME", None)
    entity.schedule_update_ha_state.assert_not_called()

    # HA state is updated when related YNCA messages are handled
    callback("SPBASS", None)
    assert entity.schedule_update_ha_state.call_count == 1
    callback("PWR", None)
    assert entity.schedule_update_ha_state.call_count == 2

    # Entity is unavailable when zone is powered off
    mock_zone.pwr = ynca.Pwr.ON
    entity.available == True
    mock_zone.pwr = ynca.Pwr.STANDBY
    entity.available == False

    # Cleanup on exit
    await entity.async_will_remove_from_hass()
    mock_zone.unregister_update_callback.assert_called_once_with(callback)
