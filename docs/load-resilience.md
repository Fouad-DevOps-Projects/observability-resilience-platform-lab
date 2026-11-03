# Load testing and automated resilience checks

This repository includes two **bounded** k6 profiles and a no-cluster-mutation resilience test suite.

## What is automated

- `apps/tests/test_resilience.py` covers downstream fault injection, dependency HTTP 500/503, malformed JSON, connection refusal, read timeout, and return to HTTP 200.
- GitHub Actions runs the Python tests and then starts the gateway/downstream on the ephemeral CI runner, executes `k6` against `127.0.0.1`, and **fails the pipeline if thresholds fail**.
- `tests/load/smoke.js`: 2 users for 15 seconds; p95 <500 ms, <0.5% failures, >99% passing checks.
- `tests/load/baseline.js`: capped at 3 requests per second for 60 seconds, up to 10 virtual users, with a guard requiring `RUN_LOAD_TEST=yes`. Also fails on dropped iterations.

These numeric thresholds are **test acceptance criteria**, not measured performance claims. GitHub CI will report the actual result after it runs. See [k6 thresholds](https://grafana.com/docs/k6/latest/using-k6/thresholds/) for details.

## Run locally via Docker Compose

```bash
docker compose up -d --build
curl -fsS http://localhost:8000/checkout

# Fast CI-like smoke check
docker compose --profile tools run --rm k6 run /scripts/smoke.js

# Explicit, bounded local baseline test
docker compose --profile tools run --rm \
  -e RUN_LOAD_TEST=yes k6 run /scripts/baseline.js
```

Run Python fault-response tests without stopping real downstream Pods:

```bash
python3 -m pip install -r apps/requirements-dev.txt
python3 -m pytest apps/tests/test_resilience.py -q
```

## On the existing GKE lab (manual, optional)

**Do not load-test public endpoints or shared production infrastructure.** Only target the disposable GKE lab when you have confirmed available node capacity. The `baseline.js` guard keeps the test opt-in; it doesn't prevent running it against an unintended destination, so check `TARGET_URL` before execution.

```bash
# Terminal A: listen only on WSL loopback
kubectl -n sre-lab port-forward svc/sre-gateway 8085:8000

# Terminal B: installed local k6 binary; not the Compose k6 container
TARGET_URL=http://127.0.0.1:8085 RUN_LOAD_TEST=yes \
  k6 run tests/load/baseline.js
```

If local k6 isn't installed, test using Docker with host networking **only on Linux**. Do not assume Docker Desktop's container sees WSL localhost; use local k6 for the GKE port-forward scenario.

Capture the actual k6 summary, exact run time, GKE node/Pod utilization, Grafana dashboard over the corresponding time range and any `dropped_iterations`. Do not publish fabricated latency or capacity figures. This script generates approximately 180 intended requests, but actual completed requests depend on load generator scheduling and the service.

## Fault injection discipline

The new automated Python resilience tests simulate failures with mocked `httpx` transports. They verify expected API behavior **without changing Kubernetes deployments** or triggering real alerts.

Real GKE incident injection remains a separate, explicitly controlled experiment described in the [incident report](incidents/incident-report.md). It can change live availability; perform it only inside an authorized, non-production lab with rollback steps and traffic controls.

## Remaining limitations

- A CI smoke pass is not evidence of GKE capacity or long-term production reliability.
- Alertmanager external notifications, durable observability storage, and GitOps dashboard provisioning are independent follow-on tasks.
- The live GKE cluster continues incurring charges until infrastructure cleanup.
