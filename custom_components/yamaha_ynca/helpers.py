"""Helpers for the Yamaha (YNCA) integration."""

import ipaddress


def scale(input_value, input_range, output_range):
    input_min = input_range[0]
    input_max = input_range[1]
    input_spread = input_max - input_min

    output_min = output_range[0]
    output_max = output_range[1]
    output_spread = output_max - output_min

    value_scaled = float(input_value - input_min) / float(input_spread)

    return output_min + (value_scaled * output_spread)


def serial_url_from_user_input(user_input: str) -> str:
    # Try and see if an IP address was passed in
    # and convert to a socket url
    try:
        parts = user_input.split(":")
        if len(parts) <= 2:
            ipaddress.ip_address(parts[0])  # Throws when invalid IP
            port = int(parts[1]) if len(parts) == 2 else 50000
            return f"socket://{parts[0]}:{port}"
    except ValueError:
        pass

    return user_input
