# Bump Backstage Dependencies

## Primary command

```bash
yarn backstage-cli versions:bump --release <version>
```

Replace `<version>` with the target Backstage release (e.g., `1.45.3`).

This command:
- Reads the release manifest for the target version
- Updates all `@backstage/*` packages in `package.json` to their correct versions for that release
- Runs `yarn install` to update the lockfile
- Runs `versions:migrate` to handle moved packages (unless `--skipMigrate`)

## Useful flags

| Flag | Effect |
|------|--------|
| `--release <version>` | Target a specific release (default: `main`) |
| `--pattern '@{backstage,roadiehq}/*'` | Include additional package scopes |
| `--skipInstall` | Skip `yarn install` (useful if you want to review changes first) |
| `--skipMigrate` | Skip automatic migration of moved packages |

## Workspace / monorepo usage

In a monorepo (like `rhdh-plugins`), run from the workspace root. The command updates all packages across the workspace.

If you only want to bump a single plugin package, you can run it from that package's directory -- but be aware that shared workspace deps may need alignment too.

## What it doesn't do

- Fix breaking API changes in your source code (see `fix-breaking-changes.md`)
- Update non-`@backstage/*` dependencies
- Migrate your code from legacy to NFS APIs

## Troubleshooting

**"Could not fetch release manifest"** — Check network connectivity. The CLI fetches from `https://versions.backstage.io`. You can also set `BACKSTAGE_MANIFEST_FILE` to a local file.

**Lockfile conflicts** — Delete the lockfile and re-run `yarn install` after the bump.

**Version not found** — Verify the release version exists. Check available releases at `https://github.com/backstage/backstage/releases`.

**Workspace resolution errors** — In monorepos, ensure all workspace packages are using compatible version ranges. Run `yarn dedupe @backstage/*` after the bump.
