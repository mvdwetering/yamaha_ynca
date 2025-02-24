from __future__ import annotations

from unittest.mock import Mock, call, patch

from custom_components import yamaha_ynca
from custom_components.yamaha_ynca.button import (
    YamahaYncaSceneButton,
    async_setup_entry,
)

from .conftest import setup_integration


@patch("custom_components.yamaha_ynca.button.YamahaYncaSceneButton", autospec=True)
async def test_async_setup_entry_autodetect_number_of_scenes(
    yamahayncascenebutton_mock, hass, mock_ynca, mock_zone_main, mock_zone_zone2
):
    mock_ynca.main = mock_zone_main
    mock_ynca.main.zonename = "_MAIN_"
    mock_ynca.main.scene1name = "SCENE_1"
    mock_ynca.main.scene2name = "SCENE_2"

    mock_ynca.zone2 = mock_zone_zone2
    mock_ynca.zone2.zonename = "_ZONE2_"
    mock_ynca.zone2.scene1name = "SCENE_1"

    integration = await setup_integration(hass, mock_ynca)
    add_entities_mock = Mock()

    await async_setup_entry(hass, integration.entry, add_entities_mock)

    yamahayncascenebutton_mock.assert_has_calls(
        [
            call("entry_id", mock_ynca.main, 1),
            call("entry_id", mock_ynca.main, 2),
            call("entry_id", mock_ynca.zone2, 1),
        ]
    )

    add_entities_mock.assert_called_once()
    entities = add_entities_mock.call_args.args[0]
    assert len(entities) == 3


@patch("custom_components.yamaha_ynca.button.YamahaYncaSceneButton", autospec=True)
async def test_async_setup_entry_configured_number_of_scenes(
    yamahayncascenebutton_mock, hass, mock_ynca, mock_zone_zone2
):
    mock_ynca.zone2 = mock_zone_zone2
    mock_ynca.zone2.zonename = "_ZONE2_"

    integration = await setup_integration(hass, mock_ynca)
    options = dict(integration.entry.options)
    options["ZONE2"] = {yamaha_ynca.const.CONF_NUMBER_OF_SCENES: 11}
    hass.config_entries.async_update_entry(integration.entry, options=options)

    add_entities_mock = Mock()
    await async_setup_entry(hass, integration.entry, add_entities_mock)

    yamahayncascenebutton_mock.assert_has_calls(
        [
            call("entry_id", mock_ynca.zone2, 1),
            call("entry_id", mock_ynca.zone2, 2),
            call("entry_id", mock_ynca.zone2, 3),
            call("entry_id", mock_ynca.zone2, 4),
            call("entry_id", mock_ynca.zone2, 5),
            call("entry_id", mock_ynca.zone2, 6),
            call("entry_id", mock_ynca.zone2, 7),
            call("entry_id", mock_ynca.zone2, 8),
            call("entry_id", mock_ynca.zone2, 9),
            call("entry_id", mock_ynca.zone2, 10),
            call("entry_id", mock_ynca.zone2, 11),
        ]
    )

    add_entities_mock.assert_called_once()
    entities = add_entities_mock.call_args.args[0]
    assert len(entities) == 11


async def test_button_entity_with_names(mock_zone):
    mock_zone.zonename = "ZoneName"
    mock_zone.scene1name = "SceneName One"

    entity = YamahaYncaSceneButton("ReceiverUniqueId", mock_zone, "1")

    assert entity.unique_id == "ReceiverUniqueId_ZoneId_scene_1"
    assert entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId_ZoneId")
    }
    assert entity.name == "SceneName One"


async def test_button_entity_no_names(mock_zone):
    entity = YamahaYncaSceneButton("ReceiverUniqueId", mock_zone, "1")

    assert entity.unique_id == "ReceiverUniqueId_ZoneId_scene_1"
    assert entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId_ZoneId")
    }
    assert entity.name == "Scene 1"


async def test_button_entity_behavior(mock_zone):
    entity = YamahaYncaSceneButton("ReceiverUniqueId", mock_zone, "1")

    # Pressing button sends message
    entity.press()
    mock_zone.scene.assert_called_once_with("1")

    # Check handling of updates from YNCA
    await entity.async_added_to_hass()
    mock_zone.register_update_callback.assert_called_once()
    callback = mock_zone.register_update_callback.call_args.args[0]
    entity.schedule_update_ha_state = Mock()

    # Ignore unrelated updates
    callback("SCENE11NAME", None)
    entity.schedule_update_ha_state.assert_not_called()

    # HA state is updated when related YNCA messages are handled
    callback("SCENE1NAME", None)
    entity.schedule_update_ha_state.assert_called_once()

    # Cleanup on exit
    await entity.async_will_remove_from_hass()
    mock_zone.unregister_update_callback.assert_called_once_with(callback)
