from __future__ import annotations

from unittest.mock import ANY, Mock, call, patch

import pytest
import ynca

import custom_components.yamaha_ynca as yamaha_ynca
from custom_components.yamaha_ynca.select import (
    YamahaYncaSelect,
    YncaSelectEntityDescription,
    async_setup_entry,
    build_enum_options_list,
)
from homeassistant.helpers.entity import EntityCategory

from tests.conftest import setup_integration


TEST_ENTITY_DESCRIPTION = YncaSelectEntityDescription(  # type: ignore
    key="hdmiout",
    entity_category=EntityCategory.CONFIG,
    enum=ynca.HdmiOut,
    icon="mdi:hdmi-port",
    name="HDMI Out",
    options=build_enum_options_list(ynca.HdmiOut),
)


@patch("custom_components.yamaha_ynca.select.YamahaYncaSelect", autospec=True)
async def test_async_setup_entry(
    yamahayncaselect_mock, hass, mock_ynca, mock_zone_main
):
    mock_ynca.main = mock_zone_main
    mock_ynca.main.hdmiout = ynca.HdmiOut.OFF
    mock_ynca.main.sleep = ynca.Sleep.THIRTY_MIN

    integration = await setup_integration(hass, mock_ynca)
    add_entities_mock = Mock()

    await async_setup_entry(hass, integration.entry, add_entities_mock)

    yamahayncaselect_mock.assert_has_calls(
        [
            # TODO: improve checks to see if expected entity descriptions are used
            #       but just want to check for key, not the whole (internal) configuration
            call("entry_id", mock_ynca.main, ANY),
            call("entry_id", mock_ynca.main, ANY),
        ]
    )

    add_entities_mock.assert_called_once()
    entities = add_entities_mock.call_args.args[0]
    assert len(entities) == 2


async def test_select_entity_fields(mock_zone):

    entity = YamahaYncaSelect("ReceiverUniqueId", mock_zone, TEST_ENTITY_DESCRIPTION)

    assert entity.name == "HDMI Out"
    assert entity.unique_id == "ReceiverUniqueId_ZoneId_hdmiout"
    assert entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId_ZoneId")
    }

    # Setting value
    entity.select_option("off")
    assert mock_zone.hdmiout is ynca.HdmiOut.OFF
    entity.select_option("out1_2")
    assert mock_zone.hdmiout is ynca.HdmiOut.OUT1_PLUS_2

    # Reading state
    mock_zone.hdmiout = ynca.HdmiOut.OUT1
    assert entity.current_option == "out1"
    mock_zone.hdmiout = ynca.HdmiOut.OUT2
    assert entity.current_option == "out2"
