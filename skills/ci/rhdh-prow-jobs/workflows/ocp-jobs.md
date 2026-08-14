# OCP Test Entry Management

Manage OCP-specific test entries in RHDH ci-operator configuration files. Covers tests that use OCP cluster claims (`cluster_claim.version`).

## Listing

```bash
uv run scripts/list_ocp_test_configs.py
uv run scripts/list_ocp_test_configs.py --branch main
```

## Generating a Test Entry

```bash
uv run scripts/generate_test_entry.py --version 4.22 --branch main
uv run scripts/generate_test_entry.py --version 4.22 --branch main --reference 4.21
```

The script outputs a ready-to-insert YAML block.

## Adding a Test Entry (requires local checkout)

1. Open the target config file (e.g., `ci-operator/config/redhat-developer/rhdh/redhat-developer-rhdh-main.yaml`)
2. Insert the new test entry in the `tests:` list, **before** `zz_generated_metadata:`
3. Place it adjacent to other `e2e-ocp-v*-helm-nightly` entries
4. Run `make update`

### Fields to set for OCP version `X.Y`

| Field | Value |
|-------|-------|
| `as` | `e2e-ocp-vX-Y-helm-nightly` |
| `cluster_claim.version` | `"X.Y"` |
| `steps.env.OC_CLIENT_VERSION` | `stable-X.Y` |

## Removing a Test Entry (requires local checkout)

1. Remove the entire test block where `as: e2e-ocp-vX-Y-helm-nightly`
2. Run `make update`
3. Check **all** product branch configs for entries that need removal
