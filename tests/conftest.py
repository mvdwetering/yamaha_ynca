"""Fixtures for testing."""

from __future__ import annotations

from collections.abc import Callable, Generator
from dataclasses import dataclass
from typing import NamedTuple
from unittest.mock import DEFAULT, Mock, patch

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
import pytest
from pytest_homeassistant_custom_component.common import (  # type: ignore[import]
    MockConfigEntry,
    mock_device_registry,
)

from custom_components import yamaha_ynca
from custom_components.yamaha_ynca.helpers import DomainEntryData
import ynca

MODELNAME = "ModelName"

INPUT_SUBUNITS = [
    "airplay",
    "bt",
    "dab",
    "deezer",
    "ipod",
    "ipodusb",
    "napster",
    "netradio",
    "pandora",
    "pc",
    "rhap",
    "server",
    "sirius",
    "siriusir",
    "siriusxm",
    "spotify",
    "tidal",
    "tun",
    "uaw",
    "usb",
]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    return


# Copied from HA tests/components/conftest.py
@pytest.fixture
def entity_registry_enabled_by_default() -> Generator[None]:
    """Test fixture that ensures all entities are enabled in the registry."""
    with patch(
        "homeassistant.helpers.entity.Entity.entity_registry_enabled_default",
        return_value=True,
    ):
        yield


@pytest.fixture
def mock_zone():
    return create_mock_zone()


@pytest.fixture
def mock_zone_main():
    main_mock = create_mock_zone(ynca.subunits.zone.Main)

    main_mock.pwrb = None
    main_mock.speakera = None
    main_mock.speakerb = None
    main_mock.zonebavail = None
    main_mock.zonebname = None
    main_mock.zonebmute = None
    main_mock.zonebvol = None

    return main_mock


@pytest.fixture
def mock_zone_main_with_zoneb(mock_zone_main):
    main_mock_with_zoneb = mock_zone_main
    main_mock_with_zoneb.pwrb = ynca.PwrB.ON
    main_mock_with_zoneb.zonebavail = ynca.ZoneBAvail.READY
    main_mock_with_zoneb.zonebmute = ynca.ZoneBMute.OFF
    main_mock_with_zoneb.zonebname = "ZoneB"
    main_mock_with_zoneb.zonebvol = -34.5
    return main_mock_with_zoneb


@pytest.fixture
def mock_zone_zone2():
    return create_mock_zone(ynca.subunits.zone.Zone2)


@pytest.fixture
def mock_zone_zone3():
    return create_mock_zone(ynca.subunits.zone.Zone3)


@pytest.fixture
def mock_zone_zone4():
    return create_mock_zone(ynca.subunits.zone.Zone4)


@pytest.fixture
def mock_config_entry():
    return create_mock_config_entry()


def create_mock_zone(spec=None):
    """Create a mocked Zone instance."""
    zone = Mock(
        spec=spec or ynca.subunits.zone.ZoneBase,
    )

    zone.id = spec.id if spec else "ZoneId"

    # Disable all features (is there an easier way with less maintenance?)
    zone.adaptivedrc = None
    zone.dirmode = None
    zone.enhancer = None
    zone.hdmiout = None
    zone.hpbass = None
    zone.hptreble = None
    zone.initvollvl = None
    zone.initvolmode = None
    zone.inp = None
    zone.lipsynchdmiout1offset = None
    zone.lipsynchdmiout2offset = None
    zone.maxvol = None
    zone.mute = None
    zone.puredirmode = None
    zone.pwr = None
    zone.scene1name = None
    zone.scene2name = None
    zone.scene3name = None
    zone.scene4name = None
    zone.scene5name = None
    zone.scene6name = None
    zone.scene7name = None
    zone.scene8name = None
    zone.scene9name = None
    zone.scene10name = None
    zone.scene11name = None
    zone.scene12name = None
    zone.sleep = None
    zone.soundprg = None
    zone.spbass = None
    zone.sptreble = None
    zone.straight = None
    zone.threedcinema = None
    zone.twochdecoder = None
    zone.vol = None
    zone.zonename = None

    return zone


@pytest.fixture
def mock_ynca(hass):
    """Create a mocked YNCA instance without any inputs or subunits."""
    mock_ynca = Mock(
        spec=ynca.YncaApi,
    )

    # No zones by default
    mock_ynca.main = None
    mock_ynca.zone2 = None
    mock_ynca.zone3 = None
    mock_ynca.zone4 = None

    # No input subunits
    for input_subunit in INPUT_SUBUNITS:
        setattr(mock_ynca, input_subunit, None)

    # Setup minimal SYS subunit with no inputs
    mock_ynca.sys = Mock(spec=ynca.subunits.system.System)
    mock_ynca.sys.id = "SYS"
    mock_ynca.sys.modelname = MODELNAME
    mock_ynca.sys.version = "Version"
    mock_ynca.sys.pwr = ynca.Pwr.ON
    mock_ynca.sys.hdmiout1 = None
    mock_ynca.sys.hdmiout2 = None
    mock_ynca.sys.hdmiout3 = None
    mock_ynca.sys.sppattern = None

    for attribute in dir(mock_ynca.sys):
        if attribute.startswith("inpname"):
            setattr(mock_ynca.sys, attribute, None)

    return mock_ynca


@pytest.fixture
def device_reg(hass: HomeAssistant) -> device_registry.DeviceRegistry:
    """Return an empty, loaded, registry."""
    return mock_device_registry(hass)


def create_mock_config_entry(modelname=None, zones=None, serial_url=None):
    return MockConfigEntry(
        version=7,
        minor_version=8,
        domain=yamaha_ynca.DOMAIN,
        entry_id="entry_id",
        title=MODELNAME,
        data={
            yamaha_ynca.CONF_SERIAL_URL: serial_url or "SerialUrl",
            yamaha_ynca.const.DATA_MODELNAME: modelname or "ModelName",
            yamaha_ynca.const.DATA_ZONES: zones or [],
        },
    )


class Integration(NamedTuple):
    entry: type[yamaha_ynca.YamahaYncaConfigEntry]
    on_disconnect: Callable | None
    mock_ynca: type[Mock]


@dataclass
class DisabledEntity:
    platform: Platform
    key: str


async def setup_integration(
    hass,
    mock_ynca: ynca.YncaApi,
    skip_setup=False,
    serial_url="SerialUrl",
):
    zones = []
    if mock_ynca.main:
        zones.append("MAIN")
    if mock_ynca.zone2:
        zones.append("ZONE2")
    if mock_ynca.zone3:
        zones.append("ZONE3")
    if mock_ynca.zone4:
        zones.append("ZONE4")

    entry = create_mock_config_entry(
        modelname=mock_ynca.sys.modelname, zones=zones, serial_url=serial_url
    )
    entry.runtime_data = DomainEntryData(
        api=mock_ynca,
        initialization_events=[],
    )
    entry.add_to_hass(hass)

    on_disconnect = None

    if not skip_setup:

        def side_effect(*args, **kwargs):
            nonlocal on_disconnect
            on_disconnect = args[1]
            return DEFAULT

        with patch("ynca.YncaApi", return_value=mock_ynca, side_effect=side_effect):
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

    return Integration(entry, on_disconnect, mock_ynca)
