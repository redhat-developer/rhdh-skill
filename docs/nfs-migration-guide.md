# Migrating RHDH Plugins to the New Frontend System (NFS)

A practical guide for Red Hat Developer Hub plugin authors migrating from the legacy Backstage frontend system to NFS.

> **Agent skill users:** The `nfs-migration` skill (`skills/nfs-migration/`) contains the same patterns broken into reference files optimized for agent consumption. This guide is the authoritative human-readable source. When updating migration patterns, update this guide first, then sync the corresponding reference file.

---

## 1. What is the New Frontend System

The Backstage New Frontend System (NFS) replaces the legacy frontend plugin API. Instead of manually wiring plugins into an app with `createPlugin`, `createRoutableExtension`, `FlatRoutes`, and imperative JSX route trees, NFS uses declarative extension **Blueprints** (`PageBlueprint`, `ApiBlueprint`, `EntityContentBlueprint`, etc.) and `createFrontendPlugin` from `@backstage/frontend-plugin-api`.

The app assembles itself from features:

```ts
import { createApp } from '@backstage/frontend-defaults';

const app = createApp({ features: [myPlugin, catalogPlugin, ...] });
```

Plugins declare what they provide. The app decides what to render.

---

## 2. Why Migrate

- **Declarative**: plugins describe their own routes, nav items, and APIs -- no more manual wiring in the app
- **Configurable**: extensions can be enabled, disabled, or reordered via `app-config.yaml`
- **Auto-discoverable**: apps can detect installed plugins automatically
- **Composable**: modules can inject extensions into other plugins (e.g. entity tabs into catalog)
- **Required**: the legacy APIs are being deprecated and will be removed

---

## 3. Deprecation Timeline

| Phase | What happens |
|-------|-------------|
| **Current (RHDH 1.10)** | NFS available as `/alpha` exports alongside legacy |
| **Next release (GA)** | NFS becomes the root export (`.`); legacy moves to `/legacy` with `@deprecated` tags |
| **GA + 2 releases** | Legacy `/legacy` exports removed entirely |

---

## 4. Key Concepts

### Blueprints vs Legacy Extension Factories

Blueprints are declarative factories that replace imperative helpers like `createRoutableExtension()`. Each blueprint type (`PageBlueprint`, `ApiBlueprint`, `EntityContentBlueprint`) knows how to register itself with the app. Nav items are auto-discovered from pages -- no separate blueprint needed.

```ts
// Legacy
export const MyPage = myPlugin.provide(createRoutableExtension({ ... }));

// NFS
const myPage = PageBlueprint.make({ params: { path: '/my-plugin', loader: () => ... } });
```

### `createFrontendPlugin` vs `createPlugin`

| Legacy `createPlugin` | NFS `createFrontendPlugin` |
|---|---|
| `id: 'my-plugin'` | `pluginId: 'my-plugin'` |
| `apis: [createApiFactory(...)]` | APIs go in `extensions` array as `ApiBlueprint` |
| Pages/routes wired externally | Pages declared as `PageBlueprint` in `extensions` |
| Named export | **Default export** |

### `createFrontendModule`

Bundles extensions that target *another* plugin. Common cases:

- **Translations** target `pluginId: 'app'`
- **Homepage widgets** target `pluginId: 'home'`

Modules are separate exports, not part of the plugin itself. Note: entity content and cards can go directly in your plugin's `extensions` array (they declare their own attach point) — a separate catalog module is only needed when injecting content from outside a plugin you don't own.

### Route Refs

You can reuse existing route refs from `@backstage/core-plugin-api` or create new ones from `@backstage/frontend-plugin-api`. Both work -- no need to migrate route refs immediately.

---

## 5. Migration Patterns

### Plugin Definition

**Legacy:**

```ts
import { createPlugin, createApiFactory, configApiRef, fetchApiRef } from '@backstage/core-plugin-api';
import { rootRouteRef } from './routes';
import { myApiRef, MyApiClient } from './api';

export const myPlugin = createPlugin({
  id: 'my-plugin',
  routes: { root: rootRouteRef },
  apis: [
    createApiFactory({
      api: myApiRef,
      deps: { configApi: configApiRef, fetchApi: fetchApiRef },
      factory: ({ configApi, fetchApi }) => new MyApiClient({ configApi, fetchApi }),
    }),
  ],
});
```

**NFS:**

```tsx
import {
  createFrontendPlugin, ApiBlueprint, PageBlueprint,
  configApiRef, fetchApiRef, createApiFactory,
} from '@backstage/frontend-plugin-api';
import { rootRouteRef } from './routes';
import { myApiRef, MyApiClient } from './api';
import { RiToolsLine } from '@remixicon/react';

const myApi = ApiBlueprint.make({
  params: defineParams => defineParams({
    api: myApiRef,
    deps: { configApi: configApiRef, fetchApi: fetchApiRef },
    factory: ({ configApi, fetchApi }) => new MyApiClient({ configApi, fetchApi }),
  }),
});

const myPage = PageBlueprint.make({
  params: {
    path: '/my-plugin',
    title: 'My Plugin',
    icon: <RiToolsLine />,
    routeRef: rootRouteRef,
    loader: () => import('./components/MyPage').then(m => <m.NfsMyPage />),
  },
});

export default createFrontendPlugin({
  pluginId: 'my-plugin',
  title: 'My Plugin',
  icon: <RiToolsLine />,
  extensions: [myApi, myPage],
  routes: { root: rootRouteRef },
});
```

Key changes: APIs and pages are extensions in the `extensions` array. Nav items are auto-discovered from pages with `title`, `icon`, and `routeRef`. The plugin is the **default export**.

### Pages

**Legacy** -- routable extension provided by the plugin, path set in the app's `FlatRoutes`:

```tsx
export const MyPage = myPlugin.provide(
  createRoutableExtension({
    name: 'MyPage',
    component: () => import('./components/MyPage').then(m => m.MyPage),
    mountPoint: rootRouteRef,
  }),
);

// In the app:
<FlatRoutes>
  <Route path="/my-plugin" element={<MyPage />} />
</FlatRoutes>
```

**NFS** -- the plugin owns its path. No app-side route wiring. The NFS page component must **not** include its own page shell (`PageWithHeader`) — the framework provides the header automatically:

```tsx
const myPage = PageBlueprint.make({
  params: {
    path: '/my-plugin',
    routeRef: rootRouteRef,
    loader: () => import('./components/MyPage').then(m => <m.NfsMyPage />),
  },
});
```

Create a separate NFS variant of each page component without the page shell. See `references/migrate-page.md` for the dual header pattern (Pattern A for simple pages, Pattern B for complex pages).

### Nav Items

**Legacy** -- manually added in the app's sidebar:

```tsx
<SidebarItem icon={MyIcon} to="my-plugin" text="My Plugin" />
```

**NFS** -- auto-discovered from pages. Set `title` and `icon` on `PageBlueprint` params and the app generates nav entries automatically. No separate blueprint needed — see the Plugin Definition example above.

> Earlier Backstage versions used `NavItemBlueprint`. It has been removed — see `references/api-changes.md`.

### APIs

**Legacy** -- `createApiFactory` in the plugin's `apis` array.

**NFS** -- wrap the existing `createApiFactory` call in `ApiBlueprint.make` using the `defineParams` callback. See the Plugin Definition example above. The `defineParams` callback is required -- it's how the blueprint validates the factory. See `references/migrate-page.md` for the full pattern.

### Entity Content (Catalog Tabs)

Entity content goes in your plugin's `extensions` array. The blueprint declares its own attach point, so the app discovers it automatically:

```tsx
import { EntityContentBlueprint } from '@backstage/plugin-catalog-react/alpha';
import { createFrontendPlugin } from '@backstage/frontend-plugin-api';

const myEntityContent = EntityContentBlueprint.make({
  params: {
    path: '/my-tab',
    title: 'My Tab',
    loader: () => import('./components/MyTab').then(m => <m.MyTab />),
  },
});

export default createFrontendPlugin({
  pluginId: 'my-plugin',
  extensions: [myEntityContent],
});
```

If you need to provide entity content from a separate package (third-party addon), use `createFrontendModule({ pluginId: 'catalog' })` instead.

### Translations

Translations must be in a separate module targeting `pluginId: 'app'`:

```tsx
import { createFrontendModule } from '@backstage/frontend-plugin-api';
import { TranslationBlueprint } from '@backstage/plugin-app-react';
import { myTranslations } from './translations';

export const myTranslationsModule = createFrontendModule({
  pluginId: 'app',
  extensions: [
    TranslationBlueprint.make({
      name: 'my-plugin-translations',
      params: { resource: myTranslations },
    }),
  ],
});
```

### RHDH-Specific Extensions

**Drawer panels** -- `AppDrawerContentBlueprint`:

```tsx
import { AppDrawerContentBlueprint } from '@red-hat-developer-hub/backstage-plugin-app-react/alpha';

const myDrawer = AppDrawerContentBlueprint.make({
  params: {
    title: 'My Drawer',
    loader: () => import('./components/MyDrawer').then(m => <m.MyDrawer />),
  },
});
```

**Global header menu items** -- `GlobalHeaderMenuItemBlueprint`:

```tsx
import { GlobalHeaderMenuItemBlueprint } from '@red-hat-developer-hub/backstage-plugin-global-header/alpha';

const myMenuItem = GlobalHeaderMenuItemBlueprint.make({
  params: {
    title: 'My Action',
    icon: MyIcon,
    routeRef: rootRouteRef,
  },
});
```

**Homepage widgets** -- `HomePageWidgetBlueprint`:

```tsx
import { HomePageWidgetBlueprint } from '@backstage/plugin-home-react/alpha';

const myWidget = HomePageWidgetBlueprint.make({
  params: {
    title: 'My Widget',
    loader: () => import('./components/MyWidget').then(m => <m.MyWidget />),
  },
});
```

### RHDH Mount Point Migration

If your plugin uses RHDH dynamic plugin mount points (`app-config.dynamic.yaml`), these map directly to NFS blueprints. See `references/mount-point-mapping.md` for the complete mapping table with before/after examples for each mount point type.

### Shared Components (Legacy + NFS)

Keep component imports (`useApi`, `useRouteRef`, etc.) on `@backstage/core-plugin-api` — they work in both legacy and NFS contexts. This lets the same components serve both export paths without changes:

```tsx
// Keep this — works in both legacy and NFS
import { useApi, useRouteRef } from '@backstage/core-plugin-api';
```

Don't migrate component imports to `@backstage/frontend-plugin-api` if you need to support legacy consumers — it breaks the legacy code path.

### CompatWrapper (rare)

Only needed when a component depends on legacy context providers that aren't available in NFS (e.g. old `SidebarContext`). Most plugins won't need this. Wrap the JSX element in the loader:

```tsx
loader: () => import('./components/MyPage').then(m => compatWrapper(<m.MyPage />))
```

Import `compatWrapper` from `@backstage/core-compat-api`.

---

## 6. Choosing Your Approach

### Approach A -- Direct to GA (recommended)

NFS becomes the root export immediately. Legacy code moves to `/legacy` or is removed.

Best when:
- You control all consumers
- You can do a clean migration in one pass
- You want the simplest result

### Approach B -- Phased

Add NFS as `/alpha` exports alongside existing legacy exports. Graduate later by swapping.

Best when:
- External consumers depend on legacy exports
- You need time to migrate tests and stories
- You want to ship incrementally

| | Direct to GA | Phased |
|---|---|---|
| Complexity | Lower | Higher (two export sets) |
| Consumer impact | Breaking change | Non-breaking initially |
| Maintenance | One code path | Two code paths temporarily |
| Recommended for | Internal plugins | Shared/published plugins |

---

## 7. Package.json Changes

Update your `package.json` exports for the GA structure:

```json
{
  "exports": {
    ".": "./src/index.ts",
    "./legacy": "./src/legacy.ts",
    "./package.json": "./package.json"
  },
  "typesVersions": {
    "*": {
      "legacy": ["src/legacy.ts"],
      "package.json": ["package.json"]
    }
  }
}
```

- `.` -- NFS plugin (default export from `createFrontendPlugin`)
- `./legacy` -- old `createPlugin`-based exports for consumers who haven't migrated yet
- Remove the `./legacy` entry when you drop legacy support

---

## 8. Verifying Your Migration

Run through this checklist:

- [ ] `yarn tsc` passes with no type errors
- [ ] `yarn build` succeeds
- [ ] Plugin default export is the `createFrontendPlugin` result
- [ ] All extensions (pages, APIs) are in the `extensions` array
- [ ] NFS page components don't include `PageWithHeader`/`Page` shell (dual header pattern)
- [ ] Routes are declared in the plugin's `routes` object
- [ ] Translations are in a separate `createFrontendModule` with `pluginId: 'app'`
- [ ] Entity content extensions are in the plugin's `extensions` array
- [ ] `package.json` exports are updated (`.` for NFS, `./legacy` for old)
- [ ] `src/index.ts` does NOT re-export legacy APIs (legacy only via `./legacy` subpath)
- [ ] Plugin file uses `.tsx` extension if it contains JSX in blueprint loaders
- [ ] Component imports stay on `@backstage/core-plugin-api` (shared between legacy and NFS)
- [ ] `dev/index.tsx` uses NFS dev app pattern; legacy dev app moved to `dev/legacy.tsx`
- [ ] Workspace app (`packages/app`) is NFS; legacy consumers moved to `./legacy` subpath or a separate `packages/app-legacy`

---

## 9. Testing with RHDH

### Local Testing

Use the `rhdh-local` skill to test in a local RHDH instance. If NFS is not yet the default app shell, enable it with environment variables:

```bash
APP_CONFIG_app_packageName=app-next
ENABLE_STANDARD_MODULE_FEDERATION=true
```

Export the plugin as a dynamic plugin and deploy it locally. Verify that:
- The plugin loads without errors
- Nav items appear in the sidebar
- Pages render at the correct paths
- Entity tabs show up on the right entity kinds

### Cluster Testing

For OpenShift/K8s deployments, add the plugin to your `dynamic-plugins.yaml` configuration and verify it loads in the NFS app shell. Check the browser console for extension registration logs.

---

## 10. Common Gotchas

1. **Import paths depend on your approach**: Direct-to-GA → import from root (`.`). Phased → import NFS from `./alpha`. Getting this wrong causes silent failures.

2. **TranslationBlueprint must target `pluginId: 'app'`**: Putting translations in the plugin itself won't work. They must be in a separate `createFrontendModule({ pluginId: 'app' })`.

3. **Nav items require `title` + `icon` + `routeRef` on the page**: Nav entries are auto-discovered from `PageBlueprint` extensions. If your plugin's nav item isn't appearing, ensure all three params are set. `NavItemBlueprint` was removed in recent Backstage versions -- see `references/api-changes.md`.

4. **Entity content not showing on entity pages**: Ensure `path`, `title`, and `loader` are all set on `EntityContentBlueprint`. The blueprint declares its own attach point — it works directly in the plugin's `extensions` array.

5. **ApiBlueprint uses `defineParams` callback**: Don't pass the factory directly -- wrap it: `params: defineParams => defineParams(createApiFactory(...))`.

6. **Keep component imports on `@backstage/core-plugin-api`**: Hooks like `useApi()` and `useRouteRef()` from `core-plugin-api` work in both legacy and NFS. Don't migrate them to `frontend-plugin-api` if you support legacy consumers. Only use `compatWrapper()` when a component depends on legacy context providers (e.g. old `SidebarContext`).

7. **Drawer content only renders when active**: If your drawer needs initialization logic on mount, use `AppRootElementBlueprint` for the persistent part.

8. **Module federation sharing**: Host and remote apps must share the same `@backstage/plugin-app-react` instance. Version mismatches cause runtime errors.

9. **NFS page components must not include a page shell**: The framework provides the header via `PageLayout`. If your NFS component wraps content in `PageWithHeader` or `Page` + `Header`, you'll get double headers. Create an `NfsMyPage` variant without the shell — see `references/migrate-page.md` for the dual header pattern.

10. **`useRouteRef` returns `undefined` in NFS**: The NFS `useRouteRef` from `@backstage/frontend-plugin-api` returns `RouteFunc | undefined` (the route might not be bound). The legacy version from `core-plugin-api` throws instead. When writing NFS-specific components, handle the `undefined` case.

---

## 11. Recent API Changes

If you migrated a plugin against an earlier Backstage NFS alpha, some APIs have changed. Key changes include the removal of `NavItemBlueprint`, deprecation of `makeWithOverrides` config pattern, and new params on `PageBlueprint` and `createFrontendPlugin`.

See the full list in [references/api-changes.md](../skills/nfs-migration/references/api-changes.md).

---

## 12. Automate It

Instead of migrating manually, use the included Agent Skill:

```bash
npx skills add redhat-developer/rhdh-skill --skill nfs-migration
```

Then tell your agent: *"Migrate my plugin to NFS"* -- it will analyze your plugin, apply the right patterns, update exports, and verify the result.

See [skills/nfs-migration/SKILL.md](../skills/nfs-migration/SKILL.md) for details.

---

## 13. Reference PRs

Real RHDH plugin migrations to study:

| Plugin | PR | What to learn |
|--------|-----|---------------|
| adoption-insights | [#2309](https://github.com/redhat-developer/rhdh-plugins/pull/2309) | Simple page plugin: Page + Nav + API |
| bulk-import | [#2247](https://github.com/redhat-developer/rhdh-plugins/pull/2247) | Page + Nav + permission patterns |
| scorecard | [#2487](https://github.com/redhat-developer/rhdh-plugins/pull/2487) | EntityContent + HomePage widgets |
| orchestrator | [#2526](https://github.com/redhat-developer/rhdh-plugins/pull/2526) | EntityContent + multi-route |
| lightspeed | [#2721](https://github.com/redhat-developer/rhdh-plugins/pull/2721) | Drawer + FAB (RHDH-specific) |
| extensions | [#2527](https://github.com/redhat-developer/rhdh-plugins/pull/2527) | compatWrapper usage |
| homepage | [#2423](https://github.com/redhat-developer/rhdh-plugins/pull/2423) | HomePageWidgets + compatWrapper |
| quickstart | [#2842](https://github.com/redhat-developer/rhdh-plugins/pull/2842) | Drawer + GlobalHeaderMenuItem |

### Upstream Backstage Docs

- [Plugin migration guide](https://backstage.io/docs/frontend-system/building-plugins/migrating)
- [Common extension blueprints](https://backstage.io/docs/frontend-system/building-plugins/common-extension-blueprints)
- [App migration guide](https://backstage.io/docs/frontend-system/building-apps/migrating)

---

## 14. Need Help?

- [RHDH Plugins GitHub Issues](https://github.com/redhat-developer/rhdh-plugins/issues)
- [Backstage Discord](https://discord.gg/backstage-687207715902193673)
- [Backstage Community](https://backstage.io/community/)
- [RHDH Documentation](https://docs.redhat.com/en/documentation/red_hat_developer_hub/)
