"""The Yamaha (YNCA) integration."""

from __future__ import annotations

import asyncio
import re
from typing import List

import ynca

from homeassistant.config_entries import ConfigEntry, OperationNotAllowed
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, device_registry
from homeassistant.helpers.service import ServiceCall, async_extract_config_entry_ids
from homeassistant.helpers.typing import ConfigType

from .const import (
    COMMUNICATION_LOG_SIZE,
    CONF_SERIAL_URL,
    DATA_ZONES,
    DOMAIN,
    LOGGER,
    MANUFACTURER_NAME,
    SERVICE_SEND_RAW_YNCA,
    ZONE_ATTRIBUTE_NAMES,
)
from .helpers import DomainEntryData, receiver_requires_audio_input_workaround
from .migrations import async_migrate_entry as migrations_async_migrate_entry

PLATFORMS: List[Platform] = [
    Platform.MEDIA_PLAYER,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.REMOTE,
]


async def update_device_registry(
    hass: HomeAssistant, config_entry: ConfigEntry, receiver: ynca.YncaApi
):
    assert receiver.sys is not None

    # Configuration URL for devices connected through IP
    configuration_url = None
    if matches := re.match(
        r"socket:\/\/(.+):\d+",  # Extract IP or hostname
        config_entry.data[CONF_SERIAL_URL],
    ):
        configuration_url = f"http://{matches[1]}"

    # Add device explicitly to registry so other entities just have to report the identifier to link up
    registry = device_registry.async_get(hass)

    for zone_attr_name in ZONE_ATTRIBUTE_NAMES:
        if zone_subunit := getattr(receiver, zone_attr_name):
            devicename = build_zone_devicename(receiver, zone_subunit)
            registry.async_get_or_create(
                config_entry_id=config_entry.entry_id,
                identifiers={(DOMAIN, f"{config_entry.entry_id}_{zone_subunit.id}")},
                manufacturer=MANUFACTURER_NAME,
                name=devicename,
                model=receiver.sys.modelname,
                sw_version=receiver.sys.version,
                configuration_url=configuration_url,
            )

    if receiver.main and receiver.main.zonebavail is ynca.ZoneBAvail.READY:
        devicename = build_zoneb_devicename(receiver)
        registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            identifiers={(DOMAIN, f"{config_entry.entry_id}_ZONEB")},
            manufacturer=MANUFACTURER_NAME,
            name=devicename,
            model=receiver.sys.modelname,
            sw_version=receiver.sys.version,
            configuration_url=configuration_url,
        )

def build_zone_devicename(receiver, zone_subunit):
    devicename = f"{receiver.sys.modelname} {zone_subunit.id}"
    if (
        zone_subunit.zonename
        and zone_subunit.zonename.lower() != zone_subunit.id.lower()
    ):
        # Prefer user defined name over "MODEL ZONE" naming
        devicename = zone_subunit.zonename
    return devicename

def build_zoneb_devicename(receiver):
    devicename = f"{receiver.sys.modelname} ZoneB"
    if (
        receiver.main.zonebname
        and receiver.main.zonebname.lower() != "ZoneB".lower()
    ):
        # Prefer user defined name over "MODEL ZONE" naming
        devicename = receiver.main.zonebname
    return devicename


async def update_configentry(
    hass: HomeAssistant, config_entry: ConfigEntry, receiver: ynca.YncaApi
):
    assert receiver.sys is not None

    # Older configurations setup before 5.3.0+ will not have zones data filled
    # So fill it when not set already
    # If not set, options will not show for zones
    if DATA_ZONES not in config_entry.data:
        new_data = dict(config_entry.data)
        zones = []
        for zone_attr in ZONE_ATTRIBUTE_NAMES:
            if getattr(receiver, zone_attr, None):
                zones.append(zone_attr.upper())
        new_data[DATA_ZONES] = zones
        hass.config_entries.async_update_entry(config_entry, data=new_data)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    return await migrations_async_migrate_entry(hass, config_entry)


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    # Just reload the integration on update. Crude, but it works
    await hass.config_entries.async_reload(entry.entry_id)


async def async_handle_send_raw_ynca(hass: HomeAssistant, call: ServiceCall):
    for config_entry_id in await async_extract_config_entry_ids(hass, call):
        if config_entry := hass.config_entries.async_get_entry(config_entry_id):
            # Check if configentry is ours, could be others when targeting areas for example
            if (config_entry.domain == DOMAIN) and (domain_entry_info := config_entry.runtime_data):
                # Handle actual call
                for line in call.data.get("raw_data").splitlines():
                    line = line.strip()
                    if line.startswith("@"):
                        domain_entry_info.api.send_raw(line)


CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up Yamaha (YNCA) integration."""

    async def async_handle_send_raw_ynca_local(call: ServiceCall):
        await async_handle_send_raw_ynca(hass, call)

    hass.services.async_register(
        DOMAIN, SERVICE_SEND_RAW_YNCA, async_handle_send_raw_ynca_local
    )

    return True


type YamahaYncaConfigEntry = ConfigEntry[DomainEntryData]


async def async_setup_entry(hass: HomeAssistant, entry: YamahaYncaConfigEntry) -> bool:
    """Set up Yamaha (YNCA) from a config entry."""

    def initialize_ynca(ynca_receiver: ynca.YncaApi):
        try:
            # Synchronous function taking a long time (> 10 seconds depending on receiver capabilities)
            ynca_receiver.initialize()
            return True
        except ynca.YncaConnectionError as e:
            raise ConfigEntryNotReady(
                "Could not connect to YNCA receiver %s" % entry.title
            ) from e
        except ynca.YncaConnectionFailed as e:
            raise ConfigEntryNotReady(
                "Could not setup connection to YNCA receiver %s" % entry.title
            ) from e
        except ynca.YncaInitializationFailedException as e:
            raise ConfigEntryNotReady(
                "Could not initialize YNCA receiver %s" % entry.title
            ) from e
        except Exception:
            LOGGER.exception(
                "Unexpected exception during initialization of %s" % entry.title
            )
            return False

    def on_disconnect():
        # Reload the entry on disconnect.
        # HA will take care of re-init and retries
        try:
            asyncio.run_coroutine_threadsafe(
                hass.config_entries.async_reload(entry.entry_id), hass.loop
            ).result()
        except OperationNotAllowed:  # pragma: no cover
            # Can not reload when during setup
            # Which is fine, so just let it go
            pass

    ynca_receiver = ynca.YncaApi(
        entry.data[CONF_SERIAL_URL],
        on_disconnect,
        COMMUNICATION_LOG_SIZE,
    )
    initialized = await hass.async_add_executor_job(initialize_ynca, ynca_receiver)

    if initialized:
        await update_device_registry(hass, entry, ynca_receiver)
        await update_configentry(hass, entry, ynca_receiver)

        assert ynca_receiver.sys is not None
        if receiver_requires_audio_input_workaround(ynca_receiver.sys.modelname):
            # Pretend AUDIO provides a name like a normal input
            # This makes it work with standard code
            ynca_receiver.sys.inpnameaudio = "AUDIO"  # type: ignore

        entry.runtime_data = DomainEntryData(
            api=ynca_receiver,
            initialization_events=ynca_receiver.get_communication_log_items(),
        )

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        entry.async_on_unload(entry.add_update_listener(async_update_options))

    return initialized


async def async_unload_entry(hass: HomeAssistant, entry: YamahaYncaConfigEntry) -> bool:
    """Unload a config entry."""

    def close_ynca(ynca_receiver: ynca.YncaApi):
        ynca_receiver.close()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        domain_entry_info = entry.runtime_data
        await hass.async_add_executor_job(close_ynca, domain_entry_info.api)

    return unload_ok
