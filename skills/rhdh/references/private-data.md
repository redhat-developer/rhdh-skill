# Private Data Repository

Repository for Jira Rich Filter exports and other operational data used by RHDH skills. Clone it alongside the other RHDH repos and register it via `rhdh config set private-data /path`.

## Repository

- **URL:** `git@gitlab.cee.redhat.com:rhidp/rhdh-skill-private-data.git`
- **Maintainers:** Matt Reid, Jasper Chui (Rich Filter owners)

## Contents

| Path | Description |
|------|-------------|
| `jira-rich-filter/rhidp-operational-rich-filter.json` | Exported "RHIDP Operational" Rich Filter — project-scoped JQL, component exclusion lists, team Cloud ID mappings, queue definitions |

## Setup

**Clone** and **register:**

```bash
git clone git@gitlab.cee.redhat.com:rhidp/rhdh-skill-private-data.git
rhdh config set private-data /path/to/rhdh-skill-private-data
```

**Update** (pull latest Rich Filter export):

```bash
cd /path/to/rhdh-skill-private-data && git pull
```

## How It's Used

The `rhdh-release` skill discovers this repo via `rhdh.config.get_repo("private-data")` and reads the Rich Filter JSON at runtime to source JQL queries. When the file is available, it overlays the markdown JQL templates with queries composed from the Rich Filter. When the repo is not configured, freeze commands error with a clear message listing available templates.
