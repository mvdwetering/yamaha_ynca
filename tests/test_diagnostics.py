from homeassistant.core import HomeAssistant

from custom_components.yamaha_ynca.diagnostics import async_get_config_entry_diagnostics
from tests.conftest import setup_integration


async def test_diagnostics(hass: HomeAssistant):

    integration = await setup_integration(hass)
    integration.mock_ynca.get_communication_log_items.return_value = ["testdata"]

    diagnostics = await async_get_config_entry_diagnostics(hass, integration.entry)

    assert "config_entry" in diagnostics

    assert "SYS" in diagnostics
    assert diagnostics["SYS"]["modelname"] == "ModelName"
    assert diagnostics["SYS"]["version"] == "Version"

    assert "communication" in diagnostics
    assert "initialization" in diagnostics["communication"]
    assert "history" in diagnostics["communication"]
    assert diagnostics["communication"]["history"] == ["testdata"]
