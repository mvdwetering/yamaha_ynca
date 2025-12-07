"""Test the Yamaha (YNCA) config flow."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import call

from homeassistant.exceptions import ServiceValidationError
import pytest

from custom_components import yamaha_ynca
from custom_components.yamaha_ynca.services import SERVICE_SEND_RAW_YNCA

from .conftest import setup_integration

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from ynca import YncaApi


async def test_service_raw_ynca(hass: HomeAssistant, mock_ynca: YncaApi) -> None:
    """Test sending raw YNCA command."""
    integration = await setup_integration(hass, mock_ynca)

    await hass.services.async_call(
        yamaha_ynca.DOMAIN,
        SERVICE_SEND_RAW_YNCA,
        {
            "config_entry_id": integration.entry.entry_id,
            "raw_data": "# Ignore this\n@COMMAND:TO_SEND=1\nMore stuff to ignore\n@COMMAND:TO_SEND=2",
        },
        blocking=True,
    )
    await hass.async_block_till_done()

    mock_ynca.send_raw.assert_has_calls(
        [call("@COMMAND:TO_SEND=1"), call("@COMMAND:TO_SEND=2")]
    )


async def test_service_raw_ynca_invalid_config_entry_id(
    hass: HomeAssistant, mock_ynca: YncaApi
) -> None:
    """Test sending invalid config_entry_id."""
    await setup_integration(hass, mock_ynca)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            yamaha_ynca.DOMAIN,
            SERVICE_SEND_RAW_YNCA,
            {
                "config_entry_id": "does_not_exist",
                "raw_data": "@COMMAND:TO_SEND=1",
            },
            blocking=True,
        )

    await hass.async_block_till_done()
