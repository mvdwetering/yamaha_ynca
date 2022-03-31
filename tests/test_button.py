"""Test the Yamaha (YNCA) config flow."""
from unittest.mock import Mock

import custom_components.yamaha_ynca as yamaha_ynca
import pytest
import ynca
from custom_components.yamaha_ynca.button import YamahaYncaSceneButton


@pytest.fixture
def mock_zone():
    """Create a mocked Zone instance."""
    zone = Mock(
        spec=ynca.ZoneBase,
    )

    zone.id = "ZoneId"
    zone.name = "ZoneName"
    zone.scenes = {"1234": "SceneName 1234"}

    return zone


async def test_button_entity(mock_zone):

    entity = YamahaYncaSceneButton("ReceiverUniqueId", mock_zone, "1234")

    assert entity.unique_id == "ReceiverUniqueId_ZoneId_scene_1234"
    assert entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId")
    }
    assert entity.name == "ZoneName: SceneName 1234"

    entity.press()
    mock_zone.activate_scene.assert_called_once_with("1234")

    await entity.async_added_to_hass()
    mock_zone.register_update_callback.assert_called_once_with(
        entity.schedule_update_ha_state
    )

    await entity.async_will_remove_from_hass()
    mock_zone.unregister_update_callback.assert_called_once_with(
        mock_zone.register_update_callback.call_args.args[0]
    )
