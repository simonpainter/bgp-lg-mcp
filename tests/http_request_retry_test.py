import pytest
import httpx

import bgp_lg


@pytest.mark.asyncio
async def test_http_request_with_retry_uses_global_outbound_limiter(monkeypatch):
    state = {"inside_limiter": False, "request_called": False}

    class FakeSemaphore:
        async def __aenter__(self):
            state["inside_limiter"] = True

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            state["inside_limiter"] = False

    class FakeClient:
        async def request(self, method, url, **kwargs):
            state["request_called"] = True
            assert state["inside_limiter"] is True
            return httpx.Response(200, request=httpx.Request(method, url))

    monkeypatch.setattr(bgp_lg, "_global_outbound_semaphore", FakeSemaphore())

    response = await bgp_lg._http_request_with_retry(
        FakeClient(), "GET", "https://api.bgpkit.com/v3/utils/asn"
    )

    assert response.status_code == 200
    assert state["request_called"] is True
    assert state["inside_limiter"] is False
