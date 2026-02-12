"""Validation utilities for IP addresses and CIDR notation."""

import ipaddress
from typing import Union


def validate_ip_or_cidr(destination: str) -> tuple[bool, str]:
    """Validate if destination is a valid public IPv4/IPv6 address or CIDR subnet.

    Args:
        destination: IP address, IPv6 address, or CIDR notation string.

    Returns:
        Tuple of (is_valid, message).
    """
    destination = destination.strip()

    try:
        # Try to parse as CIDR subnet first
        if "/" in destination:
            network = ipaddress.ip_network(destination, strict=False)
            
            # Check if it's a public address (not private/reserved)
            if network.is_private or network.is_loopback or network.is_link_local:
                return False, f"CIDR subnet {destination} is not public"
            
            return True, f"Valid CIDR subnet: {network}"
        
        # Try to parse as individual IP address
        ip = ipaddress.ip_address(destination)
        
        # Check if it's a public address
        if ip.is_private or ip.is_loopback or ip.is_link_local:
            return False, f"Address {destination} is not public"
        
        return True, f"Valid IP address: {ip}"
    
    except ValueError as e:
        return False, f"Invalid IP address or CIDR notation: {str(e)}"


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
