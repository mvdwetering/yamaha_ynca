"""Test the Yamaha (YNCA) config flow."""
from typing import Callable, NamedTuple, Type
from unittest.mock import DEFAULT, patch

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.data_entry_flow import RESULT_TYPE_CREATE_ENTRY, RESULT_TYPE_FORM
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.yamaha_ynca as yamaha_ynca
import ynca

from .mock_receiver import MockReceiver


class Integration(NamedTuple):
    entry: Type[ConfigEntry]
    on_disconnect: Callable


async def setup_integration(hass, skip_setup=False):
    entry = MockConfigEntry(
        domain=yamaha_ynca.DOMAIN,
        title="ModelName",
        data={yamaha_ynca.CONF_SERIAL_URL: "SerialUrl"},
    )
    entry.add_to_hass(hass)
    on_disconnect = None

    if not skip_setup:

        def side_effect(*args, **kwargs):
            nonlocal on_disconnect
            on_disconnect = args[1]
            return DEFAULT

        with patch("ynca.Receiver", new_callable=MockReceiver, side_effect=side_effect):
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

    return Integration(entry, on_disconnect)


async def test_async_setup_entry(hass):
    """Test a successful setup entry."""
    integration = await setup_integration(hass)

    assert len(hass.config_entries.async_entries(yamaha_ynca.DOMAIN)) == 1
    assert integration.entry.state is ConfigEntryState.LOADED

    mock_receiver = hass.data.get(yamaha_ynca.DOMAIN)[integration.entry.entry_id]
    assert len(mock_receiver.initialize.mock_calls) == 1

    # TODO Check for entities/states


async def test_async_setup_entry_fails_with_connection_error(hass):
    """Test a successful setup entry."""
    integration = await setup_integration(hass, skip_setup=True)

    mock_receiver = MockReceiver()
    mock_receiver.initialize.side_effect = ynca.YncaConnectionError("Connection error")

    with patch("ynca.Receiver", return_value=mock_receiver):
        await hass.config_entries.async_setup(integration.entry.entry_id)
        await hass.async_block_till_done()

    assert integration.entry.state is ConfigEntryState.SETUP_RETRY
    assert not hass.data.get(yamaha_ynca.DOMAIN)


async def test_async_setup_entry_fails_with_initialization_failed_error(hass):
    """Test a successful setup entry."""
    integration = await setup_integration(hass, skip_setup=True)

    mock_receiver = MockReceiver()
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

    mock_receiver = MockReceiver()
    mock_receiver.initialize.side_effect = Exception("Unexpected exception")

    with patch("ynca.Receiver", return_value=mock_receiver):
        await hass.config_entries.async_setup(integration.entry.entry_id)
        await hass.async_block_till_done()

    assert integration.entry.state is ConfigEntryState.SETUP_ERROR
    assert not hass.data.get(yamaha_ynca.DOMAIN)


async def test_async_unload_entry(hass):
    """Test successful unload of entry."""
    integration = await setup_integration(hass)

    assert await hass.config_entries.async_unload(integration.entry.entry_id)
    await hass.async_block_till_done()

    assert integration.entry.state is ConfigEntryState.NOT_LOADED
    assert not hass.data.get(yamaha_ynca.DOMAIN)


async def test_reload_on_disconnect(hass):
    """Test successful unload of entry."""
    integration = await setup_integration(hass)

    mock_receiver = hass.data.get(yamaha_ynca.DOMAIN)[integration.entry.entry_id]

    # integration.on_disconnect()

    # assert len(mock_receiver.close.mock_calls) == 1
    # assert len(mock_receiver.initialize.mock_calls) == 2
