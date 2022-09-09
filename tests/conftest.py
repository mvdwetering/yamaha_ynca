"""Fixtures for testing."""
from typing import Callable, NamedTuple, Type
from unittest.mock import DEFAULT, Mock, create_autospec, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_device_registry,
)


import custom_components.yamaha_ynca as yamaha_ynca
import ynca


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def mock_ynca(hass):
    """Create a mocked YNCA instance."""
    mock_ynca = Mock(
        spec=ynca.Ynca,
    )

    return mock_ynca


@pytest.fixture
def device_reg(hass: HomeAssistant) -> device_registry.DeviceRegistry:
    """Return an empty, loaded, registry."""
    return mock_device_registry(hass)


class Integration(NamedTuple):
    entry: Type[ConfigEntry]
    on_disconnect: Callable
    mock_ynca: Type[Mock]


async def setup_integration(
    hass,
    mock_ynca=None,
    skip_setup=False,
    serial_url="SerialUrl",
    modelname="ModelName",
):
    entry = MockConfigEntry(
        version=3,
        domain=yamaha_ynca.DOMAIN,
        entry_id="entry_id",
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

        mock_ynca = mock_ynca or create_autospec(ynca.Ynca)

        mock_ynca.SYS.modelname = modelname
        mock_ynca.SYS.version = "Version"

        with patch("ynca.Ynca", return_value=mock_ynca, side_effect=side_effect):
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

    return Integration(entry, on_disconnect, mock_ynca)
