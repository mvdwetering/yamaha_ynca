"""Test the Yamaha (YNCA) config flow migration."""

from unittest.mock import patch
import custom_components.yamaha_ynca as yamaha_ynca
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    mock_registry,
)

from custom_components.yamaha_ynca.const import CONF_HIDDEN_SOUND_MODES


async def test_async_migration_entry(hass: HomeAssistant):
    """Full chain of migrations should result in last version"""

    old_entry = MockConfigEntry(
        domain=yamaha_ynca.DOMAIN,
        entry_id="entry_id",
        title="ModelName",
        data={"serial_port": "SerialPort"},
        version=1,
    )
    old_entry.add_to_hass(hass)

    migration_success = await yamaha_ynca.async_migrate_entry(hass, old_entry)
    await hass.async_block_till_done()

    assert migration_success == True

    new_entry = hass.config_entries.async_get_entry(old_entry.entry_id)
    assert new_entry.version == 5


async def test_async_migration_entry_version_1(hass: HomeAssistant):

    old_entry = MockConfigEntry(
        domain=yamaha_ynca.DOMAIN,
        entry_id="entry_id",
        title="ModelName",
        data={"serial_port": "SerialPort"},
        version=1,
    )
    old_entry.add_to_hass(hass)

    mock_entity_registry = mock_registry(hass)
    mock_button_entity_entry = mock_entity_registry.async_get_or_create(
        Platform.BUTTON,
        yamaha_ynca.DOMAIN,
        "button.scene_button",
        config_entry=old_entry,
        device_id="device_id",
    )
    assert len(mock_entity_registry.entities) == 1  # Make sure entities were added

    # Migrate
    with patch(
        "homeassistant.helpers.entity_registry.async_get",
        return_value=mock_entity_registry,
    ):
        yamaha_ynca.migrate_v1(hass, old_entry)
    await hass.async_block_till_done()

    # Button entities removed
    assert len(mock_entity_registry.entities) == 0

    # Serial_port renamed to serial_url
    new_entry = hass.config_entries.async_get_entry(old_entry.entry_id)
    assert new_entry.version == 2
    assert new_entry.data["serial_url"] == "SerialPort"


async def test_async_migration_entry_version_2(hass: HomeAssistant):

    old_entry = MockConfigEntry(
        domain=yamaha_ynca.DOMAIN,
        entry_id="entry_id",
        title="ModelName",
        data={"serial_url": "SerialUrl"},
        version=2,
    )
    old_entry.add_to_hass(hass)

    mock_entity_registry = mock_registry(hass)
    mock_scene_entity_entry = mock_entity_registry.async_get_or_create(
        Platform.SCENE,
        yamaha_ynca.DOMAIN,
        "scene.scene_button",
        config_entry=old_entry,
        device_id="device_id",
    )
    assert len(mock_entity_registry.entities) == 1  # Make sure entities were added

    # Migrate
    with patch(
        "homeassistant.helpers.entity_registry.async_get",
        return_value=mock_entity_registry,
    ):
        yamaha_ynca.migrate_v2(hass, old_entry)
    await hass.async_block_till_done()

    # Scene entities removed
    assert len(mock_entity_registry.entities) == 0

    new_entry = hass.config_entries.async_get_entry(old_entry.entry_id)
    assert new_entry.version == 3


async def test_async_migration_entry_version_3_hidden_soundmodes(hass: HomeAssistant):

    old_entry = MockConfigEntry(
        domain=yamaha_ynca.DOMAIN,
        entry_id="entry_id",
        title="ModelName",
        data={"serial_url": "SerialUrl"},
        options={CONF_HIDDEN_SOUND_MODES: ["CHURCH_IN_ROYAUMONT", "UNSUPPORTED"]},
        version=3,
    )
    old_entry.add_to_hass(hass)

    # Migrate
    yamaha_ynca.migrate_v3(hass, old_entry)
    await hass.async_block_till_done()

    # Hidden soundmodes are translated from enum name to value
    new_entry = hass.config_entries.async_get_entry(old_entry.entry_id)
    assert new_entry.version == 4
    assert new_entry.options[CONF_HIDDEN_SOUND_MODES] == ["Church in Royaumont"]


async def test_async_migration_entry_version_3_no_hidden_soundmodes(
    hass: HomeAssistant,
):

    old_entry = MockConfigEntry(
        domain=yamaha_ynca.DOMAIN,
        entry_id="entry_id",
        title="ModelName",
        data={"serial_url": "SerialUrl"},
        version=3,
    )
    old_entry.add_to_hass(hass)

    # Migrate
    yamaha_ynca.migrate_v3(hass, old_entry)
    await hass.async_block_till_done()

    # Hidden soundmodes are translated from enum name to value
    new_entry = hass.config_entries.async_get_entry(old_entry.entry_id)
    assert new_entry.version == 4
    assert new_entry.options.get(CONF_HIDDEN_SOUND_MODES, None) is None


async def test_async_migration_entry_version_4_is_ipaddress(hass: HomeAssistant):

    old_entry = MockConfigEntry(
        domain=yamaha_ynca.DOMAIN,
        entry_id="entry_id",
        title="ModelName",
        data={"serial_url": "1.2.3.4"},
        version=4,
    )
    old_entry.add_to_hass(hass)

    yamaha_ynca.migrate_v4(hass, old_entry)
    await hass.async_block_till_done()

    # IP address converted to socket:// url
    new_entry = hass.config_entries.async_get_entry(old_entry.entry_id)
    assert new_entry.version == 5
    assert new_entry.data["serial_url"] == "socket://1.2.3.4:50000"


async def test_async_migration_entry_version_4_is_ipaddress_and_port(
    hass: HomeAssistant,
):

    old_entry = MockConfigEntry(
        domain=yamaha_ynca.DOMAIN,
        entry_id="entry_id",
        title="ModelName",
        data={"serial_url": "1.2.3.4:56789"},
        version=4,
    )
    old_entry.add_to_hass(hass)

    yamaha_ynca.migrate_v4(hass, old_entry)
    await hass.async_block_till_done()

    # IP address converted to socket:// url
    new_entry = hass.config_entries.async_get_entry(old_entry.entry_id)
    assert new_entry.version == 5
    assert new_entry.data["serial_url"] == "socket://1.2.3.4:56789"


async def test_async_migration_entry_version_4_is_not_ipaddress(
    hass: HomeAssistant,
):

    old_entry = MockConfigEntry(
        domain=yamaha_ynca.DOMAIN,
        entry_id="entry_id",
        title="ModelName",
        data={"serial_url": "not an ip address"},
        version=4,
    )
    old_entry.add_to_hass(hass)

    yamaha_ynca.migrate_v4(hass, old_entry)
    await hass.async_block_till_done()

    # IP address converted to socket:// url
    new_entry = hass.config_entries.async_get_entry(old_entry.entry_id)
    assert new_entry.version == 5
    assert new_entry.data["serial_url"] == "not an ip address"
