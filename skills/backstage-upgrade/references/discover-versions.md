# Discover Current Backstage Versions

## Read package.json

Extract all `@backstage/*` dependencies from the plugin's `package.json`:

```bash
cat package.json | grep '@backstage/' | sort
```

Check both `dependencies` and `devDependencies`. Note the versions -- they should all correspond to the same Backstage release.

## Check backstage.json

If the project root has a `backstage.json`, it tracks the overall Backstage version:

```json
{
  "version": "1.45.3"
}
```

This is the canonical "base version" for the project. All `@backstage/*` packages should match this release.

## Identify the base release

`@backstage/*` packages are versioned independently, but each Backstage release pins a specific version for every package. To identify which release the current deps correspond to:

1. Pick a core package like `@backstage/core-plugin-api` and note its version
2. Cross-reference against the [release manifests](https://versions.backstage.io) or the RHDH version matrix at `../../rhdh/references/versions.md`

## Report to the user

List:
- Current `backstage.json` version (if present)
- Current `@backstage/core-plugin-api` version (quick proxy for the release)
- Any `@backstage/*` packages that are out of sync (different release from the rest)
- Any `@backstage-community/*` packages (these were moved from `@backstage/*`)

## Mixed versions

If different `@backstage/*` packages are on different releases, this is a problem. The version bump will fix it, but flag it to the user -- mixed versions cause subtle runtime errors.
