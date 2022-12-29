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


INPUT_SUBUNITS = [
    "airplay",
    "bt",
    "dab",
    "ipod",
    "ipodusb",
    "napster",
    "netradio",
    "pandora",
    "pc",
    "rhap",
    "server",
    "sirius",
    "siriusir",
    "siriusxm",
    "spotify",
    "tun",
    "uaw",
    "usb",
]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


@pytest.fixture
def mock_ynca(hass):
    """Create a mocked YNCA instance without any inputs or subunits."""
    mock_ynca = Mock(
        spec=ynca.YncaApi,
    )

    # No zones by default
    mock_ynca.main = None
    mock_ynca.zone2 = None
    mock_ynca.zone3 = None
    mock_ynca.zone4 = None

    # No input subunits
    for input_subunit in INPUT_SUBUNITS:
        setattr(mock_ynca, input_subunit, None)

    mock_sys = Mock(spec=ynca.subunits.system.System)
    mock_ynca.sys = mock_sys
    mock_ynca.sys.modelname = "Model name"

    # Clear external input names
    for attribute in dir(mock_sys):
        if attribute.startswith("inpname"):
            setattr(mock_sys, attribute, None)

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
        version=6,
        domain=yamaha_ynca.DOMAIN,
        entry_id="entry_id",
        title="ModelName",
        data={
            yamaha_ynca.CONF_SERIAL_URL: serial_url,
            yamaha_ynca.DATA_MODELNAME: "ModelName",
            yamaha_ynca.DATA_ZONES: ["MAIN", "ZONE2", "ZONE3"],
        },
    )
    entry.add_to_hass(hass)
    on_disconnect = None

    if not skip_setup:

        def side_effect(*args, **kwargs):
            nonlocal on_disconnect
            on_disconnect = args[1]
            return DEFAULT

        mock_ynca = mock_ynca or create_autospec(ynca.YncaApi)

        mock_ynca.sys.modelname = modelname
        mock_ynca.sys.version = "Version"

        with patch("ynca.YncaApi", return_value=mock_ynca, side_effect=side_effect):
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

    return Integration(entry, on_disconnect, mock_ynca)
