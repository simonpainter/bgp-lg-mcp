import pytest

import bgp_lg


@pytest.mark.asyncio
async def test_execute_bgp_command_uses_context_manager_on_success(monkeypatch):
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
            return f"ok:{command}"

    monkeypatch.setattr(
        bgp_lg,
        "get_server_config",
        lambda _name: {"enabled": True, "host": "example.com"},
    )
    monkeypatch.setattr(bgp_lg, "TelnetClient", FakeTelnetClient)

    response = await bgp_lg.execute_bgp_command("Test Server", "show ip bgp")

    assert response == "ok:show ip bgp"
    assert FakeTelnetClient.entered is True
    assert FakeTelnetClient.exited is True


@pytest.mark.asyncio
async def test_execute_bgp_command_closes_connection_on_command_error(monkeypatch):
    class FakeTelnetClient:
        exited = False

        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            FakeTelnetClient.exited = True

        async def send_command(self, command):
            raise RuntimeError("boom")

    monkeypatch.setattr(
        bgp_lg,
        "get_server_config",
        lambda _name: {"enabled": True, "host": "example.com"},
    )
    monkeypatch.setattr(bgp_lg, "TelnetClient", FakeTelnetClient)

    with pytest.raises(RuntimeError, match="Failed to query Test Server: boom"):
        await bgp_lg.execute_bgp_command("Test Server", "show ip bgp")

    assert FakeTelnetClient.exited is True
