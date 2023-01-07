from __future__ import annotations

from unittest.mock import ANY, Mock, call, patch

import pytest
import ynca

import custom_components.yamaha_ynca as yamaha_ynca
from custom_components.yamaha_ynca.switch import (
    YamahaYncaSwitch,
    YncaSwitchEntityDescription,
    async_setup_entry,
)
from homeassistant.helpers.entity import EntityCategory

from tests.conftest import setup_integration


TEST_ENTITY_DESCRIPTION = YncaSwitchEntityDescription(
    key="enhancer",
    entity_category=EntityCategory.CONFIG,
    name="Name",
    on=ynca.Enhancer.ON,
    off=ynca.Enhancer.OFF,
)


@patch("custom_components.yamaha_ynca.switch.YamahaYncaSwitch", autospec=True)
async def test_async_setup_entry(
    yamahayncaswitch_mock, hass, mock_ynca, mock_zone_main
):
    mock_ynca.main = mock_zone_main
    mock_ynca.main.adaptivedrc = ynca.AdaptiveDrc.OFF
    mock_ynca.main.enhancer = ynca.Enhancer.OFF
    mock_ynca.main.threedcinema = ynca.ThreeDeeCinema.AUTO

    integration = await setup_integration(hass, mock_ynca)
    add_entities_mock = Mock()

    await async_setup_entry(hass, integration.entry, add_entities_mock)

    yamahayncaswitch_mock.assert_has_calls(
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


async def test_switch_entity_fields(mock_zone):

    entity = YamahaYncaSwitch("ReceiverUniqueId", mock_zone, TEST_ENTITY_DESCRIPTION)

    assert entity.name == "Name"
    assert entity.unique_id == "ReceiverUniqueId_ZoneId_enhancer"

    # Setting value
    entity.turn_on()
    assert mock_zone.enhancer is ynca.Enhancer.ON
    entity.turn_off()
    assert mock_zone.enhancer is ynca.Enhancer.OFF

    # Reading state
    mock_zone.enhancer = ynca.Enhancer.ON
    assert entity.is_on == True
    mock_zone.enhancer = ynca.Enhancer.OFF
    assert entity.is_on == False
