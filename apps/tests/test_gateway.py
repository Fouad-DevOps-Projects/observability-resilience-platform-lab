import os
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.pop("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", None)
from gateway import app


def test_health():
    client = TestClient(app)
    assert client.get("/health/ready").json() == {"status": "ready"}


def test_metrics():
    client = TestClient(app)
    client.get("/")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "sre_http_requests_total" in response.text


@pytest.mark.asyncio
async def test_checkout_success(monkeypatch):
    class MockTransport(httpx.AsyncBaseTransport):
        async def handle_async_request(self, request):
            return httpx.Response(200, json={"processed": True})

    real = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: real(transport=MockTransport(), **kwargs))
    assert TestClient(app).get("/checkout").status_code == 200
