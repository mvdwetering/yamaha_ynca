from __future__ import annotations

from unittest.mock import Mock, create_autospec

import pytest

from custom_components.yamaha_ynca.input_helpers import InputHelper
from tests.conftest import INPUT_SUBUNITS
import ynca


def test_sourcemapping_inpnames_set(mock_ynca):
    # Setup external input names
    mock_sys = mock_ynca.sys
    for attribute in dir(mock_sys):
        if attribute.startswith("inpname"):
            setattr(mock_sys, attribute, f"_{attribute.upper()}_")

    mapping = InputHelper.get_source_mapping(mock_ynca)

    assert mapping[ynca.Input.AUDIO1] == "_INPNAMEAUDIO1_"
    assert mapping[ynca.Input.AUDIO2] == "_INPNAMEAUDIO2_"
    assert mapping[ynca.Input.AUDIO3] == "_INPNAMEAUDIO3_"
    assert mapping[ynca.Input.AUDIO4] == "_INPNAMEAUDIO4_"
    assert mapping[ynca.Input.AV1] == "_INPNAMEAV1_"
    assert mapping[ynca.Input.AV2] == "_INPNAMEAV2_"
    assert mapping[ynca.Input.AV3] == "_INPNAMEAV3_"
    assert mapping[ynca.Input.AV4] == "_INPNAMEAV4_"
    assert mapping[ynca.Input.AV5] == "_INPNAMEAV5_"
    assert mapping[ynca.Input.AV6] == "_INPNAMEAV6_"
    assert mapping[ynca.Input.AV7] == "_INPNAMEAV7_"
    assert mapping[ynca.Input.DOCK] == "_INPNAMEDOCK_"
    assert mapping[ynca.Input.HDMI1] == "_INPNAMEHDMI1_"
    assert mapping[ynca.Input.HDMI2] == "_INPNAMEHDMI2_"
    assert mapping[ynca.Input.HDMI3] == "_INPNAMEHDMI3_"
    assert mapping[ynca.Input.HDMI4] == "_INPNAMEHDMI4_"
    assert mapping[ynca.Input.HDMI5] == "_INPNAMEHDMI5_"
    assert mapping[ynca.Input.HDMI6] == "_INPNAMEHDMI6_"
    assert mapping[ynca.Input.HDMI7] == "_INPNAMEHDMI7_"
    assert mapping[ynca.Input.MULTICH] == "_INPNAMEMULTICH_"
    assert mapping[ynca.Input.PHONO] == "_INPNAMEPHONO_"
    assert mapping[ynca.Input.VAUX] == "_INPNAMEVAUX_"
    assert mapping[ynca.Input.USB] == "_INPNAMEUSB_"


def test_sourcemapping_inpname_some_set(mock_ynca):
    """Scenario when a receiver supports some of the inputs and therefore
    responds with only a subset of INPNAMEs
    """
    # Setup 1 input name
    mock_ynca.sys.inpnamehdmi4 = "_INPNAMEHDMI4_"

    mapping = InputHelper.get_source_mapping(mock_ynca)

    for input_ in ynca.Input:
        if input_ is ynca.Input.HDMI4:
            assert mapping[input_] == "_INPNAMEHDMI4_"
        elif input_ is ynca.Input.MAIN_ZONE_SYNC:
            # Main Zone Sync should always be present
            assert mapping[input_] == ynca.Input.MAIN_ZONE_SYNC.value
        else:
            assert input_ not in mapping


def test_sourcemapping_inpnames_not_set(mock_ynca):
    """Some receivers do not report INPNAMES at all
    Check that they all known are reported with default names
    """
    mapping = InputHelper.get_source_mapping(mock_ynca)

    assert mapping[ynca.Input.AUDIO2] == "AUDIO2"
    assert mapping[ynca.Input.AUDIO3] == "AUDIO3"
    assert mapping[ynca.Input.AUDIO4] == "AUDIO4"
    assert mapping[ynca.Input.AV1] == "AV1"
    assert mapping[ynca.Input.AV2] == "AV2"
    assert mapping[ynca.Input.AV3] == "AV3"
    assert mapping[ynca.Input.AV4] == "AV4"
    assert mapping[ynca.Input.AV5] == "AV5"
    assert mapping[ynca.Input.AV6] == "AV6"
    assert mapping[ynca.Input.AV7] == "AV7"
    assert mapping[ynca.Input.DOCK] == "DOCK"
    assert mapping[ynca.Input.HDMI1] == "HDMI1"
    assert mapping[ynca.Input.HDMI2] == "HDMI2"
    assert mapping[ynca.Input.HDMI3] == "HDMI3"
    assert mapping[ynca.Input.HDMI4] == "HDMI4"
    assert mapping[ynca.Input.HDMI5] == "HDMI5"
    assert mapping[ynca.Input.HDMI6] == "HDMI6"
    assert mapping[ynca.Input.HDMI7] == "HDMI7"
    assert mapping[ynca.Input.MULTICH] == "MULTI CH"
    assert mapping[ynca.Input.PHONO] == "PHONO"
    assert mapping[ynca.Input.VAUX] == "V-AUX"
    assert mapping[ynca.Input.USB] == "USB"


def test_sourcemapping_input_subunits(mock_ynca):
    """Check names of input subunits"""
    # Setup subunits with dummy value, but it is good enough for building sourcelist
    for input_subunit in INPUT_SUBUNITS:
        setattr(mock_ynca, input_subunit, True)

    mapping = InputHelper.get_source_mapping(mock_ynca)

    assert mapping[ynca.Input.AIRPLAY] == "AirPlay"
    assert mapping[ynca.Input.BLUETOOTH] == "Bluetooth"
    assert mapping[ynca.Input.IPOD] == "iPod"
    assert mapping[ynca.Input.IPOD_USB] == "iPod (USB)"
    assert mapping[ynca.Input.MCLINK] == "MusicCast Link"
    assert mapping[ynca.Input.NAPSTER] == "Napster"
    assert mapping[ynca.Input.NETRADIO] == "NET RADIO"
    assert mapping[ynca.Input.PANDORA] == "Pandora"
    assert mapping[ynca.Input.PC] == "PC"
    assert mapping[ynca.Input.RHAPSODY] == "Rhapsody"
    assert mapping[ynca.Input.SERVER] == "SERVER"
    assert mapping[ynca.Input.SIRIUS] == "SIRIUS"
    assert mapping[ynca.Input.SIRIUS_IR] == "SIRIUS InternetRadio"
    assert mapping[ynca.Input.SIRIUS_XM] == "SiriusXM"
    assert mapping[ynca.Input.SPOTIFY] == "Spotify"
    assert mapping[ynca.Input.TUNER] == "TUNER"
    assert mapping[ynca.Input.UAW] == "UAW"
    assert mapping[ynca.Input.USB] == "USB"


def test_sourcemapping_no_duplicates(mock_ynca):
    """Should be no duplicates, e.g. avoid USB is in the list twice"""
    # Setup subunits with dummy value, but it is good enough for building sourcelist
    for input_subunit in INPUT_SUBUNITS:
        setattr(mock_ynca, input_subunit, True)
    mock_sys = mock_ynca.sys
    for attribute in dir(mock_sys):
        if attribute.startswith("inpname"):
            setattr(mock_sys, attribute, f"_{attribute.upper()}_")

    mapping = InputHelper.get_source_mapping(mock_ynca)

    assert len(mapping.values()) == len(set(mapping.values()))


def test_sourcemapping_input_duplicates_prefer_inpname(mock_ynca):
    """Inputs mentioned multiple times (like USB)
    should use inpname<input> over default inputsubunit name
    """
    mock_ynca.usb = True
    mock_ynca.sys.inpnameusb = "_INPNAMEUSB_"

    mapping = InputHelper.get_source_mapping(mock_ynca)

    assert mapping[ynca.Input.USB] == "_INPNAMEUSB_"


def test_sourcemapping_trim_whitepspace(mock_ynca):
    """Check that (leading and trailing) whitespace is trimmed from names"""
    mock_ynca.sys.inpnamehdmi1 = "No spaces"
    mock_ynca.sys.inpnamehdmi2 = "   Leading spaces"
    mock_ynca.sys.inpnamehdmi3 = "Trailing spaces   "
    mock_ynca.sys.inpnamehdmi4 = "   Leading and trailing spaces   "

    mapping = InputHelper.get_source_mapping(mock_ynca)

    assert mapping[ynca.Input.HDMI1] == "No spaces"
    assert mapping[ynca.Input.HDMI2] == "Leading spaces"
    assert mapping[ynca.Input.HDMI3] == "Trailing spaces"
    assert mapping[ynca.Input.HDMI4] == "Leading and trailing spaces"


def test_get_name_of_input(mock_ynca):
    mock_ynca.sys.inpnameusb = "_INPNAMEUSB_"

    # Available input
    name = InputHelper.get_name_of_input(mock_ynca, ynca.Input.USB)
    assert name == "_INPNAMEUSB_"

    # Unavailable input
    name = InputHelper.get_name_of_input(mock_ynca, ynca.Input.HDMI1)
    assert name is None


def test_get_input_by_name(mock_ynca):
    mock_ynca.sys.inpnameusb = "_INPNAMEUSB_"

    # Available input
    input_ = InputHelper.get_input_by_name(mock_ynca, "_INPNAMEUSB_")
    assert input_ is ynca.Input.USB

    # Unavailable input
    input_ = InputHelper.get_input_by_name(mock_ynca, "Unknown")
    assert input_ is None


def test_get_subunit_for_input(mock_ynca):
    mock_ynca.usb = True

    # Available subunit
    subunit = InputHelper.get_subunit_for_input(mock_ynca, ynca.Input.USB)
    assert subunit is mock_ynca.usb

    # Unavailable subunit
    subunit = InputHelper.get_subunit_for_input(mock_ynca, ynca.Input.AIRPLAY)
    assert subunit is None

    # Unavailable subunit because not related to a subunit
    subunit = InputHelper.get_subunit_for_input(mock_ynca, ynca.Input.HDMI6)
    assert subunit is None


def test_get_input_for_subunit_no_input():
    t = create_autospec(ynca.subunits.tun.Tun)
    t.id = Mock()
    t.id.value = "test_subunit"

    with pytest.raises(ValueError):
        InputHelper.get_input_for_subunit(t)
