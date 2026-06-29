# Before/After: Page Plugin Migration

Complete page plugin migration based on the adoption-insights pattern.

## Before (Legacy)

### Plugin definition

```typescript
// src/plugin.ts
import { createPlugin, createApiFactory, createRoutableExtension, configApiRef, fetchApiRef } from '@backstage/core-plugin-api';
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

export const MyPluginPage = myPlugin.provide(
  createRoutableExtension({
    name: 'MyPluginPage',
    component: () => import('./components/MyPage').then(m => m.MyPage),
    mountPoint: rootRouteRef,
  }),
);
```

### App wiring (legacy)

```tsx
// App.tsx
import { MyPluginPage } from '@scope/my-plugin';
<Route path="/my-plugin" element={<MyPluginPage />} />
```

## After (NFS)

### Plugin definition

```tsx
// src/index.ts (default export)
import { createFrontendPlugin, ApiBlueprint, PageBlueprint, configApiRef, fetchApiRef, createApiFactory } from '@backstage/frontend-plugin-api';
import { rootRouteRef } from './routes';
import { myApiRef, MyApiClient } from './api';
import MyIcon from '@mui/icons-material/Extension';

const myApi = ApiBlueprint.make({
  params: defineParams => defineParams(
    createApiFactory({
      api: myApiRef,
      deps: { configApi: configApiRef, fetchApi: fetchApiRef },
      factory: ({ configApi, fetchApi }) => new MyApiClient({ configApi, fetchApi }),
    }),
  ),
});

const myPage = PageBlueprint.make({
  params: {
    path: '/my-plugin',
    title: 'My Plugin',
    icon: MyIcon,
    routeRef: rootRouteRef,
    loader: () => import('./components/MyPage').then(m => <m.NfsMyPage />),
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

> **Nav items:** The legacy `SidebarItem` is replaced by auto-discovery — `title` + `icon` + `routeRef` on the page generates a nav entry automatically.

> **Dual header:** The loader imports `NfsMyPage` (not `MyPage`) — the NFS variant without the page shell. Create it by extracting the content from `MyPage` without the `PageWithHeader` wrapper. See `references/migrate-page.md` for the full pattern.

### App wiring (NFS)

```tsx
// App.tsx
import { createApp } from '@backstage/frontend-defaults';
import myPlugin from '@scope/my-plugin';
export default createApp({ features: [myPlugin] });
```
