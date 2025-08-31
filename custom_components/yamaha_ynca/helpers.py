"""Helpers for the Yamaha (YNCA) integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from homeassistant.helpers.entity import EntityDescription

    import ynca
    from ynca.subunit import SubunitBase


@dataclass
class DomainEntryData:
    api: ynca.YncaApi
    initialization_events: list[str]


def scale(
    input_value: float,
    input_range: tuple[float, float],
    output_range: tuple[float, float],
) -> float:
    """Scale a value from one range to another."""
    input_min = input_range[0]
    input_max = input_range[1]
    input_spread = input_max - input_min

    output_min = output_range[0]
    output_max = output_range[1]
    output_spread = output_max - output_min

    value_scaled = float(input_value - input_min) / float(input_spread)

    return output_min + (value_scaled * output_spread)


def receiver_requires_audio_input_workaround(modelname: str) -> bool:
    # These models do not report the (single) AUDIO input properly
    # Reported for RX-V475, including RX-V575, HTR-4066, HTR-5066 because they share firmware
    # See https://github.com/mvdwetering/yamaha_ynca/issues/230
    # Also for RX-V473, including RX-V573, HTR-4065, HTR-5065 because they share firmware
    # See https://github.com/mvdwetering/yamaha_ynca/discussions/234
    return modelname in [
        "RX-V475",
        "RX-V575",
        "HTR-4066",
        "HTR-5066",
        "RX-V473",
        "RX-V573",
        "HTR-4065",
        "HTR-5065",
    ]


def subunit_supports_entitydescription_key(
    entity_description: EntityDescription, subunit: SubunitBase
) -> bool:
    return getattr(subunit, entity_description.key, None) is not None
