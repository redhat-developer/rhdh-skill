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

> **Version note:** Earlier versions used `config: { schema: { filter: z => z.string().optional() } }`. This is deprecated -- use top-level `configSchema` with direct `zod/v4` imports instead. See `api-changes.md`.

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
