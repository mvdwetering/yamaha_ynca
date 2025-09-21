from __future__ import annotations

from unittest.mock import ANY, Mock, call, patch

from homeassistant.components.number import NumberDeviceClass
from homeassistant.const import SIGNAL_STRENGTH_DECIBELS
from homeassistant.helpers.entity import EntityCategory
import pytest

from custom_components import yamaha_ynca
from custom_components.yamaha_ynca.number import (
    InitialVolumeValueEntityDescription,
    YamahaYncaNumber,
    YamahaYncaNumberInitialVolume,
    YncaNumberEntityDescription,
    async_setup_entry,
)
from tests.conftest import setup_integration
import ynca


def native_max_value_fn(_associated_zone: ynca.subunits.zone.ZoneBase) -> float:
    return 5.5


TEST_ENTITY_DESCRIPTION = YncaNumberEntityDescription(
    key="spbass",
    entity_category=EntityCategory.CONFIG,
    native_min_value=-6,
    native_max_value=6,
    native_max_value_fn=native_max_value_fn,
    native_step=0.5,
    device_class=NumberDeviceClass.SIGNAL_STRENGTH,
    native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
    name="Name",
)


@patch("custom_components.yamaha_ynca.number.YamahaYncaNumber", autospec=True)
@patch(
    "custom_components.yamaha_ynca.number.YamahaYncaNumberInitialVolume", autospec=True
)
async def test_async_setup_entry(
    yamahayncanumberinitialvolume_mock,
    yamahayncanumber_mock,
    hass,
    mock_ynca,
    mock_zone_main,
):
    mock_ynca.main = mock_zone_main
    mock_ynca.main.maxvol = 0
    mock_ynca.main.spbass = -1
    mock_ynca.main.sptreble = 1
    mock_ynca.main.hpbass = 2
    mock_ynca.main.hptreble = 3
    mock_ynca.main.initvollvl = 1.0

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
    yamahayncanumberinitialvolume_mock.assert_has_calls(
        [
            # TODO: improve checks to see if expected entity descriptions are used
            #       but just want to check for key, not the whole (internal) configuration
            call("entry_id", mock_ynca.main, ANY),
        ]
    )

    add_entities_mock.assert_called_once()
    entities = add_entities_mock.call_args.args[0]
    assert len(entities) == 6


async def test_number_entity(hass, mock_ynca, mock_zone_main):
    entity_under_test = "number.modelname_main_max_volume"

    mock_zone_main.maxvol = 0
    mock_zone_main.pwr = ynca.Pwr.ON
    mock_ynca.main = mock_zone_main
    await setup_integration(hass, mock_ynca)

    # Initial value
    max_volume = hass.states.get(entity_under_test)
    assert max_volume is not None
    assert max_volume.state == "0"

    # Set value
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": entity_under_test, "value": 10},
        blocking=True,
    )
    assert mock_zone_main.maxvol == 10


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_number_entity_volume(hass, mock_ynca, mock_zone_main):
    entity_under_test = "number.modelname_main_volume_db"

    mock_zone_main.vol = -5
    mock_zone_main.pwr = ynca.Pwr.ON
    mock_ynca.main = mock_zone_main
    await setup_integration(hass, mock_ynca)

    # Initial value
    volume = hass.states.get(entity_under_test)
    assert volume is not None
    assert volume.state == "-5"

    # Set value
    await hass.services.async_call(
        "number",
        "set_value",
        {"entity_id": entity_under_test, "value": 10},
        blocking=True,
    )
    assert mock_zone_main.vol == 10


async def test_number_entity_fields(mock_zone):
    entity = YamahaYncaNumber("ReceiverUniqueId", mock_zone, TEST_ENTITY_DESCRIPTION)

    assert entity.unique_id == "ReceiverUniqueId_ZoneId_spbass"
    assert entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId_ZoneId")
    }

    # Value from native_max_value_fn instead of static value
    assert entity.capability_attributes["max"] == 5.5

    # Setting value
    entity.set_native_value(-4.5)
    assert mock_zone.spbass == -4.5

    # Reading state
    mock_zone.spbass = 5
    assert entity.state == 5


async def test_initial_volume_number_entity(mock_zone):
    entity = YamahaYncaNumberInitialVolume(
        "ReceiverUniqueId", mock_zone, InitialVolumeValueEntityDescription
    )

    assert entity.unique_id == "ReceiverUniqueId_ZoneId_initvollvl"
    assert entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId_ZoneId")
    }

    mock_zone.pwr = ynca.Pwr.STANDBY
    assert not entity.available

    mock_zone.pwr = ynca.Pwr.ON

    # Receivers without INITVOLMODE
    mock_zone.initvolmode = None
    mock_zone.initvollvl = 1.0
    assert entity.available

    mock_zone.initvollvl = ynca.InitVolLvl.MUTE
    assert not entity.available
    mock_zone.initvollvl = ynca.InitVolLvl.OFF
    assert not entity.available

    # Receivers with INITVOLMODE
    mock_zone.initvolmode = ynca.InitVolMode.ON
    mock_zone.initvollvl = 1.0
    assert entity.available

    mock_zone.initvolmode = ynca.InitVolMode.OFF
    mock_zone.initvollvl = 1.0
    assert not entity.available

    mock_zone.initvolmode = ynca.InitVolMode.ON
    mock_zone.initvollvl = ynca.InitVolLvl.MUTE
    assert not entity.available
