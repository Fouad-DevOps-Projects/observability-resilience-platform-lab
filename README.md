# Observability & Resilience Platform Lab

A hands-on SRE portfolio project for **metrics, structured logs, distributed tracing, load testing, service-level objectives and controlled failure recovery**.

**Status:** Initial implementation committed; real deployments, dashboards and failure tests must be validated before claiming success.

## Goal

Build two Python FastAPI services and observe a request end to end using Prometheus, Grafana, Loki, Tempo, OpenTelemetry and k6. Use Docker Compose locally to avoid cloud charges.

## Architecture

```mermaid
flowchart LR
  Client[k6 / HTTP] --> API[Gateway FastAPI]
  API --> Worker[Downstream FastAPI]
  API --> Prom[Prometheus]
  Worker --> Prom
  API --> OTel[OTel Collector]
  Worker --> OTel
  OTel --> Tempo[Tempo]
  API --> Alloy[Grafana Alloy]
  Worker --> Alloy
  Alloy --> Loki[Loki]
  Prom --> Grafana[Grafana]
  Tempo --> Grafana
  Loki --> Grafana
  Prom --> Alerts[Alertmanager]
```

## Getting started

```bash
docker compose up -d --build
docker compose ps
curl http://localhost:8000/health/ready
curl http://localhost:8000/checkout
```

- Gateway: http://localhost:8000
- Grafana: http://localhost:3000 (local lab initial credentials: admin / admin)
- Prometheus: http://localhost:9090
- Alertmanager: http://localhost:9093

See [experiments and evidence plan](docs/experiments.md) after the initial implementation is added. Do not publish screenshots or results from an untested deployment as though verified.
