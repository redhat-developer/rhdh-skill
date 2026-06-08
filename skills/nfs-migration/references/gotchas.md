# Common Migration Gotchas

## 1. TranslationBlueprint in the wrong module

**Why:** Translations must target `pluginId: 'app'` because they're app-level resources, not plugin-scoped.

**Fix:** Move `TranslationBlueprint` into `createFrontendModule({ pluginId: 'app', extensions: [...] })`. Export the module separately.

## 2. Missing nav item for a page

**Why:** Nav items are auto-discovered from `PageBlueprint` extensions. If `title`, `icon`, or `routeRef` is missing, the page won't appear in the sidebar.

**Fix:** Set all three on `PageBlueprint.make()` params. You can also set `title` and `icon` on `createFrontendPlugin` as fallbacks.

> **Version note:** `NavItemBlueprint` was removed in recent Backstage versions. If upgrading, delete the `.make()` call and move `title`/`icon` into your `PageBlueprint` params. See `api-changes.md`.

## 3. Entity content not discovered on entity pages

**Why:** `EntityContentBlueprint` requires `path`, `title`, and `loader` to render. If any are missing, the tab won't appear. The blueprint declares its own attach point, so it works in the plugin's `extensions` array — no separate catalog module needed.

**Fix:** Verify all required params are set. If providing entity content from a separate package (third-party addon), use `createFrontendModule({ pluginId: 'catalog', extensions: [...] })` instead.

## 4. Missing `createApiFactory` wrapper in ApiBlueprint

**Why:** `ApiBlueprint.make` expects a `defineParams` callback wrapping a `createApiFactory(...)` call. Passing raw config or a plain object won't work.

**Fix:**
```tsx
// Wrong
ApiBlueprint.make({ params: { api: myApiRef, deps: {...}, factory: (...) => ... } })

// Right
ApiBlueprint.make({
  params: defineParams => defineParams(
    createApiFactory({ api: myApiRef, deps: {...}, factory: (...) => ... })
  ),
})
```

## 5. Using API refs from `@backstage/core-plugin-api` instead of `@backstage/frontend-plugin-api`

**Why:** NFS has its own API refs. The old `core-plugin-api` refs don't resolve in the new system. (Route refs from `core-plugin-api` are fine — only API refs like `configApiRef`, `fetchApiRef`, etc. need migrating.)

**Fix:** Replace all imports:
- `configApiRef` → from `@backstage/frontend-plugin-api`
- `fetchApiRef` → from `@backstage/frontend-plugin-api`
- `identityApiRef` → from `@backstage/frontend-plugin-api`
- Same for `discoveryApiRef`, `errorApiRef`, `analyticsApiRef`, etc.

## 6. Legacy components failing after migration

**Why:** Components may depend on legacy context providers (e.g. old `SidebarContext`) that aren't available in NFS.

**What works without changes:** Hooks like `useApi` and `useRouteRef` from `@backstage/core-plugin-api` work in both legacy and NFS. Keep component imports on `core-plugin-api` so the same components serve both export paths.

**Fix (when needed):** If a component depends on a legacy context provider that isn't available in NFS, wrap it with `compatWrapper()` from `@backstage/core-compat-api`:
```tsx
loader: () => import('./MyComponent').then(m => compatWrapper(<m.MyComponent />))
```

Most plugins won't need `compatWrapper` — it's rare.

## 7. Drawer content with init logic

**Why:** Drawer components mount/unmount with the drawer. Init logic (event listeners, global state) gets torn down when the drawer closes.

**Fix:** Extract init logic into a separate `AppRootElementBlueprint`. Keep the drawer component purely presentational.

## 8. Module federation singleton issues

**Why:** When running as a dynamic plugin, multiple copies of `@backstage/plugin-app-react` or `@backstage/frontend-plugin-api` cause context mismatches.

**Fix:** Ensure these packages are shared as singletons in webpack/module federation config:
```js
shared: {
  '@backstage/plugin-app-react': { singleton: true },
  '@backstage/frontend-plugin-api': { singleton: true },
}
```

## 9. Forgetting to update package.json exports/typesVersions

**Why:** Without proper `exports` and `typesVersions`, consumers can't import from sub-paths (`./alpha`, `./legacy`).

**Fix:** See `package-json.md` for the complete configuration. Both `exports` and `typesVersions` must be updated together.

## 10. Forgetting the plugin must be the default export

**Why:** NFS apps discover plugins via default imports. A named export won't be picked up by the app's `features` array or dynamic plugin loading.

**Fix:**
```tsx
// Wrong — named export
export const myPlugin = createFrontendPlugin({ pluginId: 'my-plugin', ... });

// Right — default export
export default createFrontendPlugin({ pluginId: 'my-plugin', ... });
```

## 11. JSX in a `.ts` file

**Why:** Blueprint loaders return JSX (e.g., `<m.MyPage />`). TypeScript doesn't parse JSX in `.ts` files.

**Fix:** Use `plugin.tsx` (not `.ts`) for the NFS plugin file. Imports like `from './plugin'` resolve both extensions automatically.

## 12. Re-exporting legacy APIs from the root `index.ts`

**Why:** For direct-to-GA, the root export (`.`) should be NFS-only. If you re-export legacy named exports from `index.ts`, consumers get both APIs from the same path, which defeats the purpose of the GA migration.

**Fix:** Legacy exports should only be reachable via the `./legacy` subpath:
```tsx
// src/index.ts — NFS only
export { default } from './plugin';
export { isMyPluginAvailable } from './utils';
// Do NOT re-export legacy APIs here

// src/legacy.ts — legacy only, reachable via '@scope/my-plugin/legacy'
export { myPlugin, MyPage } from './legacyPlugin';
```

## 13. Double headers in NFS pages

**Why:** Legacy page components include `PageWithHeader` or `Page` + `Header`. In NFS, the framework provides the header via `PageLayout` — using both produces double headers.

**Fix:** Create an NFS variant of each page component without the page shell. Load the NFS variant in `PageBlueprint`:
```tsx
loader: () => import('./components/MyPage').then(m => <m.NfsMyPage />)
```

See `migrate-page.md` for the dual header pattern.

## 14. `useRouteRef` returns `undefined` in NFS

**Why:** `useRouteRef` from `@backstage/frontend-plugin-api` returns `RouteFunc | undefined`. The legacy version from `core-plugin-api` throws on unbound routes instead.

**Fix:** When writing NFS-specific components, handle the `undefined` case:
```tsx
const link = useRouteRef(myRouteRef);
// link might be undefined — check before calling
const href = link?.() ?? '/fallback';
```
