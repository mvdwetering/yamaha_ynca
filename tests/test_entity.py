from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import Mock

from homeassistant.helpers.entity import EntityDescription

from custom_components.yamaha_ynca.entity import YamahaYncaSettingEntity
import ynca

TEST_ENTITY_DESCRIPTION = EntityDescription(
    key="key",
    name="EntityName",
)


@dataclass(frozen=True, kw_only=True)
class TestYncaEntityDescription(EntityDescription):
    __test__ = False  # This avoids pytest thinking it is a test
    function_names: list[str] | None = None


TEST_ENTITY_DESCRIPTION_WITH_FUNCTION_NAME = TestYncaEntityDescription(
    key="key",
    name="EntityName",
    function_names=["FUNCTION_NAME"],
)


async def test_yamaha_ynca_settings_entity_update(mock_zone, mock_zone_zone3) -> None:
    entity = YamahaYncaSettingEntity(
        "ReceiverUniqueId", mock_zone, TEST_ENTITY_DESCRIPTION
    )

    entity2 = YamahaYncaSettingEntity(
        "ReceiverUniqueId",
        mock_zone,
        TEST_ENTITY_DESCRIPTION_WITH_FUNCTION_NAME,
        mock_zone_zone3,
    )

    # Setup entities to handle updates
    await entity.async_added_to_hass()
    assert mock_zone.register_update_callback.call_count == 1
    callback = mock_zone.register_update_callback.call_args.args[0]

    await entity2.async_added_to_hass()
    assert mock_zone.register_update_callback.call_count == 2
    callback2 = mock_zone.register_update_callback.call_args.args[0]

    entity.schedule_update_ha_state = Mock()
    entity2.schedule_update_ha_state = Mock()

    # Ignore unrelated updates
    callback("UNRELATED", None)
    callback2("UNRELATED", None)
    entity.schedule_update_ha_state.assert_not_called()
    entity2.schedule_update_ha_state.assert_not_called()

    # HA state is updated when related YNCA messages are handled
    callback("KEY", None)
    callback2("KEY", None)
    assert entity.schedule_update_ha_state.call_count == 1
    assert entity2.schedule_update_ha_state.call_count == 0

    callback("FUNCTION_NAME", None)
    callback2("FUNCTION_NAME", None)
    assert entity.schedule_update_ha_state.call_count == 1
    assert entity2.schedule_update_ha_state.call_count == 1

    # All react on PWR
    callback("PWR", None)
    callback2("PWR", None)
    assert entity.schedule_update_ha_state.call_count == 2
    assert entity2.schedule_update_ha_state.call_count == 2

    # Entity is unavailable when zone is powered off
    mock_zone.pwr = ynca.Pwr.ON
    mock_zone_zone3.pwr = ynca.Pwr.ON
    assert entity.available is True
    assert entity2.available is True
    mock_zone.pwr = ynca.Pwr.STANDBY
    assert entity.available is False
    assert entity2.available is True
    # Entity 2 has associated zone, so availability depends on that power
    mock_zone.pwr = ynca.Pwr.ON
    mock_zone_zone3.pwr = ynca.Pwr.STANDBY
    assert entity.available is True
    assert entity2.available is False

    # Cleanup on exit
    await entity.async_will_remove_from_hass()
    mock_zone.unregister_update_callback.assert_called_with(callback)
    await entity2.async_will_remove_from_hass()
    mock_zone.unregister_update_callback.assert_called_with(callback2)
