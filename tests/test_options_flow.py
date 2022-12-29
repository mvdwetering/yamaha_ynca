"""Test the Yamaha (YNCA) config flow."""
from unittest.mock import Mock, create_autospec, patch

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

import custom_components.yamaha_ynca as yamaha_ynca
import ynca

from .conftest import setup_integration


async def test_options_flow_ok(hass: HomeAssistant, mock_ynca) -> None:

    mock_ynca.main = Mock(spec=ynca.subunits.zone.Main)
    mock_ynca.zone2 = Mock(spec=ynca.subunits.zone.Zone2)
    mock_ynca.zone3 = Mock(spec=ynca.subunits.zone.Zone3)
    mock_ynca.sys.inpnamehdmi4 = "_INPNAMEHDMI4_"
    mock_ynca.netradio = create_autospec(ynca.subunits.netradio.NetRadio)

    integration = await setup_integration(hass, mock_ynca, modelname="RX-A810")
    options = dict(integration.entry.options)
    options[yamaha_ynca.const.CONF_HIDDEN_SOUND_MODES] = [
        "Obsolete",  # Test that obsolete values don't break the schema
    ]
    integration.entry.options = options

    result = await hass.config_entries.options.async_init(integration.entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "main"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            yamaha_ynca.const.CONF_HIDDEN_INPUTS_FOR_ZONE("MAIN"): ["HDMI4"],
            yamaha_ynca.const.CONF_HIDDEN_INPUTS_FOR_ZONE("ZONE2"): ["NET RADIO"],
            yamaha_ynca.const.CONF_HIDDEN_SOUND_MODES: [
                "Hall in Vienna",
            ],
        },
    )

    assert result["type"] == "create_entry"
    assert result["data"] == {
        yamaha_ynca.const.CONF_HIDDEN_INPUTS_FOR_ZONE("MAIN"): ["HDMI4"],
        yamaha_ynca.const.CONF_HIDDEN_INPUTS_FOR_ZONE("ZONE2"): ["NET RADIO"],
        yamaha_ynca.const.CONF_HIDDEN_INPUTS_FOR_ZONE("ZONE3"): [],
        yamaha_ynca.const.CONF_HIDDEN_SOUND_MODES: ["Hall in Vienna"],
    }


async def test_options_flow_no_connection(hass: HomeAssistant, mock_ynca) -> None:
    """Test optionsflow when there is no connection"""

    integration = await setup_integration(hass, mock_ynca, modelname="RX-A810")
    hass.data[yamaha_ynca.DOMAIN] = None  # Pretend connection failed

    result = await hass.config_entries.options.async_init(integration.entry.entry_id)

    assert result["type"] == FlowResultType.ABORT
