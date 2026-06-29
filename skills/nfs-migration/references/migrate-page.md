# Page and API Migration

## PageBlueprint — replaces `createRoutableExtension`

```tsx
import { PageBlueprint } from '@backstage/frontend-plugin-api';

const myPage = PageBlueprint.make({
  params: {
    path: '/my-plugin',
    title: 'My Plugin',
    icon: MyIcon,
    routeRef: rootRouteRef,
    loader: () => import('./components/MyPage').then(m => <m.NfsMyPage />),
  },
});
```

- `path`: URL path for this page
- `title`: page header title; also used for auto-discovered nav items
- `icon`: page header icon; also used for nav items. Prefer [Remix Icons](https://remixicon.com/) (`@remixicon/react`). MUI icons work with `fontSize="inherit"`
- `routeRef`: route ref created with `createRouteRef`
- `loader`: async factory returning a JSX element
- `noHeader`: (optional) hides the default plugin page header

Nav items are auto-generated from pages with `title` + `icon` + `routeRef` — no separate blueprint needed. You can also set `title` and `icon` on `createFrontendPlugin` as fallbacks.

> Earlier versions used `NavItemBlueprint`. It has been removed — see `api-changes.md`.

## Dual header pattern

In the old system, each page renders its own page shell (`PageWithHeader`, `Page` + `Header`). In NFS, the framework provides the page header automatically via `PageLayout` — so NFS page components must **not** include their own page shell. Without this, you get **double headers**.

### Pattern A: Separate components (simple pages)

Create two exports — one for each system:

```tsx
// src/components/MyPage/MyPage.tsx
import { Content, PageWithHeader } from '@backstage/core-components';

// Legacy — includes page shell
export function MyPage() {
  return (
    <PageWithHeader title="My Plugin" themeId="tool">
      <Content>
        <MyPageContent />
      </Content>
    </PageWithHeader>
  );
}

// NFS — content only, no page shell
export function NfsMyPage() {
  return (
    <Content>
      <MyPageContent />
    </Content>
  );
}
```

The NFS variant is loaded by `PageBlueprint`:

```tsx
loader: () => import('./components/MyPage').then(m => <m.NfsMyPage />),
```

If the NFS page needs a subtitle or custom actions below the framework header, use `Header` from `@backstage/ui`:

```tsx
import { Header } from '@backstage/ui';

export function NfsMyPage() {
  return (
    <>
      <Header
        title="Subtitle"
        customActions={<SupportButton>Help</SupportButton>}
      />
      <Content>
        <MyPageContent />
      </Content>
    </>
  );
}
```

### Pattern B: Header variant prop (complex pages)

For pages with significant shared logic, use a prop to switch between systems:

```tsx
function MyPageContent(props: MyPageProps & { headerVariant: 'legacy' | 'bui' }) {
  const { headerVariant, ...rest } = props;
  const pageContent = <Content>{/* shared page body */}</Content>;

  if (headerVariant === 'bui') {
    return pageContent;
  }
  return (
    <PageWithHeader title="My Plugin" themeId="tool">
      {pageContent}
    </PageWithHeader>
  );
}

// Old system export
export const MyPage = (props: MyPageProps) => (
  <MyPageContent {...props} headerVariant="legacy" />
);

// NFS export
export const NfsMyPage = (props: MyPageProps) => (
  <MyPageContent {...props} headerVariant="bui" />
);
```

## SubPageBlueprint — tabbed sub-pages

For plugins with tabbed pages, use `SubPageBlueprint` instead of internal routing. The parent `PageBlueprint` omits its `loader` — the framework renders sub-pages as tabs automatically.

```tsx
import { PageBlueprint, SubPageBlueprint } from '@backstage/frontend-plugin-api';

// Parent page — no loader, renders tabs
const myPluginPage = PageBlueprint.make({
  params: {
    path: '/my-plugin',
    routeRef: rootRouteRef,
  },
});

// Sub-pages — path is relative (no leading /)
const overviewPage = SubPageBlueprint.make({
  name: 'overview',
  params: {
    path: 'overview',
    title: 'Overview',
    loader: () => import('./components/Overview').then(m => <m.OverviewContent />),
  },
});

const settingsPage = SubPageBlueprint.make({
  name: 'settings',
  params: {
    path: 'settings',
    title: 'Settings',
    loader: () => import('./components/Settings').then(m => <m.SettingsContent />),
  },
});
```

**When to use `SubPageBlueprint`:** Only for top-level tabs that should appear in the page header. For drill-down routes (e.g. `/items/:id`), keep internal routing inside a `PageBlueprint` loader.

## ApiBlueprint — replaces `apis` array in `createPlugin`

```tsx
import { ApiBlueprint, discoveryApiRef, fetchApiRef } from '@backstage/frontend-plugin-api';
import { myApiRef, MyApiClient } from './api';

const myApi = ApiBlueprint.make({
  params: defineParams => defineParams({
    api: myApiRef,
    deps: {
      discoveryApi: discoveryApiRef,
      fetchApi: fetchApiRef,
    },
    factory: ({ discoveryApi, fetchApi }) =>
      new MyApiClient({ discoveryApi, fetchApi }),
  }),
});
```

**API refs in factories** must come from `@backstage/frontend-plugin-api` (not `core-plugin-api`): `configApiRef`, `fetchApiRef`, `identityApiRef`, `discoveryApiRef`, etc.

**API refs in components** should stay on `@backstage/core-plugin-api` so the same components work in both systems.

### API ownership

Each API has an owner plugin. Only modules targeting the owning `pluginId` can override it. Ownership is determined by:

1. Explicit `pluginId` on the API ref (recommended):
   ```tsx
   const myApiRef = createApiRef<MyApi>().with({
     id: 'plugin.my-plugin.client',
     pluginId: 'my-plugin',
   });
   ```
2. ID pattern: `plugin.<pluginId>.*` → owned by that plugin
3. `core.*` → owned by the `app` plugin

If you try to override an API from a module with the wrong `pluginId`, you get `API_FACTORY_CONFLICT`.

## Route refs

### Reuse existing route refs

Route refs from `@backstage/core-plugin-api` work directly in NFS — no conversion needed. Pass them to `createFrontendPlugin`'s `routes` and to `PageBlueprint`'s `routeRef`.

### External route refs with `defaultTarget`

Set `defaultTarget` on external route refs so plugins work out-of-the-box without requiring `bindRoutes` in the app:

```tsx
export const viewTechDocRouteRef = createExternalRouteRef({
  id: 'view-techdoc',
  optional: true,
  params: ['namespace', 'kind', 'name'],
  defaultTarget: 'techdocs.docRoot',
});
```

The target format is `<pluginId>.<routeName>`, matching the `routes` map of the target plugin. The default is only used when the target plugin is installed.

### `useRouteRef` behavior difference

In NFS, `useRouteRef` from `@backstage/frontend-plugin-api` returns `RouteFunc | undefined` (the route might not be bound). The legacy version from `core-plugin-api` throws instead. When writing NFS components, handle the `undefined` case.

## Assembling in the plugin

```tsx
import { createFrontendPlugin } from '@backstage/frontend-plugin-api';
import { RiToolsLine } from '@remixicon/react';

export default createFrontendPlugin({
  pluginId: 'my-plugin',
  title: 'My Plugin',
  icon: <RiToolsLine />,
  extensions: [myPage, myApi],
  routes: {
    root: rootRouteRef,
  },
  externalRoutes: {
    // same external routes as the old plugin
  },
});
```

Pages and APIs go into the `extensions` array. Nav items are auto-generated from pages with `title` + `icon` + `routeRef`. For icons, prefer [Remix Icons](https://remixicon.com/) from `@remixicon/react`.
