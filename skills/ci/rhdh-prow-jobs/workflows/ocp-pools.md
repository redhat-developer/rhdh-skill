# OCP Cluster Pool Management

List and manage OCP Hive ClusterPool configurations for RHDH. Covers OCP cluster pools only -- K8s platforms (AKS, EKS, GKE) use different provisioning.

## Listing

```bash
uv run scripts/list_cluster_pools.py
```

## Generating a New Pool (requires local checkout)

```bash
uv run scripts/generate_cluster_pool.py --version 4.22
uv run scripts/generate_cluster_pool.py --version 4.22 --reference 4.21
uv run scripts/generate_cluster_pool.py --version 4.22 --dry-run
```

The script:

1. Looks up the `imageSetRef` by scanning ALL cluster pools across the repo
2. Copies an existing RHDH pool as a template
3. Updates version-specific fields, sets conservative sizing (`size: 1`, `maxSize: 2`)
4. Writes the file (or outputs to stdout with `--dry-run`)

## Removing a Pool

1. Delete the `*_clusterpool.yaml` file
2. Verify no CI jobs still reference this pool's version
3. Check for remaining OCP test entries (use `workflows/ocp-jobs.md`)

## Key Details

- **Region**: All RHDH pools use `us-east-2`
- **Architecture**: `amd64`
- **Namespace**: `rhdh-cluster-pool`
- **Pool files**: `clusters/hosted-mgmt/hive/pools/rhdh/`
