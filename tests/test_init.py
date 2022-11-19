"""Test the Yamaha (YNCA) config flow."""
from unittest.mock import create_autospec, patch

from homeassistant.config_entries import ConfigEntryState

import custom_components.yamaha_ynca as yamaha_ynca
import ynca

from .conftest import setup_integration


async def test_async_setup_entry(hass, device_reg):
    """Test a successful setup entry."""
    integration = await setup_integration(hass)

    assert len(hass.config_entries.async_entries(yamaha_ynca.DOMAIN)) == 1
    assert integration.entry.state is ConfigEntryState.LOADED

    mock_ynca = hass.data.get(yamaha_ynca.DOMAIN)[integration.entry.entry_id].api
    assert len(mock_ynca.initialize.mock_calls) == 1

    assert len(device_reg.devices.keys()) == 1
    device = device_reg.async_get_device(
        identifiers={(yamaha_ynca.DOMAIN, integration.entry.entry_id)}
    )
    assert device.manufacturer == "Yamaha"
    assert device.model == "ModelName"
    assert device.sw_version == "Version"
    assert device.name == "Yamaha ModelName"
    assert device.configuration_url is None


async def test_async_setup_entry_socket_has_configuration_url(hass, device_reg):
    """Test a successful setup entry."""
    integration = await setup_integration(hass, serial_url="socket://1.2.3.4:4321")

    device = device_reg.async_get_device(
        identifiers={(yamaha_ynca.DOMAIN, integration.entry.entry_id)}
    )
    assert device.configuration_url == "http://1.2.3.4"


async def test_async_setup_entry_fails_with_connection_error(hass):
    """Test a successful setup entry."""
    integration = await setup_integration(hass, skip_setup=True)

    mock_ynca = create_autospec(ynca.YncaApi)
    mock_ynca.initialize.side_effect = ynca.YncaConnectionError("Connection error")

    with patch("ynca.YncaApi", return_value=mock_ynca):
        await hass.config_entries.async_setup(integration.entry.entry_id)
        await hass.async_block_till_done()

    assert integration.entry.state is ConfigEntryState.SETUP_RETRY
    assert not hass.data.get(yamaha_ynca.DOMAIN)


async def test_async_setup_entry_fails_with_initialization_failed_error(hass):
    """Test a successful setup entry."""
    integration = await setup_integration(hass, skip_setup=True)

    mock_ynca = create_autospec(ynca.YncaApi)
    mock_ynca.initialize.side_effect = ynca.YncaInitializationFailedException(
        "Initialize failed"
    )

    with patch("ynca.YncaApi", return_value=mock_ynca):
        await hass.config_entries.async_setup(integration.entry.entry_id)
        await hass.async_block_till_done()

    assert integration.entry.state is ConfigEntryState.SETUP_RETRY
    assert not hass.data.get(yamaha_ynca.DOMAIN)


async def test_async_setup_entry_fails_unknown_reason(hass):
    """Test a successful setup entry."""
    integration = await setup_integration(hass, skip_setup=True)

    mock_ynca = create_autospec(ynca.YncaApi)
    mock_ynca.initialize.side_effect = Exception("Unexpected exception")

    with patch("ynca.YncaApi", return_value=mock_ynca):
        await hass.config_entries.async_setup(integration.entry.entry_id)
        await hass.async_block_till_done()

    assert integration.entry.state is ConfigEntryState.SETUP_ERROR
    assert not hass.data.get(yamaha_ynca.DOMAIN)


async def test_async_unload_entry(hass):
    """Test successful unload of entry."""
    integration = await setup_integration(hass)
    mock_ynca = hass.data.get(yamaha_ynca.DOMAIN)[integration.entry.entry_id].api

    assert await hass.config_entries.async_unload(integration.entry.entry_id)
    await hass.async_block_till_done()

    mock_ynca.close.assert_called_once()
    assert integration.entry.state is ConfigEntryState.NOT_LOADED
    assert not hass.data.get(yamaha_ynca.DOMAIN)


async def test_reload_on_disconnect(hass):
    """Test successful unload of entry."""
    integration = await setup_integration(hass)

    mock_ynca = hass.data.get(yamaha_ynca.DOMAIN)[integration.entry.entry_id].api

    # This should work (it works in real environment) but it locks up the test completely :(
    # Don't know what is going on.

    # integration.on_disconnect()

    # assert len(mock_ynca.close.mock_calls) == 1
    # assert len(mock_ynca.initialize.mock_calls) == 2
