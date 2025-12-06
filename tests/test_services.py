"""Test the Yamaha (YNCA) config flow."""

from __future__ import annotations

from unittest.mock import call, patch

from homeassistant.helpers.service import ServiceCall

from custom_components import yamaha_ynca
from custom_components.yamaha_ynca.services import SERVICE_SEND_RAW_YNCA

from .conftest import setup_integration


async def test_service_raw_ynca_command_handler(hass, mock_ynca) -> None:
    """Test sending raw YNCA command."""
    integration = await setup_integration(hass, mock_ynca)

    service_call = ServiceCall(
        hass,
        yamaha_ynca.DOMAIN,
        SERVICE_SEND_RAW_YNCA,
        {
            "config_entry_id": integration.entry.entry_id,
            "raw_data": "# Ignore this\n@COMMAND:TO_SEND=1\nMore stuff to ignore\n@COMMAND:TO_SEND=2",
        },
    )

    await yamaha_ynca.services.async_handle_send_raw_ynca(hass, service_call)
    mock_ynca.send_raw.assert_has_calls(
        [call("@COMMAND:TO_SEND=1"), call("@COMMAND:TO_SEND=2")]
    )


@patch("custom_components.yamaha_ynca.services.async_handle_send_raw_ynca")
async def test_service_raw_ynca_command(
    async_handle_send_raw_ynca_mock, hass, mock_ynca, mock_zone_main
) -> None:
    """Test sending raw YNCA command."""
    mock_ynca.main = mock_zone_main
    integration = await setup_integration(hass, mock_ynca)

    # Service call is done, but does not work due to no configentries found
    await hass.services.async_call(
        yamaha_ynca.DOMAIN,
        SERVICE_SEND_RAW_YNCA,
        {
            "config_entry_id": integration.entry.entry_id,
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
    assert service_call.service == SERVICE_SEND_RAW_YNCA
    assert service_call.data == {
        "config_entry_id": integration.entry.entry_id,
        "raw_data": "COMMAND_TO_SEND",
    }
