# Verify Upgrade

Run these checks in order. Stop and fix any failures before continuing.

## Build checks

```bash
# Type check
yarn tsc

# Build
yarn build

# Lint (if configured)
yarn lint
```

## Test suite

```bash
yarn test
```

If tests fail, check whether the failures are due to:
- API changes (fix per `fix-breaking-changes.md`)
- Snapshot mismatches (update snapshots: `yarn test -u`)
- Moved packages (run `versions:migrate`)

## Import validation

Check for deprecated or moved package imports:

```bash
# Packages moved to @backstage-community
grep -r '@backstage/plugin-' src/ --include='*.ts' --include='*.tsx' | grep -v node_modules | head -20
```

Cross-reference any hits against the community plugins repo to verify they haven't been moved.

## Version consistency

Verify all `@backstage/*` packages are on the same release:

```bash
cat package.json | grep '@backstage/' | sort
```

All versions should correspond to the target release. If any are out of sync, re-run `versions:bump`.

## Runtime check (if a dev app exists)

```bash
yarn start
```

- Open the browser and verify the plugin loads
- Check the browser console for errors
- Verify core functionality works
