"""Test the Yamaha (YNCA) config flow."""
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

import custom_components.yamaha_ynca as yamaha_ynca
import ynca

from .conftest import setup_integration


async def test_menu_form(hass: HomeAssistant) -> None:
    """Test we get the menu form when initialized by user."""

    result = await hass.config_entries.flow.async_init(
        yamaha_ynca.DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.MENU


async def test_network_connect(hass: HomeAssistant) -> None:

    result = await hass.config_entries.flow.async_init(
        yamaha_ynca.DOMAIN, context={"source": "network"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "ynca.YncaApi.connection_check",
        return_value=ynca.YncaConnectionCheckResult("ModelName", ["ZONE3"]),
    ) as mock_setup, patch(
        "custom_components.yamaha_ynca.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                yamaha_ynca.const.CONF_HOST: "hostname_or_ipaddress",
                yamaha_ynca.const.CONF_PORT: 12345,
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "ModelName"
    assert result2["data"] == {
        yamaha_ynca.CONF_SERIAL_URL: "socket://hostname_or_ipaddress:12345",
        yamaha_ynca.DATA_ZONES: ["ZONE3"],
        yamaha_ynca.DATA_MODELNAME: "ModelName",
    }
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_advanced_connect(hass: HomeAssistant) -> None:

    result = await hass.config_entries.flow.async_init(
        yamaha_ynca.DOMAIN, context={"source": "advanced"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"] is None

    with patch(
        "ynca.YncaApi.connection_check",
        return_value=ynca.YncaConnectionCheckResult("ModelName", ["ZONE2"]),
    ) as mock_setup, patch(
        "custom_components.yamaha_ynca.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                yamaha_ynca.CONF_SERIAL_URL: "SerialUrl",
            },
        )
        await hass.async_block_till_done()

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["title"] == "ModelName"
    assert result2["data"] == {
        yamaha_ynca.CONF_SERIAL_URL: "SerialUrl",
        yamaha_ynca.DATA_ZONES: ["ZONE2"],
        yamaha_ynca.DATA_MODELNAME: "ModelName",
    }
    assert len(mock_setup.mock_calls) == 1
    assert len(mock_setup_entry.mock_calls) == 1


async def test_connection_error(hass: HomeAssistant) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        yamaha_ynca.DOMAIN, context={"source": "serial"}
    )

    with patch(
        "ynca.YncaApi.connection_check",
        side_effect=ynca.YncaConnectionError("Connection error"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                yamaha_ynca.CONF_SERIAL_URL: "SerialUrl",
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "connection_error"}


async def test_connection_failed(hass: HomeAssistant) -> None:
    """Test we handle cannot connect error."""
    result = await hass.config_entries.flow.async_init(
        yamaha_ynca.DOMAIN, context={"source": "serial"}
    )

    with patch(
        "ynca.YncaApi.connection_check",
        side_effect=ynca.YncaConnectionFailed("Connection failed"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                yamaha_ynca.CONF_SERIAL_URL: "SerialUrl",
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "connection_failed_serial"}


async def test_unhandled_exception(hass: HomeAssistant) -> None:
    """Test we handle random exceptions."""
    result = await hass.config_entries.flow.async_init(
        yamaha_ynca.DOMAIN, context={"source": "serial"}
    )

    with patch(
        "ynca.YncaApi.connection_check",
        side_effect=Exception("Unhandled exception"),
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                yamaha_ynca.CONF_SERIAL_URL: "SerialUrl",
            },
        )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"] == {"base": "unknown"}
