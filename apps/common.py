import json
import logging
import os
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

REQUESTS = Counter("sre_http_requests_total", "HTTP requests", ["service", "method", "path", "status"])
LATENCY = Histogram("sre_http_request_duration_seconds", "Request latency", ["service", "path"])


def configure(app: FastAPI, service: str) -> None:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
    if endpoint:
        provider = TracerProvider(resource=Resource.create({"service.name": service}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)

    logger = logging.getLogger(service)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        stream = logging.StreamHandler()
        stream.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(stream)
        path = os.getenv("APP_LOG_FILE")
        if path:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(path)
            handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(handler)

    @app.middleware("http")
    async def observe(request: Request, call_next):
        start = time.monotonic()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        finally:
            route = request.scope.get("route")
            route_name = getattr(route, "path", "_unmatched")
            REQUESTS.labels(service, request.method, route_name, str(status)).inc()
            elapsed = time.monotonic() - start
            LATENCY.labels(service, route_name).observe(elapsed)
            context = trace.get_current_span().get_span_context()
            record = {"service": service, "method": request.method, "path": route_name,
                      "status": status, "duration_ms": round(elapsed * 1000, 2),
                      "trace_id": format(context.trace_id, "032x") if context.is_valid else ""}
            logger.info(json.dumps(record))

    @app.get("/metrics", include_in_schema=False)
    def metrics():
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/health/live")
    def live():
        return {"status": "alive"}

    @app.get("/health/ready")
    def ready():
        return {"status": "ready"}
