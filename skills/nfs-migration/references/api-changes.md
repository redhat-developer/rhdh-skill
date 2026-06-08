# NFS API Changes

Breaking and notable changes between the early NFS alpha and the current Backstage GA codebase. Reference this when upgrading Backstage versions or updating plugins that were migrated against an older NFS API.

> To upgrade your `@backstage/*` dependencies to the version that includes these changes, use the `backstage-upgrade` skill (`../backstage-upgrade/SKILL.md`).

## Component imports — keep on `core-plugin-api`

Hooks like `useApi`, `useRouteRef`, and `useRouteRefParams` from `@backstage/core-plugin-api` work in both legacy and NFS contexts. **Keep component imports on `core-plugin-api`** so the same components serve both the root NFS export and the `./legacy` export.

Only the plugin definition code (`plugin.tsx`) and blueprint/API factory code use `@backstage/frontend-plugin-api` imports. Don't migrate component-level imports — it breaks legacy consumers.

`compatWrapper()` is only needed when a component depends on legacy context providers (e.g. old `SidebarContext`) that aren't available in NFS. Most plugins won't need it.

## NavItemBlueprint removed

`NavItemBlueprint` from `@backstage/frontend-plugin-api` has been removed. Nav items are now **auto-discovered** from `PageBlueprint` extensions.

When a page has `routeRef`, `title`, and `icon`, the app nav system automatically generates a sidebar entry. No separate blueprint is needed.

**If you previously used NavItemBlueprint:**

```tsx
// Old — remove this
const myNavItem = NavItemBlueprint.make({
  params: { title: 'My Plugin', routeRef: rootRouteRef, icon: MyIcon },
});

// New — add title and icon to PageBlueprint and/or createFrontendPlugin
const myPage = PageBlueprint.make({
  params: {
    path: '/my-plugin',
    title: 'My Plugin',
    icon: MyIcon,
    routeRef: rootRouteRef,
    loader: () => import('./components/MyPage').then(m => <m.MyPage />),
  },
});

export default createFrontendPlugin({
  pluginId: 'my-plugin',
  title: 'My Plugin',
  icon: MyIcon,
  extensions: [myApi, myPage],
  routes: { root: rootRouteRef },
});
```

**Priority chain** for auto-discovered nav items:
- Title: explicit `PageBlueprint` title > `createFrontendPlugin` title > pluginId
- Icon: explicit `PageBlueprint` icon > `createFrontendPlugin` icon > (excluded from nav)

If you need a standalone nav entry without a page, or full control over the nav bar, use `NavContentBlueprint` from `@backstage/plugin-app-react` to replace the entire nav component.

## `makeWithOverrides` config pattern deprecated

The `config: { schema: {...} }` pattern is deprecated. Use top-level `configSchema` instead.

```tsx
// Old (deprecated)
EntityContentBlueprint.makeWithOverrides({
  config: {
    schema: {
      filter: z => z.string().optional(),
    },
  },
  factory(originalFactory, { config }) { ... },
});

// New
import { z } from 'zod/v4';

EntityContentBlueprint.makeWithOverrides({
  configSchema: {
    filter: z.string().optional(),
  },
  factory(originalFactory, { config }) { ... },
});
```

Note: the `z` import changes from the callback form `z => z.string()` to a direct import from `zod/v4`.

## `AppRootWrapperBlueprint` param rename

The `Component` param (uppercase) is deprecated. Use `component` (lowercase).

Import from `@backstage/plugin-app-react`, **not** `@backstage/frontend-plugin-api`.

```tsx
// Old
AppRootWrapperBlueprint.make({ params: { Component: MyWrapper } });

// New
import { AppRootWrapperBlueprint } from '@backstage/plugin-app-react';
AppRootWrapperBlueprint.make({ params: { component: MyWrapper } });
```

## Deprecated param names in blueprints

Several blueprint params were renamed. The old names produce TypeScript errors:

| Blueprint | Old param (deprecated) | New param |
|-----------|----------------------|-----------|
| `PageBlueprint` | `defaultPath` | `path` |
| `EntityContentBlueprint` | `defaultPath` | `path` |
| `EntityContentBlueprint` | `defaultTitle` | `title` |
| `EntityContentBlueprint` | `defaultGroup` | `group` |

## `createFrontendPlugin` now accepts `title` and `icon`

These are used as fallbacks for page headers and auto-discovered nav entries:

```tsx
export default createFrontendPlugin({
  pluginId: 'my-plugin',
  title: 'My Plugin',
  icon: MyIcon,
  extensions: [myPage, myApi],
  routes: { root: rootRouteRef },
});
```

## `PageBlueprint` new params

- `title?: string` — page header title, also used for nav item auto-discovery
- `icon?: IconElement` — page header icon, also used for nav item
- `noHeader?: boolean` — hides the default plugin page header for full-bleed layouts

## `SubPageBlueprint` added

Creates tabbed sub-pages within a parent `PageBlueprint`. Exported from `@backstage/frontend-plugin-api`.

```tsx
import { SubPageBlueprint } from '@backstage/frontend-plugin-api';

const overviewPage = SubPageBlueprint.make({
  attachTo: { id: 'page:my-plugin', input: 'pages' },
  name: 'overview',
  params: {
    path: 'overview',
    title: 'Overview',
    loader: () => import('./components/Overview').then(m => <m.Overview />),
  },
});
```

Note: the `path` must NOT start with `/` (it's relative to the parent page).

## NFS page components — no page shell

NFS pages must not include `PageWithHeader`, `Page` + `Header`, or any page shell component. The framework provides the header automatically via `PageLayout`. Create NFS-specific page variants:

```tsx
// Legacy — includes page shell
export function MyPage() {
  return (
    <PageWithHeader title="My Plugin" themeId="tool">
      <Content><MyPageContent /></Content>
    </PageWithHeader>
  );
}

// NFS — content only
export function NfsMyPage() {
  return <Content><MyPageContent /></Content>;
}
```

Load the NFS variant in `PageBlueprint`:
```tsx
loader: () => import('./components/MyPage').then(m => <m.NfsMyPage />)
```

## `useRouteRef` returns `undefined` in NFS

`useRouteRef` from `@backstage/frontend-plugin-api` returns `RouteFunc | undefined`. The legacy version from `core-plugin-api` throws on unbound routes. Handle the `undefined` case in NFS components.

## Remix Icons preferred

Use [Remix Icons](https://remixicon.com/) from `@remixicon/react` for plugin icons. MUI icons work with `fontSize="inherit"` but Remix is the recommended choice for new plugins.

## External route refs — `defaultTarget`

Set `defaultTarget` on external route refs so plugins work out-of-the-box without `bindRoutes`:

```tsx
export const viewTechDocRouteRef = createExternalRouteRef({
  id: 'view-techdoc',
  optional: true,
  defaultTarget: 'techdocs.docRoot',
});
```

## New catalog-react blueprints

The `@backstage/plugin-catalog-react/alpha` package now exports additional blueprints:

- `CatalogFilterBlueprint` — custom catalog filters
- `EntityContentLayoutBlueprint` — entity content layouts
- `EntityContextMenuItemBlueprint` — entity context menu items
- `EntityHeaderBlueprint` — custom entity headers
- `EntityIconLinkBlueprint` — entity icon links
