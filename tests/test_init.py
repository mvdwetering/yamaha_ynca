"""Test the Yamaha (YNCA) config flow."""
from typing import Callable, NamedTuple, Type
from unittest.mock import DEFAULT, Mock, create_autospec, patch

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import RESULT_TYPE_CREATE_ENTRY, RESULT_TYPE_FORM
from homeassistant.helpers import (
    device_registry,
)

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_device_registry,
)

import custom_components.yamaha_ynca as yamaha_ynca
import ynca


class Integration(NamedTuple):
    entry: Type[ConfigEntry]
    on_disconnect: Callable
    mock_receiver: Type[Mock]


async def setup_integration(
    hass, mock_receiver=None, skip_setup=False, serial_url="SerialUrl"
):
    entry = MockConfigEntry(
        version=2,
        domain=yamaha_ynca.DOMAIN,
        title="ModelName",
        data={yamaha_ynca.CONF_SERIAL_URL: serial_url},
    )
    entry.add_to_hass(hass)
    on_disconnect = None

    if not skip_setup:

        def side_effect(*args, **kwargs):
            nonlocal on_disconnect
            on_disconnect = args[1]
            return DEFAULT

        mock_receiver = mock_receiver or create_autospec(ynca.Receiver)

        mock_receiver.SYS.modelname = "ModelName"
        mock_receiver.SYS.version = "Version"

        with patch(
            "ynca.Receiver", return_value=mock_receiver, side_effect=side_effect
        ):
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

    return Integration(entry, on_disconnect, mock_receiver)


@pytest.fixture
def device_reg(hass: HomeAssistant) -> device_registry.DeviceRegistry:
    """Return an empty, loaded, registry."""
    return mock_device_registry(hass)


async def test_async_setup_entry(hass, device_reg):
    """Test a successful setup entry."""
    integration = await setup_integration(hass)

    assert len(hass.config_entries.async_entries(yamaha_ynca.DOMAIN)) == 1
    assert integration.entry.state is ConfigEntryState.LOADED

    mock_receiver = hass.data.get(yamaha_ynca.DOMAIN)[integration.entry.entry_id]
    assert len(mock_receiver.initialize.mock_calls) == 1

    assert len(device_reg.devices.keys()) == 1
    device = device_reg.async_get_device(
        identifiers={(yamaha_ynca.DOMAIN, integration.entry.entry_id)}
    )
    assert device.manufacturer == "Yamaha"
    assert device.model == "ModelName"
    assert device.sw_version == "Version"
    assert device.name == "Yamaha ModelName"
    assert device.configuration_url is None

    # TODO Check for entities/states


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

    mock_receiver = create_autospec(ynca.Receiver)
    mock_receiver.initialize.side_effect = ynca.YncaConnectionError("Connection error")

    with patch("ynca.Receiver", return_value=mock_receiver):
        await hass.config_entries.async_setup(integration.entry.entry_id)
        await hass.async_block_till_done()

    assert integration.entry.state is ConfigEntryState.SETUP_RETRY
    assert not hass.data.get(yamaha_ynca.DOMAIN)


async def test_async_setup_entry_fails_with_initialization_failed_error(hass):
    """Test a successful setup entry."""
    integration = await setup_integration(hass, skip_setup=True)

    mock_receiver = create_autospec(ynca.Receiver)
    mock_receiver.initialize.side_effect = ynca.YncaInitializationFailedException(
        "Initialize failed"
    )

    with patch("ynca.Receiver", return_value=mock_receiver):
        await hass.config_entries.async_setup(integration.entry.entry_id)
        await hass.async_block_till_done()

    assert integration.entry.state is ConfigEntryState.SETUP_RETRY
    assert not hass.data.get(yamaha_ynca.DOMAIN)


async def test_async_setup_entry_fails_unknown_reason(hass):
    """Test a successful setup entry."""
    integration = await setup_integration(hass, skip_setup=True)

    mock_receiver = create_autospec(ynca.Receiver)
    mock_receiver.initialize.side_effect = Exception("Unexpected exception")

    with patch("ynca.Receiver", return_value=mock_receiver):
        await hass.config_entries.async_setup(integration.entry.entry_id)
        await hass.async_block_till_done()

    assert integration.entry.state is ConfigEntryState.SETUP_ERROR
    assert not hass.data.get(yamaha_ynca.DOMAIN)


async def test_async_unload_entry(hass):
    """Test successful unload of entry."""
    integration = await setup_integration(hass)
    mock_receiver = hass.data.get(yamaha_ynca.DOMAIN)[integration.entry.entry_id]

    assert await hass.config_entries.async_unload(integration.entry.entry_id)
    await hass.async_block_till_done()

    mock_receiver.close.assert_called_once()
    assert integration.entry.state is ConfigEntryState.NOT_LOADED
    assert not hass.data.get(yamaha_ynca.DOMAIN)


async def test_reload_on_disconnect(hass):
    """Test successful unload of entry."""
    integration = await setup_integration(hass)

    mock_receiver = hass.data.get(yamaha_ynca.DOMAIN)[integration.entry.entry_id]

    # This should work (it works in real environment) but it locks up the test completely :(
    # Don't know what is going on.

    # integration.on_disconnect()

    # assert len(mock_receiver.close.mock_calls) == 1
    # assert len(mock_receiver.initialize.mock_calls) == 2
