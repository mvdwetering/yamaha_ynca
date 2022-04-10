"""Test the Yamaha (YNCA) config flow migration."""

import custom_components.yamaha_ynca as yamaha_ynca
from custom_components.yamaha_ynca.const import DOMAIN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


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

    migration_success = await yamaha_ynca.async_migrate_entry(hass, entry_v1)
    await hass.async_block_till_done()

    assert migration_success

    entry_v2 = hass.config_entries.async_get_entry(entry_v1.entry_id)
    assert entry_v2.version == 2
    assert entry_v2.title == entry_v1.title
    assert entry_v2.data["serial_url"] == "SerialPort"
