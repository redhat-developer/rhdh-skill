# K8s Platform Job Listing (AKS, EKS, GKE)

List K8s platform test entries across RHDH release branches.

## AKS

```bash
uv run scripts/list_aks_jobs.py
uv run scripts/list_aks_jobs.py --branch main
```

## EKS

```bash
uv run scripts/list_eks_jobs.py
uv run scripts/list_eks_jobs.py --branch main
```

## GKE

```bash
uv run scripts/list_gke_jobs.py
uv run scripts/list_gke_jobs.py --branch main
```

## Updating K8s Versions (AKS/EKS, requires local checkout)

The K8s version is set per branch as the `MAPT_KUBERNETES_VERSION` env var in each CI config file:

```text
ci-operator/config/redhat-developer/rhdh/redhat-developer-rhdh-<branch>.yaml
```

Update all test entries in the file for the target platform. Example:

```yaml
  steps:
    env:
      MAPT_KUBERNETES_VERSION: "1.35"
```

`make update` is NOT required for version-only changes.

## GKE Note

GKE uses a pre-existing static cluster. Version upgrades are performed via the GCP Console, not CI config.

## Related Workflows

- Invoke `/rhdh-platform-lifecycle` to check K8s version support before updating
