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


@pytest.fixture
def mock_zone():
    """Create a mocked Zone instance."""
    zone = Mock(
        spec=ynca.subunits.zone.ZoneBase,
    )

    zone.id = "ZoneId"
    zone.zonename = None

    return zone


TEST_ENTITY_DESCRIPTION = YncaSwitchEntityDescription(
    key="enhancer",
    entity_category=EntityCategory.CONFIG,
    name="Enhancer",
    on=ynca.OnOff.ON,
    off=ynca.OnOff.OFF,
)


@patch("custom_components.yamaha_ynca.switch.YamahaYncaSwitch", autospec=True)
async def test_async_setup_entry(
    yamahayncaswitch_mock,
    hass,
    mock_ynca,
):

    mock_ynca.main = Mock(spec=ynca.subunits.zone.Main)
    mock_ynca.main.enhancer = ynca.OnOff.OFF

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

    assert entity.name == "ZoneId: Enhancer"
    assert entity.unique_id == "ReceiverUniqueId_ZoneId_enhancer"

    # Setting value
    entity.turn_on()
    assert mock_zone.enhancer is ynca.OnOff.ON
    entity.turn_off()
    assert mock_zone.enhancer is ynca.OnOff.OFF

    # Reading state
    mock_zone.enhancer = ynca.OnOff.ON
    assert entity.is_on == True
    mock_zone.enhancer = ynca.OnOff.OFF
    assert entity.is_on == False
