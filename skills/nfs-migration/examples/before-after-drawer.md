# Before/After: Drawer Plugin Migration (RHDH-Specific)

Drawer plugin migration based on the lightspeed/quickstart pattern.

## Before (Legacy)

```tsx
// src/plugin.ts
export const MyDrawerContent = myPlugin.provide(
  createComponentExtension({
    name: 'MyDrawerContent',
    component: { lazy: () => import('./components/DrawerContent').then(m => m.DrawerContent) },
  }),
);
// Wired via app-config.dynamic.yaml mount points
```

## After (NFS)

### Drawer content plugin

```tsx
import { createFrontendPlugin, createFrontendModule, AppRootElementBlueprint } from '@backstage/frontend-plugin-api';
import { AppDrawerContentBlueprint } from '@red-hat-developer-hub/backstage-plugin-app-react/alpha';
import { MY_DRAWER_ID } from './const';

const myDrawer = AppDrawerContentBlueprint.make({
  name: 'my-drawer',
  params: {
    id: MY_DRAWER_ID,
    loader: () => import('./components/DrawerContent').then(m => <m.DrawerContent />),
    resizable: true,
    defaultWidth: 400,
  },
});

export default createFrontendPlugin({
  pluginId: 'my-drawer-plugin',
  extensions: [myDrawer],
});

// Init logic (auto-open, snackbar) goes in a separate app module
const myInitElement = AppRootElementBlueprint.make({
  name: 'my-drawer-init',
  params: { element: <MyDrawerInit /> },
});

export const myDrawerInitModule = createFrontendModule({
  pluginId: 'app',
  extensions: [myInitElement],
});
```

> **Note:** Drawer content only renders when the drawer is active. Init logic that should run on page load (e.g. auto-open triggers, snackbar notifications) needs `AppRootElementBlueprint` in a separate module attached to the `app` plugin.
