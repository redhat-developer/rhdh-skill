# RHDH-Specific Extension Migration

These blueprints are unique to Red Hat Developer Hub or have RHDH-specific usage patterns. For the full mount point → blueprint mapping, see `mount-point-mapping.md`.

## AppDrawerContentBlueprint — drawer panels

Replaces `application/internal/drawer-content` mount point.

```tsx
import { AppDrawerContentBlueprint } from '@red-hat-developer-hub/backstage-plugin-app-react/alpha';

const myDrawer = AppDrawerContentBlueprint.make({
  name: 'my-drawer',
  params: {
    id: MY_DRAWER_ID,
    element: <MyDrawerContent />,
    resizable: true,
    defaultWidth: 400,
  },
});
```

Register in your plugin's `extensions` array.

Drawer content mounts/unmounts with the drawer. Init logic that should persist (auto-open triggers, event listeners, snackbar setup) goes in a separate `AppRootElementBlueprint` registered via `createFrontendModule({ pluginId: 'app' })`:

```tsx
const myInitElement = AppRootElementBlueprint.make({
  name: 'my-init',
  params: { element: <MyInit /> },
});

export const myInitModule = createFrontendModule({
  pluginId: 'app',
  extensions: [myInitElement],
});
```

## GlobalHeaderMenuItemBlueprint — header menu items

Replaces `global.header/*` and `header/*` mount points.

```tsx
import { GlobalHeaderMenuItemBlueprint } from '@red-hat-developer-hub/backstage-plugin-global-header/alpha';

const myMenuItem = GlobalHeaderMenuItemBlueprint.make({
  name: 'my-menu-item',
  params: {
    target: 'help',
    component: MyMenuItem,
    priority: 50,
  },
});
```

- `target`: the header section (`help`, `profile`, `create`, etc.)
- `component`: React component for the menu item
- `priority`: ordering within the section (higher = first)

If your plugin owns the menu item, include it in the plugin's `extensions` array. If injecting from outside, use `createFrontendModule({ pluginId: 'global-header' })`.

## HomePageWidgetBlueprint — homepage cards

Replaces `home.page/cards` and `home.page/widgets` mount points.

```tsx
import { HomePageWidgetBlueprint } from '@backstage/plugin-home-react/alpha';

const myWidget = HomePageWidgetBlueprint.make({
  name: 'my-widget',
  params: {
    name: 'My Widget',
    layout: {
      width: { minColumns: 4, maxColumns: 12, defaultColumns: 12 },
      height: { minRows: 2, maxRows: 12, defaultRows: 4 },
    },
    components: () => import('./components/MyWidget').then(m => ({
      Content: m.MyWidget,
    })),
  },
});
```

Note: `HomePageWidgetBlueprint` uses `components` (returning `{ Content }`) and `layout` — different from other blueprints that use `loader`.

Register via module targeting the home plugin:

```tsx
export const myHomeModule = createFrontendModule({
  pluginId: 'home',
  extensions: [myWidget],
});
```

## AppRootWrapperBlueprint — app-level providers

Replaces `application/provider` mount point. Import from `@backstage/plugin-app-react`.

```tsx
import { AppRootWrapperBlueprint } from '@backstage/plugin-app-react';

const myWrapper = AppRootWrapperBlueprint.make({
  name: 'my-provider',
  params: {
    component: ({ children }) => (
      <MyProvider>{children}</MyProvider>
    ),
  },
});
```

Register via `createFrontendModule({ pluginId: 'app' })`.
