# Check RHDH Release Lifecycle

Query the Red Hat Product Life Cycles API for RHDH release information.

## Run

```bash
uv run scripts/check_rhdh_lifecycle.py
```

### Check a specific version

```bash
uv run scripts/check_rhdh_lifecycle.py --version 1.9
```

### Show only active releases

```bash
uv run scripts/check_rhdh_lifecycle.py --active-only
```

## Output

| Column | Description |
|--------|-------------|
| VERSION | RHDH release version (e.g., `1.9`) |
| SUPPORTED | `yes` or `no` |
| TYPE | `Full Support`, `Maintenance Support`, or `End of life` |
| GA_DATE | General Availability date |
| FULL_SUPPORT_END | End of Full Support phase |
| MAINTENANCE_END | End of Maintenance Support phase |
| SUPPORTED_OCP | OCP versions this RHDH release officially supports |

The `openshift_compatibility` field in the API is the authoritative source for which OCP versions each RHDH release supports.

## Action

Report the results. Use the per-release OCP support breakdown to identify which OCP versions are covered by active RHDH releases. This is the primary input for CI coverage decisions — compare with `check-ocp.md` output to spot gaps.
