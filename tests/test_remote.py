from __future__ import annotations

from unittest.mock import ANY, Mock, call, patch
import pytest

import ynca

import custom_components.yamaha_ynca as yamaha_ynca
from custom_components.yamaha_ynca.remote import (
    YamahaYncaZoneRemote,
    async_setup_entry,
)

from tests.conftest import setup_integration


@patch("custom_components.yamaha_ynca.remote.YamahaYncaZoneRemote", autospec=True)
async def test_async_setup_entry(
    yamahayncazoneremote_mock, hass, mock_ynca, mock_zone_main, mock_zone_zone3
):
    mock_ynca.main = mock_zone_main
    mock_ynca.zone3 = mock_zone_zone3

    integration = await setup_integration(hass, mock_ynca)
    add_entities_mock = Mock()

    await async_setup_entry(hass, integration.entry, add_entities_mock)

    yamahayncazoneremote_mock.assert_has_calls(
        [
            call("entry_id", mock_ynca, mock_ynca.main, ANY),
            call("entry_id", mock_ynca, mock_ynca.zone3, ANY),
        ]
    )

    add_entities_mock.assert_called_once()
    entities = add_entities_mock.call_args.args[0]
    assert len(entities) == 2


async def test_remote_entity_fields(mock_ynca, mock_zone_zone3):
    entity = YamahaYncaZoneRemote("ReceiverUniqueId", mock_ynca, mock_zone_zone3, {})

    assert entity.unique_id == "ReceiverUniqueId_ZONE3_remote"
    assert entity.device_info["identifiers"] == {
        (yamaha_ynca.DOMAIN, "ReceiverUniqueId_ZONE3")
    }


async def test_remote_send_codes_mapped(mock_ynca, mock_zone_zone3):
    codes = {
        "code1": "12-AB",
        "code2": "12-CDEF",
        "code3": "1234-ABCD",
        "code1_no_sep": "12AB",
        "code2_no_sep": "12CDEF",
        "code3_no_sep": "1234ABCD",
        "code1_other_sep": "12:AB",
        "code2_other_sep": "12/CDEF",
        "code3_other_sep": "1234_ABCD",
    }
    entity = YamahaYncaZoneRemote("ReceiverUniqueId", mock_ynca, mock_zone_zone3, codes)

    # Setting value
    expected_call_count = 0
    for name, code in codes.items():
        entity.send_command([code])

        expected_call_count += 1
        assert mock_ynca.sys.remotecode.call_count == expected_call_count

        if name.startswith("code1"):
            mock_ynca.sys.remotecode.assert_called_with("12EDAB54")
        elif name.startswith("code2"):
            mock_ynca.sys.remotecode.assert_called_with("12EDCDEF")
        elif name.startswith("code3"):
            mock_ynca.sys.remotecode.assert_called_with("1234ABCD")
        else:
            assert False


async def test_remote_send_codes_raw_formats(mock_ynca, mock_zone_zone3):
    entity = YamahaYncaZoneRemote("ReceiverUniqueId", mock_ynca, mock_zone_zone3, {})

    # Setting value
    entity.send_command(["12ABCD"])
    mock_ynca.sys.remotecode.assert_called_with("12EDABCD")

    with pytest.raises(ValueError):
        entity.send_command(["not a valid code"])


async def test_remote_turn_on_off(mock_ynca, mock_zone_zone3):
    mock_zone_zone3.pwr = ynca.Pwr.STANDBY

    entity = YamahaYncaZoneRemote(
        "ReceiverUniqueId",
        mock_ynca,
        mock_zone_zone3,
        {"on": "12345678", "standby": "90ABCDEF"},
    )

    entity.turn_on()
    mock_ynca.sys.remotecode.assert_called_with("12345678")

    entity.turn_off()
    mock_ynca.sys.remotecode.assert_called_with("90ABCDEF")
