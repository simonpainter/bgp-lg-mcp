import pytest

import server


@pytest.mark.asyncio
async def test_ping_host_rejects_cidr_notation():
    response = await server.ping_host("8.8.8.0/24")
    assert "CIDR notation is not allowed for ping" in response


@pytest.mark.asyncio
async def test_traceroute_host_rejects_cidr_notation():
    response = await server.traceroute_host("8.8.8.0/24")
    assert "CIDR notation is not allowed for traceroute" in response
