from unittest.mock import Mock, call, patch

import custom_components.yamaha_ynca as yamaha_ynca
import pytest
import ynca
from custom_components.yamaha_ynca.button import (
    YamahaYncaSceneButton,
    async_setup_entry,
)
from tests.conftest import setup_integration


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


@patch("custom_components.yamaha_ynca.button.YamahaYncaSceneButton", autospec=True)
async def test_async_setup_entry(
    yamahayncascenebutton_mock,
    hass,
    mock_ynca,
):

    mock_ynca.main = Mock(spec=ynca.subunits.zone.Main)
    mock_ynca.zone2 = Mock(spec=ynca.subunits.zone.Zone2)

    for scene_id in range(1, 12 + 1):
        setattr(mock_ynca.main, f"scene{scene_id}name", None)
        setattr(mock_ynca.zone2, f"scene{scene_id}name", None)

    mock_ynca.main.zonename = "_MAIN_"
    mock_ynca.main.scene1name = "SCENE_1"
    mock_ynca.main.scene4name = "SCENE_4"
    mock_ynca.zone2.zonename = "_ZONE2_"
    mock_ynca.zone2.scene12name = "SCENE_12"

    integration = await setup_integration(hass, mock_ynca, modelname="RX-A810")
    add_entities_mock = Mock()

    await async_setup_entry(hass, integration.entry, add_entities_mock)

    yamahayncascenebutton_mock.assert_has_calls(
        [
            call("entry_id", mock_ynca.main, 1),
            call("entry_id", mock_ynca.main, 4),
            call("entry_id", mock_ynca.zone2, 12),
        ]
    )

    add_entities_mock.assert_called_once()
    entities = add_entities_mock.call_args.args[0]
    assert len(entities) == 3


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

    callback = mock_zone.register_update_callback.call_args.args[0]
    entity.schedule_update_ha_state = Mock()

    callback("SCENE11NAME", None)
    entity.schedule_update_ha_state.assert_not_called()

    callback("ZONENAME", None)
    assert entity.schedule_update_ha_state.call_count == 1
    callback("SCENE1NAME", None)
    assert entity.schedule_update_ha_state.call_count == 2

    await entity.async_will_remove_from_hass()
    mock_zone.unregister_update_callback.assert_called_once_with(callback)
