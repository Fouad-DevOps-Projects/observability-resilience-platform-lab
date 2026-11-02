# Experiment plan and evidence checklist

**The entries below are plans, not completed tests.** Run the commands and commit actual dated outputs/screenshots before marking any experiment verified.

## 1. Boot and service readiness

```bash
docker compose up -d --build
docker compose ps
curl -i http://localhost:8000/health/ready
curl -i http://localhost:8000/checkout
```

Expect both endpoints to return 200 when the downstream service is ready. Capture actual Compose status and curl output.

## 2. Metrics and SLI baseline

Open http://localhost:9090/targets and verify the gateway and downstream jobs are UP. Query:

```promql
sum(rate(sre_http_requests_total{service="gateway",path="/checkout"}[2m]))
sum(rate(sre_http_requests_total{service="gateway",path="/checkout",status=~"5.."}[2m]))
histogram_quantile(0.95,sum by (le)(rate(sre_http_request_duration_seconds_bucket{service="gateway",path="/checkout"}[5m])))
```

SLO proposal: checkout availability >= 99% and p95 latency < 1 second under defined normal test load. These are **targets**, not measured claims. Capture dashboard queries, time window and observed results.

## 3. Distributed tracing and logs

Call /checkout repeatedly, then open Grafana Explore:
- Tempo: find spans named for gateway /checkout and downstream /process, confirm a shared trace ID.
- Loki: search `{job="sre-app"}` and find JSON entries for both services. Confirm trace IDs can link logs to Tempo traces where emitted.
- Save redacted screenshots of real results; never fabricate traces.

## 4. Load test

```bash
docker compose --profile tools run --rm k6 run /scripts/smoke.js
```

Save k6 output and match time windows against Prometheus p95/error rate and Loki logs. Thresholds in the script are expectations until validated.

## 5. Controlled failure and recovery

```bash
docker compose stop downstream
curl -i http://localhost:8000/checkout
docker compose start downstream
curl -i http://localhost:8000/checkout
```

Record exact UTC timestamps, request status, detection delay, recovery delay and actual Alertmanager firing/resolved evidence. Note: Alertmanager currently has **no external notification receiver**; it cannot demonstrate email/Slack delivery.

## 6. Teardown

```bash
docker compose --profile tools down
```

Volumes remain by default for evidence; use `docker compose down -v` only when you're ready to delete local metrics/traces.
