# Full Backstage Upgrade

<prerequisites>
- Plugin or app with `@backstage/*` dependencies
- `yarn` or `npm` available
- `@backstage/cli` installed (or available via `npx`)
- Network access to fetch release manifests
</prerequisites>

<process>

## Phase 1: Discover

Load `references/discover-versions.md` and identify:
- Current `@backstage/*` versions
- Base Backstage release version
- Any version misalignment across packages

Report findings to the user before proceeding.

## Phase 2: Determine Target

Load `references/determine-target.md`.

- If the user chose **"latest for my RHDH version"**: load `../../rhdh/references/versions.md`, ask which RHDH version they target, and use the corresponding Backstage version.
- If the user chose **"specific version"**: use the version they provided.

Compare current vs target. If they match, report "Already on target version" and stop.

## Phase 3: Bump Dependencies

Load `references/bump-deps.md` and run:

```bash
yarn backstage-cli versions:bump --release <target-version>
```

Review the changes to `package.json` before continuing.

## Phase 4: Migrate Moved Packages

Load `references/migrate-packages.md` and run:

```bash
yarn backstage-cli versions:migrate
```

Check for any remaining old-namespace imports.

## Phase 5: Fix Breaking Changes

Load `references/fix-breaking-changes.md`.

1. Identify all Backstage releases between the old and new version
2. Read the changelogs for breaking changes
3. Search the plugin source for affected APIs
4. Apply fixes

If you were directed here from another skill, also apply any breaking-change checklist they referenced.

## Phase 6: Verify

Load `references/verify-upgrade.md` and run all checks:

```bash
yarn tsc
yarn build
yarn test
```

Fix any failures before reporting success.

</process>

<success_criteria>
- All `@backstage/*` deps match the target release
- No deprecated or moved package imports remain
- `yarn tsc`, `yarn build`, and `yarn test` pass
- No console errors when running the dev app (if applicable)
</success_criteria>
