# Determine Target Backstage Version

## For RHDH plugins

RHDH pins a specific Backstage version per release. Load the version matrix from `../../rhdh/references/versions.md` to find the mapping.

> **Dependency:** RHDH version alignment requires the `rhdh` core skill to be installed alongside this skill. If `versions.md` is not found at that path, ask the user for the target RHDH and Backstage versions directly.

Ask the user: **"Which RHDH version are you targeting?"**

| RHDH Version | Backstage Version |
|---|---|
| See `../../rhdh/references/versions.md` for the current matrix |

Use the Backstage version from the matrix as the `--release` argument for `versions:bump`.

## For standalone Backstage projects

If the plugin isn't targeting a specific RHDH release, ask the user:

- **"Latest stable"** → Use the most recent Backstage release (check `https://versions.backstage.io` or the Backstage GitHub releases page)
- **Specific version** → Use what they specify (e.g., `1.45.3`)

## Version format

The `--release` flag for `backstage-cli versions:bump` accepts:

- `main` — latest monthly release (default)
- `next` — latest weekly pre-release
- `1.45.3` — exact version pin

For RHDH alignment, always use the exact version from the matrix.

## Checking if an upgrade is needed

Compare the current base version (from `discover-versions.md`) against the target. If they match, no upgrade is needed -- tell the user.

If the target is older than current, warn the user -- downgrading is risky and may not be supported by `versions:bump`.
