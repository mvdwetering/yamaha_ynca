"""Helpers for the Yamaha (YNCA) integration."""

from dataclasses import dataclass
from typing import List

import ynca


@dataclass
class DomainEntryData:
    api: ynca.YncaApi
    initialization_events: List[str]


def scale(input_value, input_range, output_range):
    input_min = input_range[0]
    input_max = input_range[1]
    input_spread = input_max - input_min

    output_min = output_range[0]
    output_max = output_range[1]
    output_spread = output_max - output_min

    value_scaled = float(input_value - input_min) / float(input_spread)

    return output_min + (value_scaled * output_spread)
