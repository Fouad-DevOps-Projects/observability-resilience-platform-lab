import os
import httpx
from fastapi import FastAPI, HTTPException
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from common import configure

app = FastAPI(title="SRE Gateway")
configure(app, "gateway")
if os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT"):
    HTTPXClientInstrumentor().instrument()


@app.get("/")
def root():
    return {"service": "gateway", "status": "ok"}


@app.get("/checkout")
async def checkout():
    url = os.getenv("DOWNSTREAM_URL", "http://localhost:8001")
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(url + "/process")
            response.raise_for_status()
        return {"checkout": "ok", "downstream": response.json()}
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="downstream unavailable") from exc
