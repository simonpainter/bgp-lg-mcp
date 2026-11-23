import pytest

from bgp_lg import TelnetClient


class FakeReader:
    def __init__(self, chunks):
        self.chunks = iter(chunks)

    async def read(self, size):
        return next(self.chunks, b"")


class FakeWriter:
    def __init__(self):
        self.writes = []

    def write(self, data):
        self.writes.append(data)

    async def drain(self):
        pass


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "marker_chunks",
    [
        [b" --More-- "],
        [b" --Mo", b"re-- "],
        [b"---(more)---"],
        [b"---(more 45%)---"],
    ],
)
async def test_pager_continues_and_removes_markers(marker_chunks):
    client = TelnetClient("example.com", prompt=">")
    client.reader = FakeReader(
        [b"first page\n"] + marker_chunks
        + [b"\x08\x08   \x08\x08second page\n", b"third page\n", b"router>"]
    )
    client.writer = FakeWriter()

    output = await client._read_until_prompt()

    assert client.writer.writes == [b" "]
    assert output == "first page\nsecond page\nthird page\nrouter>"
    assert "\x08" not in output


@pytest.mark.asyncio
async def test_multiple_pager_prompts_each_advance_once():
    client = TelnetClient("example.com", prompt=">")
    client.reader = FakeReader([
        b"page one\n --More-- ",
        b"\x08 \x08page two\n---(more 45%)---",
        b"page three\nrouter>",
    ])
    client.writer = FakeWriter()

    output = await client._read_until_prompt()

    assert client.writer.writes == [b" ", b" "]
    assert output == "page one\npage two\npage three\nrouter>"


@pytest.mark.asyncio
async def test_connect_disables_paging_after_authentication(monkeypatch):
    credentials = dict(zip(("username", "password"), ("user", "pass")))
    client = TelnetClient("example.com", prompt=">", **credentials)
    reader = FakeReader([
        b"Username:", b"Password: >", b"router>",
        b"terminal length 0\n% Unknown command\nrouter>",
        b"route output\nrouter>",
    ])
    writer = FakeWriter()

    async def fake_open_connection(host, port):
        return reader, writer

    monkeypatch.setattr("bgp_lg.asyncio.open_connection", fake_open_connection)

    await client.connect()
    output = await client.send_command("show route")

    assert writer.writes == [b"user\n", b"pass\n", b"terminal length 0\n", b"show route\n"]
    assert output == "route output\nrouter>"
