"""Test the Yamaha (YNCA) config flow migration."""

from unittest.mock import patch
import custom_components.yamaha_ynca as yamaha_ynca
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_registry,
)


async def test_async_migration_entry_version_1(hass: HomeAssistant):
    """Test a successful setup entry."""

    entry_v1 = MockConfigEntry(
        domain=yamaha_ynca.DOMAIN,
        entry_id="entry_id",
        title="ModelName",
        data={"serial_port": "SerialPort"},
        version=1,
    )
    entry_v1.add_to_hass(hass)

    mock_entity_registry = mock_registry(hass)
    mock_button_entity_entry = mock_entity_registry.async_get_or_create(
        Platform.BUTTON,
        yamaha_ynca.DOMAIN,
        "button.scene_button",
        config_entry=entry_v1,
        device_id="device_id",
    )
    mock_scene_entity_entry = mock_entity_registry.async_get_or_create(
        Platform.SCENE,
        yamaha_ynca.DOMAIN,
        "scene.scene_button",
        config_entry=entry_v1,
        device_id="device_id",
    )
    assert len(mock_entity_registry.entities) == 2  # Make sure entities were added

    # Migrate
    with patch(
        "homeassistant.helpers.entity_registry.async_get",
        return_value=mock_entity_registry,
    ):
        migration_success = await yamaha_ynca.async_migrate_entry(hass, entry_v1)
    await hass.async_block_till_done()

    assert migration_success

    # Serial_port renamed to serial_url
    entry_v3 = hass.config_entries.async_get_entry(entry_v1.entry_id)
    assert entry_v3.version == 3
    assert entry_v3.title == entry_v1.title
    assert entry_v3.data["serial_url"] == "SerialPort"

    # Button and Scene entities removed
    assert len(mock_entity_registry.entities) == 0


async def test_async_migration_entry_version_2(hass: HomeAssistant):
    """Test a successful setup entry."""

    entry_v2 = MockConfigEntry(
        domain=yamaha_ynca.DOMAIN,
        entry_id="entry_id",
        title="ModelName",
        data={"serial_url": "SerialUrl"},
        version=2,
    )
    entry_v2.add_to_hass(hass)

    mock_entity_registry = mock_registry(hass)
    mock_scene_entity_entry = mock_entity_registry.async_get_or_create(
        Platform.SCENE,
        yamaha_ynca.DOMAIN,
        "scene.scene_button",
        config_entry=entry_v2,
        device_id="device_id",
    )
    assert len(mock_entity_registry.entities) == 1  # Make sure entities were added

    # Migrate
    with patch(
        "homeassistant.helpers.entity_registry.async_get",
        return_value=mock_entity_registry,
    ):
        migration_success = await yamaha_ynca.async_migrate_entry(hass, entry_v2)
    await hass.async_block_till_done()

    assert migration_success

    # Serial_port renamed to serial_url
    entry_v3 = hass.config_entries.async_get_entry(entry_v2.entry_id)
    assert entry_v3.version == 3
    assert entry_v3.title == entry_v2.title
    assert entry_v3.data["serial_url"] == "SerialUrl"

    # Scene entities removed
    assert len(mock_entity_registry.entities) == 0