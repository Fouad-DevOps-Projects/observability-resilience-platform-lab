# Safely adopting the add-ons into Argo CD

## Verified adoption result

The existing GKE cluster successfully adopted all three add-on
Applications. After manual synchronization, all five Applications
were **Synced / Healthy**. Loki and Alloy remained running with
zero restarts; ExternalSecret `ghcr-pull` remained `SecretSynced`
and Ready.

The configuration subsequently enables automatic reconciliation
and self-healing, with automatic pruning disabled. The procedure
below remains the safe process for a new cluster or fresh adoption.


The base Argo CD Application [`sre-lab`](../argocd/sre-lab.yaml) reconciles only `kubernetes/phase1`. **Do not change its source path to `kubernetes/`**: the SLO objects belong in `monitoring`, the other resources in `sre-lab`, and some resources depend on separately installed CRDs.

Three separate Applications in [`argocd/addons.yaml`](../argocd/addons.yaml) provide clear ownership:

- `sre-logging`: Loki, Alloy, and namespace-scoped least-privilege log access.
- `sre-secrets`: SecretStore, ExternalSecret, and a reader Kubernetes ServiceAccount; no credentials are stored in Git.
- `sre-slo`: PrometheusRule in the `monitoring` namespace, with `release: monitoring` for Prometheus discovery.

These Applications are declared **without automated sync** by design. They are not installed or synced merely by pushing this commit. This is deliberate: preexisting objects were applied manually, so adoption deserves a controlled change window and an explicit diff.

## Prerequisites

- Argo CD is running and the base `sre-lab` Application remains Synced/Healthy.
- `sre-lab` and `monitoring` namespaces exist.
- Prometheus Operator CRDs and External Secrets Operator CRDs are installed and healthy.
- GCP Secret Manager key `sre-ghcr-dockerconfig` already exists; GKE Workload Identity binding authorizes `sre-lab/sre-secret-reader` to read *only the intended secret*. Confirm its IAM principal matches the current GCP project number/cluster identity before redeploying elsewhere.
- ImagePullSecret `sre-lab/ghcr-pull` currently resolves correctly (never print or commit its decoded data).
- Ensure no other Argo CD Application controls the same resources. Changing an Applications' ownership without coordination can create reconciliation loops.

## Read-only preflight

```bash
kubectl get applications -n argocd
kubectl get pods -n sre-lab
kubectl get secretstore,externalsecret -n sre-lab
kubectl get prometheusrule sre-checkout-slo -n monitoring
kubectl auth can-i create applications.argoproj.io -n argocd
kubectl apply --dry-run=server -f argocd/addons.yaml
```

Inspect service account identity and the ExternalSecret without printing credentials:

```bash
kubectl get serviceaccount sre-secret-reader -n sre-lab -o yaml
kubectl get externalsecret ghcr-pull -n sre-lab -o jsonpath='{.status.conditions[*].type}{" "}{.status.conditions[*].status}{"\n"}'
```

## Controlled GitOps adoption

Create the Applications but **do not immediately sync all three at once**:

```bash
kubectl apply -f argocd/addons.yaml
kubectl get applications -n argocd
```

In the Argo CD UI, review the Diff for each Application. **Start with `sre-logging`**, check for differences in existing resources and confirm no unexpected deletion or restart. Then sync it manually with pruning disabled and verify Loki and Alloy remain healthy. Proceed with `sre-slo` and confirm the recording rules still evaluate. Adopt `sre-secrets` last: verify the ServiceAccount and SecretStore Workload Identity fields match the live setup; a bad update can prevent private-image pulls.

Suggested validation:

```bash
kubectl get applications -n argocd
kubectl get pods -n sre-lab
kubectl get prometheusrule sre-checkout-slo -n monitoring
kubectl get secretstore,externalsecret -n sre-lab
kubectl get secret ghcr-pull -n sre-lab -o jsonpath='{.type}{"\n"}'
```

Only after a stable manual sync, enable automatic sync / self-heal **per Application** if desired. Evaluate pruning separately after the ownership model has been proven. For a resource already in use, never enable automatic pruning casually.

## Dashboard lifecycle

Both dashboard exports live in `grafana/dashboards`. They are *versioned artifacts*, not yet provisioned into Grafana via GitOps. Use classic JSON for manual import; provisioning via Grafana Operator, ConfigMap sidecar or Terraform would be a separate, tested enhancement.

## Teardown

Argo CD does not provision or own the underlying GKE cluster. Deleting an Argo Application is not a substitute for deleting Terraform-managed cloud resources. Verify which resources are owned by each App before deletion, preserve required screenshots, and tear down the billable cluster using the infrastructure repository's Terraform state.
