import asyncio

import pytest

import bgp_lg


class FakeWriter:
    async def drain(self):
        pass


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("responses", "expected_commands", "failure_text"),
    [
        (["Username:", "Login incorrect"], ["user"], "Login incorrect"),
        (["Username:", "Password:", "Authentication failed"], ["user", "badpass"], "Authentication failed"),
    ],
)
async def test_telnet_client_connect_raises_on_authentication_failure(
    monkeypatch, responses, expected_commands, failure_text
):
    client = bgp_lg.TelnetClient("example.com", username="user", password="badpass")
    remaining_responses = iter(responses)
    sent_commands = []
    read_calls = 0

    async def fake_open_connection(host, port):
        assert host == "example.com"
        assert port == 23
        return asyncio.StreamReader(), FakeWriter()

    async def fake_send_command(command):
        sent_commands.append(command)

    async def fake_read_until_prompt(max_wait=5, require_prompt=True):
        nonlocal read_calls
        read_calls += 1
        if read_calls == 1:
            assert max_wait == 15
            assert require_prompt is False
        else:
            assert max_wait == client.timeout
            assert require_prompt is True
        return next(remaining_responses)

    monkeypatch.setattr(bgp_lg.asyncio, "open_connection", fake_open_connection)
    monkeypatch.setattr(client, "_send_command", fake_send_command)
    monkeypatch.setattr(client, "_read_until_prompt", fake_read_until_prompt)

    with pytest.raises(ConnectionError, match=failure_text):
        await client.connect()

    assert sent_commands == expected_commands
