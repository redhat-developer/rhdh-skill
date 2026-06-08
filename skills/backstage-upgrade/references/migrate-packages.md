# Migrate Moved Packages

## What are moved packages?

Backstage has been moving community-maintained packages from the `@backstage/*` namespace to `@backstage-community/*`. When you upgrade, the old package names become deprecated and eventually removed.

## Automatic migration

```bash
yarn backstage-cli versions:migrate
```

This command:
1. Detects `@backstage/*` packages that have a `backstage.moved` field in their `package.json` pointing to the new name
2. Updates your `package.json` dependencies to use the new package name
3. Updates source code imports to use the new package path

### Flags

| Flag | Effect |
|------|--------|
| `--pattern '@backstage/*'` | Glob pattern for packages to check (default: `@backstage/*`) |
| `--skipCodeChanges` | Only update `package.json`, don't modify source imports |

## Other migrate subcommands

The `backstage-cli` has additional migration helpers:

| Command | What it does |
|---------|-------------|
| `migrate package-roles` | Add missing `backstage.role` fields to `package.json` |
| `migrate package-scripts` | Align `scripts` in `package.json` to match the role |
| `migrate package-exports` | Synchronize `exports` field definitions |
| `migrate package-lint-configs` | Switch to `@backstage/cli/config/eslint-factory` |
| `migrate react-router-deps` | Move `react-router` deps to peer dependencies |

Run these when the type checker or build flags issues related to package configuration.

## Manual check

After running `versions:migrate`, grep for any remaining old-namespace imports:

```bash
grep -r '@backstage/plugin-' src/ --include='*.ts' --include='*.tsx' | grep -v node_modules
```

Cross-reference any hits with the [Backstage community plugins repo](https://github.com/backstage/community-plugins) to check if they've been moved.
