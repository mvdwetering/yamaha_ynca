"""The Yamaha (YNCA) integration."""

from __future__ import annotations

import asyncio
import contextlib
from functools import partial
from importlib.metadata import version
import re
import threading
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry, OperationNotAllowed, UnknownEntry
from homeassistant.const import Platform
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.service import ServiceCall, async_extract_config_entry_ids

import ynca

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
from .input_helpers import InputHelper
from .migrations import async_migrate_entry as migrations_async_migrate_entry
from .services import async_setup_services

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.typing import ConfigType

LOGGER.debug(
    "ynca package info, version %s, location %s", version("ynca"), ynca.__file__
)

PLATFORMS: list[Platform] = [
    Platform.MEDIA_PLAYER,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
    Platform.REMOTE,
]


async def update_device_registry(
    hass: HomeAssistant, config_entry: ConfigEntry, receiver: ynca.YncaApi
) -> None:
    # Configuration URL for devices connected through IP
    configuration_url = None
    if matches := re.match(
        r"socket:\/\/(.+):\d+",  # Extract IP or hostname
        config_entry.data[CONF_SERIAL_URL],
    ):
        configuration_url = f"http://{matches[1]}"

    # Add device explicitly to registry so other entities just have to report the identifier to link up
    registry = dr.async_get(hass)

    for zone_attr_name in ZONE_ATTRIBUTE_NAMES:
        if zone_subunit := getattr(receiver, zone_attr_name):
            devicename = build_zone_devicename(receiver, zone_subunit)
            registry.async_get_or_create(
                config_entry_id=config_entry.entry_id,
                identifiers={(DOMAIN, f"{config_entry.entry_id}_{zone_subunit.id}")},
                manufacturer=MANUFACTURER_NAME,
                name=devicename,
                model=receiver.sys.modelname,  # type: ignore[union-attr]
                sw_version=receiver.sys.version,  # type: ignore[union-attr]
                configuration_url=configuration_url,
            )

    if receiver.main and receiver.main.zonebavail is ynca.ZoneBAvail.READY:
        devicename = build_zoneb_devicename(receiver)
        registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            identifiers={(DOMAIN, f"{config_entry.entry_id}_ZONEB")},
            manufacturer=MANUFACTURER_NAME,
            name=devicename,
            model=receiver.sys.modelname,  # type: ignore[union-attr]
            sw_version=receiver.sys.version,  # type: ignore[union-attr]
            configuration_url=configuration_url,
        )


def build_zone_devicename(receiver: ynca.YncaApi, zone_subunit: ynca.ZoneBase) -> str:
    devicename = f"{receiver.sys.modelname} {zone_subunit.id}"  # type: ignore[union-attr]
    if (
        zone_subunit.zonename
        and zone_subunit.zonename.lower() != zone_subunit.id.lower()
    ):
        # Prefer user defined name over "MODEL ZONE" naming
        devicename = zone_subunit.zonename
    return devicename


def build_zoneb_devicename(receiver: ynca.YncaApi) -> str:
    devicename = f"{receiver.sys.modelname} ZoneB"  # type: ignore[union-attr]
    if receiver.main.zonebname and receiver.main.zonebname.lower() != "ZoneB".lower():  # type: ignore[union-attr]
        # Prefer user defined name over "MODEL ZONE" naming
        devicename = receiver.main.zonebname  # type: ignore[union-attr]
    return devicename


async def update_configentry(
    hass: HomeAssistant, config_entry: ConfigEntry, receiver: ynca.YncaApi
) -> None:
    # Older configurations setup before 5.3.0 will not have zones data filled
    # So fill it when not set already
    # If not set, options will not show for zones
    if DATA_ZONES not in config_entry.data:
        new_data = dict(config_entry.data)
        zones = [
            zone_attr.upper()
            for zone_attr in ZONE_ATTRIBUTE_NAMES
            if getattr(receiver, zone_attr, None)
        ]
        new_data[DATA_ZONES] = zones
        hass.config_entries.async_update_entry(config_entry, data=new_data)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    return await migrations_async_migrate_entry(hass, config_entry)


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    # Just reload the integration on update. Crude, but it works
    await hass.config_entries.async_reload(entry.entry_id)


async def async_handle_send_raw_ynca(hass: HomeAssistant, call: ServiceCall) -> None:
    for config_entry_id in await async_extract_config_entry_ids(hass, call):  # type: ignore[arg-type]
        # Check if configentry is ours, could be others when targeting areas for example
        if (
            (config_entry := hass.config_entries.async_get_entry(config_entry_id))
            and (config_entry.domain == DOMAIN)
            and (domain_entry_info := config_entry.runtime_data)
        ):
            # Handle actual call
            for line in call.data.get("raw_data").splitlines():
                line = line.strip()  # noqa: PLW2901
                if line.startswith("@"):
                    domain_entry_info.api.send_raw(line)


CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up Yamaha (YNCA) integration."""

    async_setup_services(hass)

    async def async_handle_send_raw_ynca_local(call: ServiceCall) -> None:
        await async_handle_send_raw_ynca(hass, call)

    hass.services.async_register(
        DOMAIN, SERVICE_SEND_RAW_YNCA, async_handle_send_raw_ynca_local
    )

    return True


type YamahaYncaConfigEntry = ConfigEntry[DomainEntryData]


async def preset_support_detection_hack(
    hass: HomeAssistant, ynca_receiver: ynca.YncaApi
) -> None:
    """Check which subunits explicitly do not support presets and remove the attribute from the subunit. This will make it easy to show presets for correct subunits."""

    def do_the_check() -> None:
        connection = ynca_receiver.get_raw_connection()

        for input_attribute_name in InputHelper.get_internal_subunit_attribute_names():
            if (
                subunit := getattr(ynca_receiver, input_attribute_name, None)
            ) and hasattr(subunit, "preset"):
                check_done_event = threading.Event()
                restricted = False
                subunit_id = subunit.id

                def ynca_message_callback(
                    status: ynca.YncaProtocolStatus,
                    subunit: str | None,
                    function_: str | None,
                    _value: str | None,
                    check_done_event: threading.Event,
                    subunit_id: str,
                ) -> None:
                    if subunit == subunit_id and function_ == "AVAIL":
                        check_done_event.set()
                    elif status is ynca.YncaProtocolStatus.RESTRICTED:
                        nonlocal restricted
                        restricted = True

                ynca_message_callback_with_additional_parameters = partial(
                    ynca_message_callback,
                    check_done_event=check_done_event,
                    subunit_id=subunit_id,
                )
                connection.register_message_callback(
                    ynca_message_callback_with_additional_parameters
                )
                connection.get(subunit.id, "PRESET")
                connection.get(subunit.id, "AVAIL")

                if check_done_event.wait(1) and restricted:
                    delattr(subunit, "preset")

                connection.unregister_message_callback(
                    ynca_message_callback_with_additional_parameters
                )

    await hass.async_add_executor_job(do_the_check)


async def async_setup_entry(hass: HomeAssistant, entry: YamahaYncaConfigEntry) -> bool:
    """Set up Yamaha (YNCA) from a config entry."""

    def initialize_ynca(ynca_receiver: ynca.YncaApi) -> bool:
        try:
            # Synchronous function taking a long time (> 10 seconds depending on receiver capabilities)
            ynca_receiver.initialize()
            return True  # noqa: TRY300
        except ynca.YncaConnectionError as e:
            msg = f"Could not connect to YNCA receiver {entry.title}"
            raise ConfigEntryNotReady(msg) from e
        except ynca.YncaConnectionFailed as e:
            msg = f"Could not setup connection to YNCA receiver {entry.title}"
            raise ConfigEntryNotReady(msg) from e
        except ynca.YncaInitializationFailedException as e:
            msg = f"Could not initialize YNCA receiver {entry.title}"
            raise ConfigEntryNotReady(msg) from e
        except Exception:  # noqa: BLE001
            LOGGER.exception(
                f"Unexpected exception during initialization of {entry.title}"
            )
        return False

    def on_disconnect() -> None:
        # Reload the entry on disconnect.
        # HA will take care of re-init and retries
        # OperationNotAllowed => Can not reload during setup, which is fine, so just let it go
        # UnknownEntry => Can happen when entry was removed while trying to connect and connection fails
        with contextlib.suppress(OperationNotAllowed, UnknownEntry):  # pragma: no cover
            asyncio.run_coroutine_threadsafe(
                hass.config_entries.async_reload(entry.entry_id), hass.loop
            ).result()

    ynca_receiver = ynca.YncaApi(
        entry.data[CONF_SERIAL_URL],
        on_disconnect,
        COMMUNICATION_LOG_SIZE,
    )
    initialized = await hass.async_add_executor_job(initialize_ynca, ynca_receiver)

    if initialized:
        await update_device_registry(hass, entry, ynca_receiver)
        await update_configentry(hass, entry, ynca_receiver)
        await preset_support_detection_hack(hass, ynca_receiver)

        if receiver_requires_audio_input_workaround(str(ynca_receiver.sys.modelname)):  # type: ignore[union-attr]
            # Pretend AUDIO provides a name like a normal input
            # This makes it work with standard code
            # Note that this _adds_ an attribute to the SYS subunit which essentially is a hack
            ynca_receiver.sys.inpnameaudio = "AUDIO"  # type: ignore[union-attr]

        entry.runtime_data = DomainEntryData(
            api=ynca_receiver,
            initialization_events=ynca_receiver.get_communication_log_items(),
        )

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

        entry.async_on_unload(entry.add_update_listener(async_update_options))

    return initialized


async def async_unload_entry(hass: HomeAssistant, entry: YamahaYncaConfigEntry) -> bool:
    """Unload a config entry."""

    def close_ynca(ynca_receiver: ynca.YncaApi) -> None:
        ynca_receiver.close()

    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await hass.async_add_executor_job(close_ynca, entry.runtime_data.api)

    return unload_ok
