"""Repeatable fault-response tests with no live cluster modifications."""

import os
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.pop("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT", None)

from gateway import app as gateway_app
from downstream import app as downstream_app


class FakeTransport(httpx.AsyncBaseTransport):
    def __init__(self, outcome):
        self.outcome = outcome

    async def handle_async_request(self, request):
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return self.outcome


def patch_downstream(monkeypatch, response):
    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=FakeTransport(response), **kwargs),
    )


def test_downstream_failure_injection_is_opt_in(monkeypatch):
    monkeypatch.delenv("FORCE_FAILURE", raising=False)
    with TestClient(downstream_app) as client:
        assert client.get("/process").status_code == 200
        monkeypatch.setenv("FORCE_FAILURE", "true")
        assert client.get("/process").status_code == 503
        monkeypatch.delenv("FORCE_FAILURE", raising=False)
        assert client.get("/process").status_code == 200


@pytest.mark.parametrize(
    "failure",
    [
        httpx.Response(503, json={"detail": "downstream unavailable"}),
        httpx.Response(500, json={"detail": "internal error"}),
        httpx.Response(200, text="invalid json"),
        httpx.ConnectError("connection refused"),
        httpx.ReadTimeout("dependency timeout"),
    ],
    ids=["503", "500", "bad-json", "connection-refused", "read-timeout"],
)
def test_gateway_maps_dependency_failures_to_503(monkeypatch, failure):
    patch_downstream(monkeypatch, failure)
    with TestClient(gateway_app) as client:
        response = client.get("/checkout")
    assert response.status_code == 503
    assert response.json()["detail"] == "downstream unavailable"


def test_gateway_recovers_when_dependency_recovers(monkeypatch):
    with TestClient(gateway_app) as client:
        patch_downstream(
            monkeypatch,
            httpx.Response(503, json={"detail": "injected failure"}),
        )
        assert client.get("/checkout").status_code == 503

        patch_downstream(
            monkeypatch,
            httpx.Response(200, json={"processed": True}),
        )
        response = client.get("/checkout")

    assert response.status_code == 200
    assert response.json() == {
        "checkout": "ok",
        "downstream": {"processed": True},
    }
