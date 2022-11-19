from unittest.mock import Mock

import custom_components.yamaha_ynca as yamaha_ynca
import pytest
import ynca
from custom_components.yamaha_ynca.button import YamahaYncaSceneButton


@pytest.fixture
def mock_zone():
    """Create a mocked Zone instance."""
    zone = Mock(
        spec=ynca.subunits.zone.ZoneBase,
    )

    zone.id = "ZoneId"
    zone.zonename = "ZoneName"
    zone.scene1name = "SceneName One"

    return zone


async def test_button_entity(mock_zone):

    entity = YamahaYncaSceneButton("ReceiverUniqueId", mock_zone, "1")

    assert entity.unique_id == "ReceiverUniqueId_ZoneId_scene_1"
    assert entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId")
    }
    assert entity.name == "ZoneName: SceneName One"

    entity.press()
    mock_zone.scene_recall.assert_called_once_with("1")

    await entity.async_added_to_hass()
    mock_zone.register_update_callback.assert_called_once()

    await entity.async_will_remove_from_hass()
    mock_zone.unregister_update_callback.assert_called_once_with(
        mock_zone.register_update_callback.call_args.args[0]
    )
