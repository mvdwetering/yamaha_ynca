from __future__ import annotations

from custom_components.yamaha_ynca.helpers import scale


def test_scale(hass) -> None:
    assert scale(1, [1, 10], [2, 11]) == 2
