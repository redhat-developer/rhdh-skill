# Check GKE Kubernetes Version Lifecycle

GKE uses a pre-existing long-running cluster. The K8s version is NOT in CI config -- updates are performed via the GCP Console.

## Run

```bash
uv run scripts/check_gke_lifecycle.py
```

## Output

Supported GKE K8s versions with their support status and dates:

- **Standard**: actively supported, receives regular patches and security updates
- **Maintenance**: past standard support, still receives critical security patches

## Action

**Always recommend upgrading to the newest Standard version.** Check the actual cluster version via the [GKE clusters page](https://console.cloud.google.com/kubernetes/list/overview).

If the API call fails, fall back to the vendor docs:

```text
WebFetch https://cloud.google.com/kubernetes-engine/docs/release-schedule
```
