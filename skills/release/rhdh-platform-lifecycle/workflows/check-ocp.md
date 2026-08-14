# Check OCP Version Lifecycle

Query the Red Hat Product Life Cycles API for OCP version support status.

## Run

```bash
uv run scripts/check_ocp_lifecycle.py
```

### Check a specific version

```bash
uv run scripts/check_ocp_lifecycle.py --version 4.16
```

## Output

| Column | Description |
|--------|-------------|
| VERSION | OCP minor version (e.g., `4.16`) |
| OCP_SUPP | `yes` if OCP has upstream support (any phase) |
| RHDH_SUPP | `yes` if any active RHDH release supports this OCP version |
| PHASE | Current lifecycle phase (Full support, Maintenance, EUS, End of life) |
| GA_DATE | General Availability date |
| END_DATE | Latest end-of-support date across all phases |

The **RHDH_SUPP** column is the key indicator for CI coverage decisions.

## Action

Report the results. If a version is OCP-supported but not RHDH-supported (`RHDH_SUPP = no`), flag it — this may indicate a CI coverage gap or a version that RHDH has intentionally dropped. Refer to the `prow` skill for CI job management if updates are needed.

## Key Concepts

- **Full Support**: Actively supported, receives patches and security updates
- **Maintenance Support**: Past full support, still receives critical fixes
- **Extended Update Support (EUS)**: Extended lifecycle for specific versions
- An OCP version can be OCP-supported but not RHDH-supported (e.g., an older EUS version that RHDH has dropped)
