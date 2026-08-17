# Migration Verification

## Smoke-test checklist

Run these in order. Stop and fix any failures before continuing.

1. **`yarn tsc`** — TypeScript compilation passes with no errors
2. **`yarn build`** — Package builds successfully
3. **Default export check** — `src/index.ts` default-exports a `createFrontendPlugin` result
4. **Extensions array** — All blueprints are listed in the `extensions` array
5. **Start the app** — `yarn start` (or dev app equivalent), page loads at expected path
6. **Nav item** — Sidebar shows the plugin's nav entry
7. **API calls** — Open browser DevTools Network tab, verify API requests succeed
8. **Entity tabs** (if applicable) — Navigate to an entity, verify tab appears
9. **Translations** (if applicable) — Switch language, verify strings update

## Testing principles (any framework)

| What to verify | How |
|---------------|-----|
| Extension registration | All blueprints present in `extensions` array |
| Page shell removed | NFS page components don't include `PageWithHeader` — framework provides the header |
| Route resolution | Page accessible at its declared `path` |
| API availability | API blueprint provides the correct client instance |
| Nav items | Page with `title` + `icon` + `routeRef` appears in sidebar automatically |
| Entity tabs | Visible on entity pages for matching entity filter |
| Entity cards | Visible on entity overview for matching filter |
| Translations | Language switching renders translated strings |
| App wrappers | Provider context available to child components |
| Shared components | Component imports stay on `core-plugin-api` (work in both legacy and NFS) |
| Legacy compat | Components using `compatWrapper` (if any) render without errors |

## Scalprum / dynamic plugin verification

If dual-exporting (legacy + NFS), also verify:

- [ ] `scalprum.exposedModules` still resolves all `importName`/`module` references in existing operator config
- [ ] OCI image rebuilt and smoke-tested in RHDH with `APP_CONFIG_app_packageName=app-next`

## Consumer import check

After migrating, verify that any workspace apps (`packages/app`, dev apps) that import from the plugin still compile:

```bash
# Find all imports from the plugin
grep -r "from '@scope/my-plugin'" packages/ --include='*.ts' --include='*.tsx'
```

- **Alpha approach:** No changes needed — legacy is still at the root.
- **Colocated approach:** Legacy re-exports from `index.ts` maintain compatibility — verify they resolve.

## Quick validation commands

```bash
# Type check (from workspace root — catches consumer import issues too)
yarn tsc

# Build
yarn build

# Lint (if configured)
yarn lint

# Start NFS dev app
yarn start

# Start legacy dev app (if kept)
yarn start:legacy
```
