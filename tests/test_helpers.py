from __future__ import annotations
from unittest.mock import Mock

from homeassistant.helpers.entity import EntityDescription
import pytest
import ynca
from custom_components.yamaha_ynca.helpers import YamahaYncaSettingEntityMixin, scale


def test_scale(hass):
    assert scale(1, [1, 10], [2, 11]) == 2


@pytest.fixture
def mock_zone():
    """Create a mocked Zone instance."""
    zone = Mock(
        spec=ynca.subunits.zone.ZoneBase,
    )

    zone.id = "ZoneId"
    zone.zonename = None

    return zone


TEST_ENTITY_DESCRIPTION = EntityDescription(
    key="function_name",
    name="EntityName",
)


async def test_yamaha_ynca_settings_entity_behavior(mock_zone):

    entity = YamahaYncaSettingEntityMixin(
        "ReceiverUniqueId", mock_zone, TEST_ENTITY_DESCRIPTION
    )

    # Check handling of updtes from YNCA
    await entity.async_added_to_hass()
    mock_zone.register_update_callback.assert_called_once()
    callback = mock_zone.register_update_callback.call_args.args[0]
    entity.schedule_update_ha_state = Mock()

    # Ignore unrelated updates
    callback("UNRELATED", None)
    entity.schedule_update_ha_state.assert_not_called()

    # HA state is updated when related YNCA messages are handled
    callback("FUNCTION_NAME", None)
    assert entity.schedule_update_ha_state.call_count == 1
    callback("PWR", None)
    assert entity.schedule_update_ha_state.call_count == 2

    # Entity is unavailable when zone is powered off
    mock_zone.pwr = ynca.Pwr.ON
    assert entity.available == True
    mock_zone.pwr = ynca.Pwr.STANDBY
    assert entity.available == False

    # Cleanup on exit
    await entity.async_will_remove_from_hass()
    mock_zone.unregister_update_callback.assert_called_once_with(callback)
