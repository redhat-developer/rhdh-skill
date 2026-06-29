# Before/After: Entity Tab Migration

Complete entity tab migration based on the scorecard/orchestrator pattern.

## Before (Legacy)

```tsx
// In the app's EntityPage.tsx
import { EntityScorecardContent } from '@scope/my-plugin';

<EntityLayout.Route path="/my-tab" title="My Tab">
  <EntityScorecardContent />
</EntityLayout.Route>
```

## After (NFS)

### Basic entity content extension

```tsx
// src/alpha/entityTab.tsx (or inline in alpha/index.tsx)
import { EntityContentBlueprint } from '@backstage/plugin-catalog-react/alpha';
import { createFrontendPlugin } from '@backstage/frontend-plugin-api';

const myEntityContent = EntityContentBlueprint.make({
  params: {
    path: '/my-tab',
    title: 'My Tab',
    filter: 'kind:Component',
    loader: () => import('./components/MyTab').then(m => <m.MyTabContent />),
  },
});

export default createFrontendPlugin({
  pluginId: 'my-plugin',
  extensions: [myEntityContent],
});
```

### Config-driven filtering variant

Use `EntityContentBlueprint.makeWithOverrides` when you want operators to control filtering via `app-config.yaml` instead of hardcoding it:

```tsx
import { z } from 'zod/v4';

const myEntityContent = EntityContentBlueprint.makeWithOverrides({
  configSchema: {
    filter: z.string().optional(),
  },
  factory(originalFactory, { config }) {
    return originalFactory({
      path: '/my-tab',
      title: 'My Tab',
      filter: config.filter ?? 'kind:Component',
      loader: () => import('./components/MyTab').then(m => <m.MyTabContent />),
    });
  },
});
```

This lets operators override the entity filter in `app-config.yaml`:

```yaml
app:
  extensions:
    - entity-content:catalog/my-tab:
        config:
          filter: 'kind:Component,API'
```
