# Entity Content and Card Migration

Entity content and cards can go directly in your plugin's `extensions` array. The `EntityContentBlueprint` declares its own attach point (`page:catalog/entity`), so the app discovers them automatically regardless of where they're registered.

Use `createFrontendModule({ pluginId: 'catalog' })` only when you're injecting entity content from a separate package that doesn't own the plugin (e.g., a third-party addon).

## EntityContentBlueprint — replaces entity tab routes

```tsx
import { EntityContentBlueprint } from '@backstage/plugin-catalog-react/alpha';

const entityContent = EntityContentBlueprint.make({
  name: 'my-tab',
  params: {
    path: '/my-plugin',
    title: 'My Plugin',
    loader: () => import('./components/MyEntityPage').then(m => <m.MyEntityPage />),
  },
});
```

### With config-driven entity filtering

Use `makeWithOverrides` to support `filter` from app-config:

```tsx
import { z } from 'zod/v4';

const entityContent = EntityContentBlueprint.makeWithOverrides({
  name: 'my-tab',
  configSchema: {
    filter: z.string().optional(),
  },
  factory(originalFactory, { config }) {
    return originalFactory({
      path: '/my-plugin',
      title: 'My Plugin',
      filter: config.filter || 'kind:component',
      loader: () => import('./components/MyEntityPage').then(m => <m.MyEntityPage />),
    });
  },
});
```

> **Version note:** Earlier versions used `config: { schema: { filter: z => z.string().optional() } }`. This is deprecated -- use top-level `configSchema` with direct `zod/v4` imports instead. Invoke `/backstage-api-changes` by name for the full delta.

## EntityCardBlueprint — replaces entity overview cards

Same pattern as `EntityContentBlueprint` but for cards displayed on entity overview pages:

```tsx
import { EntityCardBlueprint } from '@backstage/plugin-catalog-react/alpha';

const entityCard = EntityCardBlueprint.make({
  name: 'my-card',
  params: {
    filter: 'kind:component',
    loader: () => import('./components/MyCard').then(m => <m.MyCard />),
  },
});
```

## Register in your plugin

Include entity extensions in your plugin's `extensions` array:

```tsx
import { createFrontendPlugin } from '@backstage/frontend-plugin-api';

export default createFrontendPlugin({
  pluginId: 'my-plugin',
  extensions: [entityContent, entityCard],
});
```

### Alternative: separate module

If you're providing entity content from a package that doesn't own the plugin (e.g., a third-party addon), use a module instead:

```tsx
import { createFrontendModule } from '@backstage/frontend-plugin-api';

export const myCatalogModule = createFrontendModule({
  pluginId: 'catalog',
  extensions: [entityContent, entityCard],
});
```

Export the module so consumers can include it in their app's `features` array.

## EntityContextMenuItemBlueprint

See `mount-point-mapping.md` for the migration pattern (replaces `entity.context.menu` mount point).

## Entity tab groups

Tabs are organized into groups on `page:catalog/entity`. Default groups: `overview`, `documentation`, `development`, `deployment`, `operation`, `observability`.

**Plugin authors** assign content to a group via the `group` param:

```tsx
const entityContent = EntityContentBlueprint.make({
  name: 'my-tab',
  params: {
    path: '/my-tab',
    title: 'My Tab',
    group: 'development',
    loader: () => import('./MyTab').then(m => <m.MyTab />),
  },
});
```

**Operators** configure groups in `app-config.yaml`:

```yaml
app:
  extensions:
    - page:catalog/entity:
        config:
          showNavItemIcons: true
          groups:
            - overview:
                title: Overview
            - documentation:
                title: Documentation
            - development:
                title: Development
            - custom:
                title: My Custom Group
            - deployment: false  # hide this group
```

Set `group: false` on an `entity-content:*` extension to show it as a standalone tab outside any group.

See `operator-config.md` for the full operator configuration reference.

## Card layout: `type: info` vs `type: content`

Entity overview uses `DefaultEntityContentLayout` with two card types:

- **`type: info`** — renders in a sticky sidebar (right side). Use for compact summary cards like About, Links.
- **`type: content`** — renders in the main area (left side). Default if not specified.

```yaml
app:
  extensions:
    - entity-card:catalog/about:
        config:
          type: info
    - entity-card:catalog/links:
        config:
          type: info
```

Warnings (orphan, relation, processing errors) are built into the layout — no separate mount point configuration needed.
