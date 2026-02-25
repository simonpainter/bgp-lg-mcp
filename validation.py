"""Validation utilities for IP addresses and CIDR notation."""

import ipaddress
from typing import Union

from pydantic import ValidationError

from models import RouteLookupRequest


def validate_ip_or_cidr(destination: str) -> tuple[bool, str]:
    """Validate if destination is a valid public IPv4/IPv6 address or CIDR subnet.

    Uses the RouteLookupRequest Pydantic model for validation.

    Args:
        destination: IP address, IPv6 address, or CIDR notation string.

    Returns:
        Tuple of (is_valid, message).
    """
    try:
        request = RouteLookupRequest(destination=destination)
        validated = request.destination
        if "/" in validated:
            network = ipaddress.ip_network(validated, strict=False)
            return True, f"Valid CIDR subnet: {network}"
        ip = ipaddress.ip_address(validated)
        return True, f"Valid IP address: {ip}"
    except ValidationError as e:
        errors = e.errors()
        msg = errors[0]["msg"] if errors else "Invalid input"
        # Strip the "Value error, " prefix that pydantic adds
        msg = msg.removeprefix("Value error, ")
        return False, msg


def get_ip_type(destination: str) -> str:
    """Determine if address is IPv4 or IPv6.

    Args:
        destination: IP address or CIDR notation.

    Returns:
        "IPv4", "IPv6", or "unknown".
    """
    try:
        if "/" in destination:
            network = ipaddress.ip_network(destination, strict=False)
            return "IPv6" if network.version == 6 else "IPv4"
        
        ip = ipaddress.ip_address(destination)
        return "IPv6" if ip.version == 6 else "IPv4"
    except ValueError:
        return "unknown"
