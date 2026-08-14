# App-Level Extension Migration

## AppRootWrapperBlueprint — wraps the entire app

Use for providers, theme wrappers, or any component that needs to wrap the whole React tree.

```tsx
import { AppRootWrapperBlueprint } from '@backstage/plugin-app-react';

const appWrapper = AppRootWrapperBlueprint.make({
  name: 'my-provider',
  params: {
    component: ({ children }) => (
      <MyProvider config={...}>
        {children}
      </MyProvider>
    ),
  },
});
```

## AppRootElementBlueprint — invisible root elements

Use for initialization logic, snackbar containers, FAB buttons, or anything that renders at the app root without wrapping children.

```tsx
import { AppRootElementBlueprint } from '@backstage/frontend-plugin-api';

const appElement = AppRootElementBlueprint.make({
  name: 'my-init',
  params: {
    element: <MyInitializer />,
  },
});
```

## PluginWrapperBlueprint — wraps a single plugin's UI

Use for context providers that should only wrap one plugin, not the entire app. Imported from `@backstage/frontend-plugin-api/alpha`.

```tsx
import { PluginWrapperBlueprint } from '@backstage/frontend-plugin-api/alpha';

const myPluginWrapper = PluginWrapperBlueprint.make({
  params: { component: MyPluginProvider },
});
```

Unlike `AppRootWrapperBlueprint` (app-wide), this scopes the provider to your plugin's extensions only. Note: this is an `@alpha` API — the import path may change in future Backstage releases.

## Shared components (legacy + NFS)

Hooks like `useApi` and `useRouteRef` from `@backstage/core-plugin-api` work in both legacy and NFS contexts. Keep component imports on `core-plugin-api` so the same components serve both export paths:

```tsx
// Keep this — works in both legacy and NFS
import { useApi, useRouteRef } from '@backstage/core-plugin-api';
```

## compatWrapper — rare

Only needed when a component depends on legacy context providers (e.g., `SidebarContext`) that aren't available in NFS. Wrap the JSX element in the loader:

```tsx
loader: () => import('./components/MyPage').then(m => compatWrapper(<m.MyPage />))
```

Import `compatWrapper` from `@backstage/core-compat-api`. Most plugins won't need this.

## When to use each

| Scenario | Approach |
|----------|----------|
| Need to wrap entire app (providers, themes) | `AppRootWrapperBlueprint` |
| Need invisible element at root (init, snackbars, FABs) | `AppRootElementBlueprint` |
| Components using `useApi`/`useRouteRef` | Keep on `@backstage/core-plugin-api` — works in both systems |
| Component depends on legacy context providers | Wrap with `compatWrapper()` (rare) |
| Provider scoped to one plugin only | `PluginWrapperBlueprint` |
| Both wrapping and init logic needed | Use both separately — don't combine |

All app-level extensions go in your plugin's `extensions` array (they belong to your plugin, not to another plugin).
