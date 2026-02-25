"""BGPKit API client for IP lookup (country, ASN, prefix, RPKI)."""

import ipaddress
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

BGPKIT_API_BASE = "https://api.bgpkit.com/v3"
REQUEST_TIMEOUT = 10  # seconds


def _validate_ip(ip: str) -> str:
    """Validate and normalise an IP address string.

    Args:
        ip: IPv4 or IPv6 address string.

    Returns:
        Normalised IP address string.

    Raises:
        ValueError: If the string is not a valid IP address.
    """
    ip = ip.strip()
    try:
        return str(ipaddress.ip_address(ip))
    except ValueError:
        raise ValueError(f"Invalid IP address: {ip!r}")


async def lookup_ip(ip: str) -> dict[str, Any]:
    """Look up country, ASN, prefix, and RPKI status for an IP address via BGPKit.

    Calls ``GET https://api.bgpkit.com/v3/ip-info?ip=<ip>``.

    Args:
        ip: IPv4 or IPv6 address (public or private).

    Returns:
        Dict with shape::

            {
                "ip": "string",
                "country": "string",
                "asn": {
                    "prefix": "string",
                    "asn": 1,
                    "name": "string",
                    "country": "string",
                    "rpki": "string",
                    "updatedAt": "string"
                }
            }

        When the IP is unrouted or private and BGPKit returns no prefix
        information, the ``"asn"`` key is ``None``.

    Raises:
        ValueError: For invalid IP addresses.
        RuntimeError: For upstream HTTP errors or unexpected response shapes.
    """
    normalised = _validate_ip(ip)

    url = f"{BGPKIT_API_BASE}/ip-info"
    params = {"ip": normalised}

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.get(url, params=params)
    except httpx.TimeoutException as exc:
        raise RuntimeError(
            f"BGPKit API request timed out after {REQUEST_TIMEOUT}s"
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"BGPKit API request failed: {exc}") from exc

    if response.status_code == 429:
        raise RuntimeError(
            "BGPKit API rate limit exceeded. Please wait before retrying."
        )

    if response.status_code != 200:
        raise RuntimeError(
            f"BGPKit API returned HTTP {response.status_code}: {response.text}"
        )

    try:
        payload = response.json()
    except Exception as exc:
        raise RuntimeError(
            f"BGPKit API returned non-JSON response: {response.text}"
        ) from exc

    # BGPKit wraps its response in {"code": 200, "data": {...}}
    data = payload.get("data") if isinstance(payload, dict) else None
    if data is None:
        # Treat as no-match (private / unrouted)
        return {"ip": normalised, "country": None, "asn": None}

    country = data.get("country")

    # Build ASN sub-object; absent if no BGP prefix was found
    prefix = data.get("prefix") or data.get("network")
    asn_number = data.get("asn") or data.get("as_number")
    as_name = data.get("as_name") or data.get("name")
    as_country = data.get("as_country") or data.get("asn_country") or country
    rpki = data.get("rpki_status") or data.get("rpki")
    updated_at = data.get("updated_at") or data.get("updatedAt")

    asn_obj = None
    if prefix is not None or asn_number is not None:
        asn_obj = {
            "prefix": prefix,
            "asn": asn_number,
            "name": as_name,
            "country": as_country,
            "rpki": rpki,
            "updatedAt": updated_at,
        }

    return {
        "ip": normalised,
        "country": country,
        "asn": asn_obj,
    }
