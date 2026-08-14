# Check PostgreSQL Version Lifecycle

Aggregates PostgreSQL lifecycle data from three providers via endoflife.date:

- **Upstream PostgreSQL** -- community support EOL dates
- **Amazon RDS for PostgreSQL** -- AWS RDS support EOL dates
- **Azure Database for PostgreSQL** -- Azure Flexible Server support EOL dates

## Run

```bash
uv run scripts/check_pg_lifecycle.py
```

### Show only supported versions

```bash
uv run scripts/check_pg_lifecycle.py --active-only
```

## Output

| Column | Description |
|--------|-------------|
| VERSION | PostgreSQL major version (e.g., `16`) |
| SUPPORTED | `yes` if supported by at least one provider |
| UPSTREAM_EOL | Community PostgreSQL end-of-life date |
| RDS_EOL | Amazon RDS end-of-support date |
| AZURE_EOL | Azure Database end-of-support date |
| RELEASE | Upstream release date |

## Action

A PostgreSQL version should be removed from RHDH test coverage when **all three providers** have reached EOL. If only one or two providers have EOL'd but others still support it, keep the version.

For new deployments, recommend the newest major version that is supported by all three providers.
