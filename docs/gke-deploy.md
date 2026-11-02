# Reusing the existing GKE cluster

This file documents a **planned** deployment, not successful execution.

## Prerequisites

- Confirm the new GitHub Actions image publishing job succeeds before applying the Argo CD application.
- A GHCR image may be private; create the `ghcr-pull` Docker Registry Secret in namespace `sre-lab` with credentials that can read this package. Never commit the credential.
- Existing Argo CD, Prometheus and Grafana stay in their original namespaces.

## Deploy

```bash
kubectl create namespace sre-lab --dry-run=client -o yaml | kubectl apply -f -
# Securely create ghcr-pull first; keep its contents out of Git and shell history.
kubectl apply -f argocd/sre-lab.yaml
kubectl get applications -n argocd
kubectl get pods,svc -n sre-lab
kubectl get servicemonitors -n sre-lab
kubectl top node
```

The four Phase-1 Pods request a total of 250m CPU and 420Mi memory. Their combined limits are 1150m CPU and 1152Mi memory. The node previously showed overcommitted limits, so watch OOMKill and scheduling failures. No external LoadBalancer and no PVC is requested.

## Validate

```bash
kubectl port-forward -n sre-lab svc/sre-gateway 8000:8000
# In a second terminal:
curl -i http://localhost:8000/checkout
curl -s http://localhost:8000/metrics | grep sre_http_requests_total
```

Look for the `sre-lab/sre-apis` ServiceMonitor in Prometheus Targets. For Tempo, add the Grafana datasource URL `http://sre-tempo.sre-lab.svc.cluster.local:3200`, then verify gateway and downstream spans from the same trace.

**Data retention:** Tempo uses `emptyDir`, so traces disappear after Pod recreation. This is a small educational lab, not production HA. Capture real screenshots and sanitized CLI outputs before teardown.
