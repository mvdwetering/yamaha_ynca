from __future__ import annotations

from typing import TYPE_CHECKING

from custom_components.yamaha_ynca.helpers import scale

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def test_scale(hass: HomeAssistant) -> None:
    assert scale(1, [1, 10], [2, 11]) == 2
