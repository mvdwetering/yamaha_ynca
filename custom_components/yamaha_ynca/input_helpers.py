"""Helpers for the Yamaha (YNCA) integration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import ynca


@dataclass
class Mapping:
    ynca_input: ynca.Input
    subunit_attribute_name: str | None


input_mappings: List[Mapping] = [
    # Inputs provided by subunits
    Mapping(ynca.Input.AIRPLAY, "airplay"),
    Mapping(ynca.Input.BLUETOOTH, "bt"),
    Mapping(ynca.Input.IPOD, "ipod"),
    Mapping(ynca.Input.IPOD_USB, "ipodusb"),
    Mapping(ynca.Input.NAPSTER, "napster"),
    Mapping(ynca.Input.NETRADIO, "netradio"),
    Mapping(ynca.Input.PANDORA, "pandora"),
    Mapping(ynca.Input.PC, "pc"),
    Mapping(ynca.Input.RHAPSODY, "rhap"),
    Mapping(ynca.Input.SERVER, "server"),
    Mapping(ynca.Input.SIRIUS, "sirius"),
    Mapping(ynca.Input.SIRIUS_IR, "siriusir"),
    Mapping(ynca.Input.SIRIUS_XM, "siriusxm"),
    Mapping(ynca.Input.SPOTIFY, "spotify"),
    Mapping(ynca.Input.TUNER, "tun"),
    Mapping(ynca.Input.UAW, "uaw"),
    Mapping(ynca.Input.USB, "usb"),
    # Inputs with connectors on the receiver
    Mapping(ynca.Input.AUDIO1, None),
    Mapping(ynca.Input.AUDIO2, None),
    Mapping(ynca.Input.AUDIO3, None),
    Mapping(ynca.Input.AUDIO4, None),
    Mapping(ynca.Input.AV1, None),
    Mapping(ynca.Input.AV2, None),
    Mapping(ynca.Input.AV3, None),
    Mapping(ynca.Input.AV4, None),
    Mapping(ynca.Input.AV5, None),
    Mapping(ynca.Input.AV6, None),
    Mapping(ynca.Input.AV7, None),
    Mapping(ynca.Input.DOCK, None),
    Mapping(ynca.Input.HDMI1, None),
    Mapping(ynca.Input.HDMI2, None),
    Mapping(ynca.Input.HDMI3, None),
    Mapping(ynca.Input.HDMI4, None),
    Mapping(ynca.Input.HDMI5, None),
    Mapping(ynca.Input.HDMI6, None),
    Mapping(ynca.Input.HDMI7, None),
    Mapping(ynca.Input.MULTICH, None),
    Mapping(ynca.Input.PHONO, None),
    Mapping(ynca.Input.VAUX, None),
    Mapping(ynca.Input.USB, None),
]


class InputHelper:
    @staticmethod
    def get_subunit_for_input(api: ynca.YncaApi, input: ynca.Input):
        """Returns Subunit of the current provided input if possible, otherwise None"""
        for mapping in input_mappings:
            if (
                mapping.ynca_input is input
                and mapping.subunit_attribute_name is not None
            ):
                return getattr(api, mapping.subunit_attribute_name, None)
        return None

    @staticmethod
    def get_input_by_name(api: ynca.YncaApi, name: str) -> ynca.Input | None:
        """Returns input by name"""
        source_mapping = InputHelper.get_source_mapping(api)
        for source_input, source_name in source_mapping.items():
            if source_name == name:
                return source_input
        return None

    @staticmethod
    def get_name_of_input(api: ynca.YncaApi, input: ynca.Input) -> str | None:
        source_mapping = InputHelper.get_source_mapping(api)
        for source_input, source_name in source_mapping.items():
            if input is source_input:
                return source_name
        return None

    @staticmethod
    def get_source_mapping(api: ynca.YncaApi) -> Dict[ynca.Input, str]:
        """Mapping of input to sourcename for this YNCA instance."""
        source_mapping = {}

        # keep track of added inputs as some are renamable and subunits (e.g. USB)
        inputs_added = set()

        # Try renameable inputs first
        # this will also weed out inputs that are not supported on the specific receiver
        for mapping in input_mappings:
            # Use the input name with only letters and numbers
            # Solves cases like V-AUX input vs VAUX inputnmamevaux
            postfix = "".join(
                x
                for x in mapping.ynca_input.value.lower()
                if x.isalpha() or x.isdigit()
            )

            if name := getattr(api.sys, f"inpname{postfix}", None):
                inputs_added.add(mapping.ynca_input)
                source_mapping[mapping.ynca_input] = name
                continue

        # Some receivers don't expose external inputs as renameable so just add them all
        if len(source_mapping) == 0:
            for mapping in input_mappings:
                if mapping.subunit_attribute_name is None:
                    inputs_added.add(mapping.ynca_input)
                    source_mapping[mapping.ynca_input] = mapping.ynca_input.value

        # Add sources from subunits
        for mapping in input_mappings:
            if (
                mapping.subunit_attribute_name
                and mapping.ynca_input not in inputs_added
            ):
                if getattr(api, mapping.subunit_attribute_name):
                    source_mapping[mapping.ynca_input] = mapping.ynca_input.value

        return source_mapping
