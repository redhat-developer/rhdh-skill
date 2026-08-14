# Check Red Hat Product Lifecycle

Query the Red Hat Product Life Cycles API for any Red Hat product.

## Run

### Check a product by alias

```bash
uv run scripts/check_lifecycle.py --product rhbk
uv run scripts/check_lifecycle.py --product quay
```

### RHBK major version grouping

```bash
uv run scripts/check_lifecycle.py --product rhbk --group-major
```

### Show only active versions

```bash
uv run scripts/check_lifecycle.py --product quay --active-only
```

### List known aliases

```bash
uv run scripts/check_lifecycle.py --list-products
```

## Known Aliases

| Alias | Full Product Name |
|-------|-------------------|
| `rhdh` | Red Hat Developer Hub |
| `ocp` | Red Hat OpenShift Container Platform |
| `rhbk` | Red Hat build of Keycloak |
| `quay` | Red Hat Quay |
| `rosa` | Red Hat OpenShift Service on AWS |
| `osd` | Red Hat OpenShift Dedicated |

Any product name not in the alias list is passed to the API as-is.

## Output

| Column | Description |
|--------|-------------|
| VERSION | Product version (e.g., `26.2`, `3.15`) |
| SUPPORTED | `yes` if the version is still active |
| TYPE | Lifecycle type from the API (e.g., `Full Support`, `End of life`) |
| GA_DATE | General Availability date |
| END_DATE | Latest end-of-support date across all phases |

With `--group-major` (RHBK): groups minor releases under major version summaries.

## Action

Report the results. If the user asked about a specific product version, highlight whether it is still supported and when support ends. No automated updates — this is informational only.

## RHBK Note

Track **major versions only** (e.g., `26`). A major version is active if at least one of its minor releases is still supported. Use `--group-major` to see the summary.
