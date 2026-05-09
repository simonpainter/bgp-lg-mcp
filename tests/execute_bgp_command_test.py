import pytest

import bgp_lg


def _build_fake_telnet_client(raise_on_send: bool = False):
    class FakeTelnetClient:
        entered = False
        exited = False

        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def __aenter__(self):
            FakeTelnetClient.entered = True
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            FakeTelnetClient.exited = True

        async def send_command(self, command):
            if raise_on_send:
                raise RuntimeError("boom")
            return f"ok:{command}"

    return FakeTelnetClient


@pytest.mark.asyncio
async def test_execute_bgp_command_uses_context_manager_on_success(monkeypatch):
    fake_telnet_client = _build_fake_telnet_client()

    monkeypatch.setattr(
        bgp_lg,
        "get_server_config",
        lambda _name: {"enabled": True, "host": "example.com"},
    )
    monkeypatch.setattr(bgp_lg, "TelnetClient", fake_telnet_client)

    response = await bgp_lg.execute_bgp_command("Test Server", "show ip bgp")

    assert response == "ok:show ip bgp"
    assert fake_telnet_client.entered is True
    assert fake_telnet_client.exited is True


@pytest.mark.asyncio
async def test_execute_bgp_command_closes_connection_on_command_error(monkeypatch):
    fake_telnet_client = _build_fake_telnet_client(raise_on_send=True)

    monkeypatch.setattr(
        bgp_lg,
        "get_server_config",
        lambda _name: {"enabled": True, "host": "example.com"},
    )
    monkeypatch.setattr(bgp_lg, "TelnetClient", fake_telnet_client)

    with pytest.raises(RuntimeError, match="Failed to query Test Server: boom"):
        await bgp_lg.execute_bgp_command("Test Server", "show ip bgp")

    assert fake_telnet_client.exited is True


@pytest.mark.asyncio
async def test_execute_bgp_command_uses_global_and_per_server_limiters(monkeypatch):
    events = []

    class FakeSemaphore:
        def __init__(self, name):
            self.name = name

        async def __aenter__(self):
            events.append(f"enter:{self.name}")
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            events.append(f"exit:{self.name}")

    class FakeTelnetClient:
        async def __aenter__(self):
            events.append("enter:telnet")
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            events.append("exit:telnet")

        async def send_command(self, command):
            events.append(f"send:{command}")
            return "ok"

    async def fake_get_per_server_semaphore(server_key):
        assert server_key == "example.com:23"
        return FakeSemaphore("server")

    monkeypatch.setattr(
        bgp_lg,
        "get_server_config",
        lambda _name: {"enabled": True, "host": "example.com", "port": 23},
    )
    monkeypatch.setattr(bgp_lg, "_global_outbound_semaphore", FakeSemaphore("global"))
    monkeypatch.setattr(bgp_lg, "_get_per_server_semaphore", fake_get_per_server_semaphore)
    monkeypatch.setattr(bgp_lg, "TelnetClient", lambda **_kwargs: FakeTelnetClient())

    response = await bgp_lg.execute_bgp_command("Test Server", "show ip bgp")

    assert response == "ok"
    assert events == [
        "enter:global",
        "enter:server",
        "enter:telnet",
        "send:show ip bgp",
        "exit:telnet",
        "exit:server",
        "exit:global",
    ]
