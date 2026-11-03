# Validated GKE deployment

The observability platform was deployed on the single-node `portfolio-gke` GKE cluster in `me-central1-a`. The shared lab was **decommissioned on 3 November 2026**, after its configuration, incident exercises and benchmark results were preserved. Terraform successfully destroyed the node pool and cluster; independent post-destroy checks showed empty GKE and Compute Engine resource lists. [Teardown record](https://github.com/Fouad-DevOps-Projects/cloud-native-infrastructure/blob/main/docs/evidence/gke/teardown/README.md). The original gateway/downstream/Tempo/OTEL resources were reconciled by the `sre-lab` Argo CD Application. The logging and secret resources were originally applied with `kubectl`; the new [add-on Argo Applications](../argocd/addons.yaml) require explicit, safe adoption ([runbook](gitops-adoption.md)).

## Prerequisites

- Access to the GKE context and Argo CD with sufficient permissions.
- Monitoring stack (Prometheus Operator, Prometheus, Grafana and Alertmanager).
- External Secrets Operator installed, GCP Secret Manager API enabled, an existing `sre-ghcr-dockerconfig` secret, and properly scoped Workload Identity IAM binding for `sre-lab/sre-secret-reader`.
- GitHub Actions publishes the API image to GHCR. `ghcr-pull` must resolve before starting the private-image workloads. Never store Docker auth JSON in the repository.

## Deploy / inspect

```bash
kubectl get applications -n argocd
kubectl get pods,svc -n sre-lab
kubectl get servicemonitor -n sre-lab
kubectl get secretstore,externalsecret -n sre-lab
kubectl get prometheusrule sre-checkout-slo -n monitoring
```

On a fresh cluster, satisfy the prerequisites, create `sre-lab`, create/configure the Secret Manager reader identity, reconcile `ghcr-pull`, and only then install [`argocd/sre-lab.yaml`](../argocd/sre-lab.yaml). Follow [GitOps adoption](gitops-adoption.md) for the existing logging/secrets/SLO add-ons; do not simultaneously hand ownership to multiple Applications.

## Verify endpoints and SLOs

```bash
kubectl port-forward -n sre-lab svc/sre-gateway 8085:8000
# Second terminal:
curl -i http://localhost:8085/checkout
curl -s http://localhost:8085/metrics | grep sre_http_requests_total
```

The Grafana Tempo data source is `http://sre-tempo.sre-lab.svc.cluster.local:3200`; the Loki data source is `http://sre-loki.sre-lab.svc.cluster.local:3100`. Both are private Kubernetes Services. Verify Prometheus ServiceMonitor targets and recording rules. Prometheus stores the app's service label as `exported_service`.

## Verified lab outcomes

- A two-service, nine-span checkout trace and matching Loki trace ID.
- Availability, error-rate, latency and throughput dashboard.
- Controlled downstream outage: availability 14.3%, 5xx 85.7%; Prometheus alert Pending → Firing, followed by recovery.
- Tempo OOM (exit 137) corrected through GitOps by increasing memory limit to 1Gi.

See [the incident report](incidents/incident-report.md) and [screenshot gallery](../README.md#incident-drill-detect--respond--recover).

## Operational limits

Tempo and Loki use `emptyDir` and lose local data upon Pod replacement. The cluster uses a single worker and is *not* production-grade high availability. No external Alertmanager notification was verified. The GKE lab was destroyed and independently verified on 3 November 2026. The separately created GCP Secret Manager secret remained immediately after Terraform teardown and was subsequently deleted with its three stored versions; verify GHCR token revocation separately. A fresh deployment will incur new cloud costs.
