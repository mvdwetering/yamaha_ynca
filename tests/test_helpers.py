from __future__ import annotations

from custom_components.yamaha_ynca.helpers import scale, extract_protocol_version


def test_scale() -> None:
    assert scale(1, [1, 10], [2, 11]) == 2


def test_extract_protocol_version() -> None:
    # Some real versions
    assert extract_protocol_version("1.23/1.04") == (1, 4)
    assert extract_protocol_version("2.78/1.81") == (1, 81)
    assert extract_protocol_version("1.80/2.01") == (2, 1)
    assert extract_protocol_version("3.70/2.01") == (2, 1)
    assert extract_protocol_version("1.53/3.12") == (3, 12)
    assert extract_protocol_version("1.67/3.14") == (3, 14)
    assert extract_protocol_version("2.86/4.41") == (4, 41)

    # Some invalid versions
    assert extract_protocol_version("invalid") == (0, 0)
    assert extract_protocol_version(None) == (0, 0)
