"""Test the Yamaha (YNCA) config flow."""
from __future__ import annotations

from unittest.mock import Mock, create_autospec, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry
import ynca

import custom_components.yamaha_ynca as yamaha_ynca
from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers.service import ServiceCall
from homeassistant.setup import async_setup_component

from .conftest import setup_integration


async def test_async_setup_entry(
    hass,
    device_reg,
    mock_ynca,
    mock_zone_main,
    mock_zone_zone2,
    mock_zone_zone3,
    mock_zone_zone4,
):
    """Test a successful setup entry."""
    mock_ynca.main = mock_zone_main
    mock_ynca.zone2 = mock_zone_zone2
    mock_ynca.zone3 = mock_zone_zone3
    mock_ynca.zone4 = mock_zone_zone4

    integration = await setup_integration(hass, mock_ynca)

    assert len(hass.config_entries.async_entries(yamaha_ynca.DOMAIN)) == 1
    assert integration.entry.state is ConfigEntryState.LOADED

    assert len(mock_ynca.initialize.mock_calls) == 1
    assert (
        mock_ynca is hass.data.get(yamaha_ynca.DOMAIN)[integration.entry.entry_id].api
    )

    assert len(device_reg.devices.keys()) == 4

    for zone_id in ["MAIN", "ZONE2", "ZONE3", "ZONE4"]:
        device = device_reg.async_get_device(
            identifiers={
                (yamaha_ynca.DOMAIN, f"{integration.entry.entry_id}_{zone_id}")
            }
        )
        assert device.manufacturer == "Yamaha"
        assert device.model == "ModelName"
        assert device.sw_version == "Version"
        assert device.name == f"ModelName {zone_id}"
        assert device.configuration_url is None


async def test_async_setup_entry_socket_has_configuration_url(
    hass, device_reg, mock_ynca, mock_zone_main
):
    """Test a successful setup entry."""
    mock_ynca.main = mock_zone_main

    integration = await setup_integration(
        hass, mock_ynca, serial_url="socket://1.2.3.4:4321"
    )

    device = device_reg.async_get_device(
        identifiers={(yamaha_ynca.DOMAIN, f"{integration.entry.entry_id}_MAIN")}
    )
    assert device.configuration_url == "http://1.2.3.4"


async def test_async_setup_entry_fails_with_connection_error(hass, mock_ynca):
    """Test a successful setup entry."""
    integration = await setup_integration(hass, mock_ynca, skip_setup=True)

    mock_ynca.initialize.side_effect = ynca.YncaConnectionError("Connection error")

    with patch("ynca.YncaApi", return_value=mock_ynca):
        await hass.config_entries.async_setup(integration.entry.entry_id)
        await hass.async_block_till_done()

    assert integration.entry.state is ConfigEntryState.SETUP_RETRY
    assert not hass.data.get(yamaha_ynca.DOMAIN)

    # Unload to avoid errors about "Lingering timer" which was started to retry setup
    await hass.config_entries.async_unload(integration.entry.entry_id)


async def test_async_setup_entry_fails_with_connection_failed(hass, mock_ynca):
    """Test a successful setup entry."""
    integration = await setup_integration(hass, mock_ynca, skip_setup=True)

    mock_ynca.initialize.side_effect = ynca.YncaConnectionFailed("Connection failed")

    with patch("ynca.YncaApi", return_value=mock_ynca):
        await hass.config_entries.async_setup(integration.entry.entry_id)
        await hass.async_block_till_done()

    assert integration.entry.state is ConfigEntryState.SETUP_RETRY
    assert not hass.data.get(yamaha_ynca.DOMAIN)

    # Unload to avoid errors about "Lingering timer" which was started to retry setup
    await hass.config_entries.async_unload(integration.entry.entry_id)


async def test_async_setup_entry_fails_with_initialization_failed_error(
    hass, mock_ynca
):
    """Test a successful setup entry."""
    integration = await setup_integration(hass, mock_ynca, skip_setup=True)

    mock_ynca.initialize.side_effect = ynca.YncaInitializationFailedException(
        "Initialize failed"
    )

    with patch("ynca.YncaApi", return_value=mock_ynca):
        await hass.config_entries.async_setup(integration.entry.entry_id)
        await hass.async_block_till_done()

    assert integration.entry.state is ConfigEntryState.SETUP_RETRY
    assert not hass.data.get(yamaha_ynca.DOMAIN)

    # Unload to avoid errors about "Lingering timer" which was started to retry setup
    await hass.config_entries.async_unload(integration.entry.entry_id)


async def test_async_setup_entry_fails_unknown_reason(hass, mock_ynca):
    """Test a successful setup entry."""
    integration = await setup_integration(hass, mock_ynca, skip_setup=True)

    mock_ynca.initialize.side_effect = Exception("Unexpected exception")

    with patch("ynca.YncaApi", return_value=mock_ynca):
        await hass.config_entries.async_setup(integration.entry.entry_id)
        await hass.async_block_till_done()

    assert integration.entry.state is ConfigEntryState.SETUP_ERROR
    assert not hass.data.get(yamaha_ynca.DOMAIN)


async def test_async_unload_entry(hass, mock_ynca, mock_zone_main):
    """Test successful unload of entry."""
    mock_ynca.main = mock_zone_main
    integration = await setup_integration(hass, mock_ynca)

    assert await hass.config_entries.async_unload(integration.entry.entry_id)
    await hass.async_block_till_done()

    mock_ynca.close.assert_called_once()
    assert integration.entry.state is ConfigEntryState.NOT_LOADED
    assert not hass.data.get(yamaha_ynca.DOMAIN)


@patch("homeassistant.config_entries.ConfigEntries.async_reload")
async def test_reload_on_disconnect(async_reload_mock, hass, mock_ynca, mock_zone_main):
    """Test successful unload of entry."""
    mock_ynca.main = mock_zone_main
    integration = await setup_integration(hass, mock_ynca)

    # on_disconnect gets called from a normal thread
    # also do that in the test otherwise it will hang
    await hass.async_add_executor_job(integration.on_disconnect)
    await hass.async_block_till_done()

    assert len(async_reload_mock.mock_calls) == 1


async def test_update_configentry(hass, mock_ynca, mock_zone_main, mock_zone_zone3):
    """Test successful unload of entry."""

    mock_ynca.main = mock_zone_main
    mock_ynca.zone3 = mock_zone_zone3

    entry = MockConfigEntry(
        version=7,
        domain=yamaha_ynca.DOMAIN,
        entry_id="entry_id",
        title="MODELNAME",
        data={
            yamaha_ynca.CONF_SERIAL_URL: "serial_url",
            yamaha_ynca.const.DATA_MODELNAME: "modelname",
            # no zones, will be added by function under test: yamaha_ynca.const.DATA_ZONES: zones,
        },
    )

    await yamaha_ynca.update_configentry(hass, entry, mock_ynca)

    assert "zones" in entry.data
    assert "MAIN" in entry.data["zones"]
    assert "ZONE2" not in entry.data["zones"]
    assert "ZONE3" in entry.data["zones"]
    assert "ZONE4" not in entry.data["zones"]


# Can't figure out how to patch `async_extract_config_entry_ids`
#
# @patch("homeassistant.helpers.service.async_extract_config_entry_ids")
# async def test_service_raw_ynca_command_handler(
#     async_extract_config_entry_ids_mock, hass, mock_ynca
# ):
#     """Test sending raw YNCA command."""
#     integration = await setup_integration(hass, mock_ynca)

#     call = ServiceCall(
#         yamaha_ynca.DOMAIN,
#         yamaha_ynca.SERVICE_SEND_RAW_YNCA,
#         {
#             "device_id": f"{integration.entry.entry_id}_MAIN",
#             "raw_data": "COMMAND_TO_SEND",
#             # "entity_id": "media_player.main",
#         },
#     )

#     async_extract_config_entry_ids_mock.return_value = {integration.entry.entry_id}
#     await yamaha_ynca.async_handle_send_raw_ynca(hass, call)
#     mock_ynca.send_raw.assert_called_once_with("COMMAND_TO_SEND")


@patch("custom_components.yamaha_ynca.async_handle_send_raw_ynca")
async def test_service_raw_ynca_command(
    async_handle_send_raw_ynca_mock, hass, mock_ynca, mock_zone_main
):
    """Test sending raw YNCA command."""
    mock_ynca.main = mock_zone_main
    integration = await setup_integration(hass, mock_ynca)

    # Service call is done, but odes not work due to no configentries found
    await hass.services.async_call(
        yamaha_ynca.DOMAIN,
        yamaha_ynca.SERVICE_SEND_RAW_YNCA,
        {
            "device_id": f"{integration.entry.entry_id}_MAIN",
            "raw_data": "COMMAND_TO_SEND",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    # Check
    async_handle_send_raw_ynca_mock.assert_called_once()
    assert len(async_handle_send_raw_ynca_mock.call_args.args) == 2

    assert async_handle_send_raw_ynca_mock.call_args.args[0] == hass

    service_call = async_handle_send_raw_ynca_mock.call_args.args[1]
    assert service_call.domain == yamaha_ynca.DOMAIN
    assert service_call.service == yamaha_ynca.SERVICE_SEND_RAW_YNCA
    assert service_call.data == {
        "device_id": f"{integration.entry.entry_id}_MAIN",
        "raw_data": "COMMAND_TO_SEND",
    }
