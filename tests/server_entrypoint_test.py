import server


def test_run_http_server_uses_streamable_http_by_default(monkeypatch):
    class DummyMCP:
        def __init__(self):
            self.calls = []

        def run(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    dummy = DummyMCP()
    monkeypatch.setattr(server, "mcp", dummy)
    monkeypatch.delenv("TRANSPORT_MODE", raising=False)
    monkeypatch.setattr(server.sys, "argv", ["bgp-lg-mcp"])

    server.run_http_server()

    assert dummy.calls == [((), {"transport": "streamable-http"})]


def test_run_http_server_uses_stdio_when_stdio_flag_is_set(monkeypatch):
    class DummyMCP:
        def __init__(self):
            self.calls = []

        def run(self, *args, **kwargs):
            self.calls.append((args, kwargs))

    dummy = DummyMCP()
    monkeypatch.setattr(server, "mcp", dummy)
    monkeypatch.delenv("TRANSPORT_MODE", raising=False)
    monkeypatch.setattr(server.sys, "argv", ["bgp-lg-mcp", "--stdio"])

    server.run_http_server()

    assert dummy.calls == [((), {})]
