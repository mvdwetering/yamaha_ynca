from __future__ import annotations

from homeassistant.core import HomeAssistant

from custom_components.yamaha_ynca.diagnostics import async_get_config_entry_diagnostics
from tests.conftest import setup_integration


async def test_diagnostics(hass: HomeAssistant, mock_ynca):
    integration = await setup_integration(hass, mock_ynca)
    integration.mock_ynca.get_communication_log_items.return_value = ["testdata"]

    diagnostics = await async_get_config_entry_diagnostics(hass, integration.entry)

    assert "config_entry" in diagnostics

    assert "sys" in diagnostics
    assert diagnostics["sys"]["modelname"] == "ModelName"
    assert diagnostics["sys"]["version"] == "Version"

    assert "communication" in diagnostics
    assert "initialization" in diagnostics["communication"]
    assert "history" in diagnostics["communication"]
    assert diagnostics["communication"]["history"] == ["testdata"]
