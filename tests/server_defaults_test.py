import pytest

import server


@pytest.mark.asyncio
async def test_ping_host_uses_routeviews_main_by_default(monkeypatch):
    def fake_get_server_config(server_name):
        if server_name == "RouteViews Main":
            return {"supports_ping": True}
        return {"supports_ping": False}

    async def fake_execute_bgp_command(server_name, command):
        assert server_name == "RouteViews Main"
        assert command == "ping 8.8.8.8"
        return "ping output"

    monkeypatch.setattr(server, "get_server_config", fake_get_server_config)
    monkeypatch.setattr(server, "execute_bgp_command", fake_execute_bgp_command)
    monkeypatch.setattr(
        server,
        "_parse_ping_output",
        lambda _response: {
            "sent": 5,
            "received": 5,
            "success_rate": 100.0,
            "min_ms": 1.0,
            "avg_ms": 2.0,
            "max_ms": 3.0,
        },
    )

    response = await server.ping_host("8.8.8.8")
    assert "Server: RouteViews Main" in response
    assert "Error:" not in response


@pytest.mark.asyncio
async def test_traceroute_host_uses_routeviews_main_by_default(monkeypatch):
    def fake_get_server_config(server_name):
        if server_name == "RouteViews Main":
            return {"supports_traceroute": True}
        return {"supports_traceroute": False}

    async def fake_execute_bgp_command(server_name, command):
        assert server_name == "RouteViews Main"
        assert command == "traceroute 1.1.1.1"
        return "traceroute output"

    monkeypatch.setattr(server, "get_server_config", fake_get_server_config)
    monkeypatch.setattr(server, "execute_bgp_command", fake_execute_bgp_command)
    monkeypatch.setattr(
        server,
        "_parse_traceroute_output",
        lambda _response, _ip: {
            "target_hostname": None,
            "total_hops": 1,
            "hops": [
                {
                    "hop_number": 1,
                    "host": "example.net",
                    "ip": "192.0.2.1",
                    "asn": "64512",
                    "times_ms": [1.0, 1.1, 1.2],
                    "rtt_avg_ms": 1.1,
                }
            ],
        },
    )

    response = await server.traceroute_host("1.1.1.1")
    assert "Server: RouteViews Main" in response
    assert "Error:" not in response
