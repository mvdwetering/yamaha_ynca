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
    yamahayncanumber_mock, hass, mock_ynca, mock_zone_main
):
    mock_ynca.main = mock_zone_main
    mock_ynca.main.maxvol = 0
    mock_ynca.main.spbass = -1
    mock_ynca.main.sptreble = 1
    mock_ynca.main.hpbass = None
    mock_ynca.main.hptreble = None

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

    assert entity.name == "Name"
    assert entity.unique_id == "ReceiverUniqueId_ZoneId_spbass"
    assert entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId_ZoneId")
    }

    # Setting value
    entity.set_native_value(-4.5)
    assert mock_zone.spbass == -4.5

    # Reading state
    mock_zone.spbass = 5
    assert entity.state == 5
