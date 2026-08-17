# Backport Skill

Automate the RHDH plugin backport process — cherry-pick, PR creation, Version Packages, overlays update, and changelog.

## Quick Start

```bash
# Full automation
/backport 1.10 3456

# Create PR only, review manually
/backport 1.10 3456 --mode create

# Complete after manual merge
/backport 1.10 3456 --mode finish
```

## Modes

| Mode | Steps | Use when |
|------|-------|----------|
| `auto` (default) | 1-10 | Full hands-off backport |
| `create` | 1-6 | Want to review PR before merging |
| `finish` | 7-10 | After manually merging the backport PR |

## Features

- Uses `release-x.y/{plugin}` branches directly — supports concurrent backports
- Auto-creates release branch from latest tag if it doesn't exist
- AI conflict resolution for cherry-pick failures
- Yarn.lock-only changes (CVE fixes) skip Version Packages — no npm release needed
- Stale `maintenance-changesets-release` branches auto-cleaned
- Works across `rhdh-plugins` and `rhdh-plugin-export-overlays` repos via GitHub API

## Prerequisites

- `gh` CLI installed and authenticated
- Fork of `rhdh-plugins` with `origin` remote
- `upstream` remote pointing to `redhat-developer/rhdh-plugins`
- Python 3.9+
